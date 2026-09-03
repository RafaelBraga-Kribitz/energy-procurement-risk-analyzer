"""Retrospective engine — what each strategy actually cost, 2021-2025 (M6, Q1).

Binding contract: SPEC-05 §3 (strategy formulas S1-S4), §5 (ST-301..304).
S1 hourly join uses pre-aligned frames (NULL-price hours already dropped).

Implements: ST-101..107, ST-301..304, ST-502, ST-503, ST-602.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, cast

import pandas as pd

from epra.common.config import Settings, StrategyCfg
from epra.strategies.align import AlignedVolumes
from epra.strategies.calibration import Anchors

logger = logging.getLogger(__name__)
S1_ID = "S1"
S2_ID = "S2"
S3_ID = "S3"
HYBRID_IDS: dict[float, str] = {0.30: "S4_30", 0.50: "S4_50", 0.70: "S4_70"}
COST_COLS = (
    "year_local",
    "month_local",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
    "unit_cost_eur_mwh",
)
ST502_SENTENCE = (
    "Contract prices proxied via ÖSPI (futures-based index); "
    "premiums are calibrated assumptions - see LIMITATIONS."
)
LP050_SENTENCE = (
    "Reference load profile is constructed (CALIBRATED), not measured; "
    "construction rules in SPEC-03."
)


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _as_float(value: object) -> float:
    return float(cast(Any, value))


def cost_s1(hourly: pd.DataFrame) -> pd.DataFrame:
    """Monthly FULL_SPOT cost: ``Σ load_mwh × price_at_eur_mwh``.

    Pre: hourly has no NULL prices (alignment already applied).

    Implements: ST-101, ST-301.
    """
    if hourly.empty:
        return pd.DataFrame(columns=list(COST_COLS))
    if hourly["price_at_eur_mwh"].isna().any():
        raise ValueError("cost_s1 requires aligned hours with no NULL prices (ST-101)")
    work = hourly.assign(cost_eur=hourly["load_mwh"] * hourly["price_at_eur_mwh"])
    monthly = work.groupby(["year_local", "month_local"], as_index=False, sort=True).agg(
        volume_mwh=("load_mwh", "sum"),
        cost_eur=("cost_eur", "sum"),
    )
    monthly["strategy_id"] = S1_ID
    monthly["unit_cost_eur_mwh"] = monthly["cost_eur"] / monthly["volume_mwh"]
    return monthly.loc[:, list(COST_COLS)]


def _oespi_month(oespi: pd.DataFrame, year: int, month: int) -> pd.Series:
    rows = oespi.loc[(oespi["year_local"] == year) & (oespi["month_local"] == month)]
    if len(rows) != 1:
        raise ValueError(f"expected one ÖSPI row for {year}-{month:02d}, got {len(rows)}")
    return rows.iloc[0]


def blended_contract_price(
    anchors: Anchors,
    oespi_base: float,
    oespi_peak: float,
    w_peak: float,
    *,
    peak_available: bool,
) -> float:
    """Translate ÖSPI index levels through P_ref (T-5).

    Implements: ST-102, ST-104.
    """
    if anchors.oespi_base_ref <= 0:
        raise ValueError("oespi_base_ref must be > 0")
    base_leg = anchors.p_ref_base * (oespi_base / anchors.oespi_base_ref)
    if not peak_available:
        return base_leg
    if anchors.oespi_peak_ref <= 0:
        raise ValueError("oespi_peak_ref must be > 0")
    peak_leg = anchors.p_ref_peak * (oespi_peak / anchors.oespi_peak_ref)
    return base_leg * (1.0 - w_peak) + peak_leg * w_peak


def p_s2(
    year: int,
    month: int,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    *,
    peak_available: bool = True,
) -> float:
    """Monthly ÖSPI-indexed contract price (ST-102).

    Implements: ST-102, ST-104.
    """
    row = _oespi_month(oespi, year, month)
    return blended_contract_price(
        anchors,
        float(row["oespi_base"]),
        float(row["oespi_peak"]),
        w_peak,
        peak_available=peak_available,
    )


def lock_window_slice(
    oespi: pd.DataFrame, delivery_year: int, lock_months: list[int]
) -> pd.DataFrame:
    """ÖSPI rows in Y-1 lock months only (ST-105, ST-503).

    Implements: ST-105, ST-503.
    """
    lock_year = delivery_year - 1
    months = set(lock_months)
    rows = oespi.loc[(oespi["year_local"] == lock_year) & (oespi["month_local"].isin(months))]
    present = {int(m) for m in rows["month_local"].tolist()}
    missing = sorted(months - present)
    if missing:
        raise ValueError(
            f"lock window incomplete for delivery {delivery_year} "
            f"(missing {lock_year} months {missing})"
        )
    return rows


def p_s3(
    year: int,
    oespi: pd.DataFrame,
    anchors: Anchors,
    cfg: StrategyCfg,
    *,
    w_peak: float,
) -> float:
    """Fixed annual price from Y-1 lock-window ÖSPI mean plus premium.

    Implements: ST-105.
    """
    lock = lock_window_slice(oespi, year, cfg.lock_window_months)
    indexed = blended_contract_price(
        anchors,
        float(lock["oespi_base"].mean()),
        float(lock["oespi_peak"].mean()),
        w_peak,
        peak_available=cfg.peak_available,
    )
    return indexed + cfg.fixed_premium_eur_mwh


def _priced_month(volume: pd.DataFrame, price: float, strategy_id: str) -> pd.DataFrame:
    out = volume.copy()
    out["strategy_id"] = strategy_id
    out["cost_eur"] = out["volume_mwh"] * price
    out["unit_cost_eur_mwh"] = price
    return out.loc[:, list(COST_COLS)]


def cost_s2(
    monthly: pd.DataFrame,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    *,
    peak_available: bool = True,
) -> pd.DataFrame:
    """Monthly indexed cost (ST-103).

    Implements: ST-103.
    """
    rows = [
        _priced_month(
            chunk,
            p_s2(
                _as_int(chunk["year_local"].iloc[0]),
                _as_int(chunk["month_local"].iloc[0]),
                oespi,
                anchors,
                w_peak,
                peak_available=peak_available,
            ),
            S2_ID,
        )
        for _, chunk in monthly.groupby(["year_local", "month_local"], sort=True)
    ]
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=list(COST_COLS))


def cost_s3(
    monthly: pd.DataFrame,
    oespi: pd.DataFrame,
    anchors: Anchors,
    cfg: StrategyCfg,
    *,
    w_peak: float,
) -> pd.DataFrame:
    """Monthly cost at the year's locked S3 price (ST-106).

    Implements: ST-106.
    """
    rows: list[pd.DataFrame] = []
    for year, chunk in monthly.groupby("year_local", sort=True):
        price = p_s3(_as_int(year), oespi, anchors, cfg, w_peak=w_peak)
        rows.append(_priced_month(chunk, price, S3_ID))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=list(COST_COLS))


def cost_s4(s1: pd.DataFrame, s3: pd.DataFrame, h: float) -> pd.DataFrame:
    """Hybrid: fraction ``h`` at S3, remainder at S1 (ST-107).

    Implements: ST-107.
    """
    if h not in HYBRID_IDS:
        raise ValueError(f"h must be one of {sorted(HYBRID_IDS)}, got {h}")
    left = s1.rename(columns={"cost_eur": "c1", "volume_mwh": "v1", "unit_cost_eur_mwh": "u1"})
    right = s3.rename(columns={"cost_eur": "c3", "volume_mwh": "v3", "unit_cost_eur_mwh": "u3"})
    keys = ["year_local", "month_local"]
    merged = left.merge(right[[*keys, "c3", "v3"]], on=keys, how="inner")
    if len(merged) != len(s1) or not (merged["v1"] == merged["v3"]).all():
        raise ValueError("S4 requires identical S1/S3 monthly volumes (ST-501)")
    merged["volume_mwh"] = merged["v1"]
    merged["cost_eur"] = h * merged["c3"] + (1.0 - h) * merged["c1"]
    merged["strategy_id"] = HYBRID_IDS[h]
    merged["unit_cost_eur_mwh"] = merged["cost_eur"] / merged["volume_mwh"]
    return merged.loc[:, list(COST_COLS)]


def run(
    settings: Settings,
    *,
    aligned: AlignedVolumes | None = None,
    monthly_oespi: pd.DataFrame | None = None,
    anchors: Anchors | None = None,
    w_peak: float | None = None,
    cfg: StrategyCfg | None = None,
) -> pd.DataFrame:
    """Compute cost(strategy, year, month) for configured years.

    Implements: ST-301, ST-302, ST-304, ST-602, D-03.
    """
    from epra.common.config import load_strategy_config
    from epra.strategies.annual import (
        annual_summary,
        render_annual_charts,
        wipe_known_reports,
        write_strategy_costs,
        write_unit_cost_md,
        wrong_strategy_costs,
    )

    cfg = cfg or load_strategy_config()
    aligned, monthly_oespi, anchors, w_peak = _resolve_inputs(
        settings,
        cfg,
        aligned=aligned,
        monthly_oespi=monthly_oespi,
        anchors=anchors,
        w_peak=w_peak,
    )
    years = set(cfg.retrospective_years)
    retro = AlignedVolumes(
        hourly=aligned.hourly.loc[aligned.hourly["year_local"].isin(years)],
        monthly=aligned.monthly.loc[aligned.monthly["year_local"].isin(years)],
        dropped_hours=aligned.dropped_hours,
    )
    stacked = _stack_costs(retro, monthly_oespi, anchors, w_peak, cfg)
    annual = annual_summary(stacked)
    _enforce_st602(annual)
    wipe_known_reports(settings)
    write_strategy_costs(stacked, settings)
    render_annual_charts(annual, settings)
    write_unit_cost_md(annual, settings)
    _write_strategy_ssot(wrong_strategy_costs(annual), anchors, settings)
    return stacked


def _resolve_inputs(
    settings: Settings,
    cfg: StrategyCfg,
    *,
    aligned: AlignedVolumes | None,
    monthly_oespi: pd.DataFrame | None,
    anchors: Anchors | None,
    w_peak: float | None,
) -> tuple[AlignedVolumes, pd.DataFrame, Anchors, float]:
    from epra.strategies.align import (
        align_hourly,
        load_consumer_load,
        load_price_hourly,
        load_price_monthly,
        load_w_peak,
    )
    from epra.strategies.calibration import compute_anchors

    if aligned is None:
        aligned = align_hourly(load_consumer_load(settings), load_price_hourly(settings))
    if monthly_oespi is None:
        monthly_oespi = load_price_monthly(settings)
    if w_peak is None:
        w_peak = load_w_peak(settings)
    if anchors is None:
        anchors = _anchors_from_frame(
            compute_anchors(settings, cfg, aligned=aligned, monthly_oespi=monthly_oespi)
        )
    return aligned, monthly_oespi, anchors, w_peak


def _enforce_st602(annual: pd.DataFrame) -> None:
    from epra.strategies.annual import check_st602a, check_st602b

    for name, gate in (("ST-602(a)", check_st602a(annual)), ("ST-602(b)", check_st602b(annual))):
        if gate.status == "skip":
            logger.info("%s skip: %s", name, gate.reason)
        elif gate.status == "fail":
            raise RuntimeError(gate.reason)


def _anchors_from_frame(frame: pd.DataFrame) -> Anchors:
    row = frame.iloc[0]
    return Anchors(
        p_ref_base=float(row["p_ref_base"]),
        p_ref_peak=float(row["p_ref_peak"]),
        oespi_base_ref=float(row["oespi_base_ref"]),
        oespi_peak_ref=float(row["oespi_peak_ref"]),
    )


def _stack_costs(
    aligned: AlignedVolumes,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    cfg: StrategyCfg,
) -> pd.DataFrame:
    s1 = cost_s1(aligned.hourly)
    s3 = cost_s3(aligned.monthly, oespi, anchors, cfg, w_peak=w_peak)
    s2 = cost_s2(aligned.monthly, oespi, anchors, w_peak, peak_available=cfg.peak_available)
    hybrids = [cost_s4(s1, s3, h) for h in cfg.hybrid_ratios]
    return pd.concat([s1, s2, s3, *hybrids], ignore_index=True)


def _ssot_row(key: str, value: float, unit: str) -> dict[str, object]:
    return {
        "key": key,
        "value": value,
        "unit": unit,
        "tag": "CALIBRATED",
        "produced_by": "epra.strategies.retrospective",
    }


def _write_strategy_ssot(span: pd.DataFrame, anchors: Anchors, settings: Settings) -> None:
    from epra.strategies.align import processed_dir
    from epra.strategies.annual import write_ssot_parquet

    rows: list[dict[str, object]] = []
    total = 0.0
    for rec in span.itertuples(index=False):
        year = _as_int(rec.year_local)
        value = _as_float(rec.wrong_strategy_cost_eur)
        total += value
        rows.append(_ssot_row(f"wrong_strategy_cost_{year}", value, "EUR"))
    rows.append(_ssot_row("wrong_strategy_cost_total", total, "EUR"))
    rows.extend(
        [
            _ssot_row("p_ref_base", anchors.p_ref_base, "EUR/MWh"),
            _ssot_row("p_ref_peak", anchors.p_ref_peak, "EUR/MWh"),
            _ssot_row("oespi_base_ref", anchors.oespi_base_ref, "index"),
            _ssot_row("oespi_peak_ref", anchors.oespi_peak_ref, "index"),
        ]
    )
    path = processed_dir(settings) / "ssot_inputs_strategies.parquet"
    write_ssot_parquet(pd.DataFrame(rows), path)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.retrospective`` (ST-002)."""
    import argparse
    import sys

    from epra.common.config import load_settings
    from epra.common.db import warehouse_path
    from epra.common.logging import setup

    parser = argparse.ArgumentParser(prog="python -m epra.strategies.retrospective")
    parser.parse_args(argv)
    setup()
    settings = load_settings()
    path = warehouse_path(settings)
    if not path.is_file():
        msg = (
            f"warehouse not found at {path}. "
            "Run `make warehouse` first (strategies read marts only, D-03)."
        )
        print(f"ERROR: {msg}", file=sys.stderr)
        return 1
    run(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
