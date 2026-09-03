"""Retrospective engine — what each strategy actually cost, 2021-2025 (M6, Q1).

Binding contract: SPEC-05 §3 (strategy formulas S1-S4), §5 (ST-301..304).
S1 hourly join uses pre-aligned frames (NULL-price hours already dropped).

Implements: ST-101..107, ST-301, ST-502, ST-503 (run() still T6.05).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import pandas as pd

from epra.common.config import Settings, StrategyCfg
from epra.strategies.calibration import Anchors

_MSG = "M6 not implemented yet — build per SPEC-05 §§3-5 (see module docstring)"
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


def _as_int(value: object) -> int:
    return int(cast(Any, value))


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


def run(settings: Settings) -> None:
    """Compute cost(strategy, year, month) for 2021-2025 + sensitivities."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.retrospective`` (ST-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
