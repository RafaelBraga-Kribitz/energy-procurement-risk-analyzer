"""Forward risk engine — seasonal block bootstrap via ST-406 cost cells (M6, Q3).

Binding contract: SPEC-05 §6 (ST-401..406). One ``default_rng``; path-major,
month-minor draws. A drawn month brings hourly prices AND ÖSPI together (T-6).
Day mapping is ADR-014 / SG-07. Quantiles and CVaR95 are ADR-015 / SG-08.

Cell additivity (ST-406): for S1 and S2, path annual cost equals the sum of
``CostCells`` entries for the drawn ``(horizon_month, pool_year)``. S3 is
``volume(m) × p_S3(delivery year)``; when the lock window is fully observed,
that product is stored on every pool-year cell for the month (constant in
``pool_year``). When lock months are still future, ``p_S3`` is assembled at
simulate time from observed ÖSPI plus ÖSPI of the years drawn for those months.

Implements: ST-401..406, ST-602, ST-603, ADR-014, ADR-015, D-07..D-12.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, cast

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from numpy.random import Generator

from epra.analytics._kit import frame_to_markdown, save_png, write_markdown
from epra.common.config import Settings, StrategyCfg, load_strategy_config
from epra.report.style import STRATEGY_COLORS
from epra.strategies.align import STRATEGY_IDS, processed_dir
from epra.strategies.annual import strategies_dir, upsert_ssot_parquet
from epra.strategies.calibration import Anchors
from epra.strategies.retrospective import (
    HYBRID_IDS,
    S1_ID,
    S2_ID,
    S3_ID,
    ST502_SENTENCE,
    blended_contract_price,
    p_s2,
)

logger = logging.getLogger(__name__)
CELL_COLS = (
    "horizon_year",
    "horizon_month",
    "pool_year",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
)


@dataclass(frozen=True)
class CostCells:
    """Monthly strategy costs keyed by ``(horizon_month, pool_year, strategy_id)``.

    Implements: ST-406, D-07.
    """

    frame: pd.DataFrame


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _as_float(value: object) -> float:
    return float(cast(Any, value))


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(cast(Any, value)).date()


def month_range_after(last_year: int, last_month: int, n: int) -> list[tuple[int, int]]:
    """Next ``n`` calendar months after ``(last_year, last_month)``."""
    year, month = last_year, last_month
    out: list[tuple[int, int]] = []
    for _ in range(n):
        month += 1
        if month == 13:
            month = 1
            year += 1
        out.append((year, month))
    return out


def _drawn_days(drawn: pd.DataFrame) -> int:
    return max(_as_date(v).day for v in drawn["date_local"])


def _last_same_weekend_day(drawn: pd.DataFrame, want_weekend: bool) -> date:
    rows = drawn.drop_duplicates(subset=["date_local"])
    match = rows.loc[rows["is_weekend"].astype(bool) == want_weekend]
    if match.empty:
        raise ValueError("drawn month has no day with the required is_weekend")
    days = sorted(_as_date(v) for v in match["date_local"])
    return days[-1]


def _lookup_drawn_price(
    drawn: pd.DataFrame, day: int, hour_local: int, occurrence: int
) -> float | None:
    days = [_as_date(v).day for v in drawn["date_local"]]
    mask = (pd.Series(days, index=drawn.index) == day) & (drawn["hour_local"] == hour_local)
    hit = drawn.loc[mask]
    if hit.empty:
        return None
    ordered = hit.sort_values("ts_utc") if "ts_utc" in hit.columns else hit
    idx = min(occurrence, len(ordered) - 1)
    return _as_float(ordered.iloc[idx]["price_at_eur_mwh"])


def map_month(drawn: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    """Map drawn-month prices onto target-month hours (ADR-014 / SG-07).

    Primary key ``(day-of-month, hour_local)``. Overflow days reuse the drawn
    month's last day with matching ``is_weekend``. DST-missing drawn hour:
    forward-fill from the previous mapped local hour. DST-extra target hour:
    reuse the drawn 02:00 price (ADR-014).

    Implements: ST-401, ADR-014.
    """
    if drawn.empty or target.empty:
        raise ValueError("map_month requires non-empty drawn and target frames")
    max_day = _drawn_days(drawn)
    occ: dict[tuple[int, int], int] = {}
    prices: list[float] = []
    last: float | None = None
    ordered = target.sort_values("ts_utc") if "ts_utc" in target.columns else target
    for rec in ordered.itertuples(index=False):
        day_date = _as_date(rec.date_local)
        hour = _as_int(rec.hour_local)
        day = day_date.day
        if day > max_day:
            day = _last_same_weekend_day(drawn, bool(rec.is_weekend)).day
        key = (day, hour)
        n = occ.get(key, 0)
        occ[key] = n + 1
        found = _lookup_drawn_price(drawn, day, hour, n)
        if found is None:
            if last is None:
                raise ValueError(f"no drawn price for day {day} hour {hour} and no prior hour")
            found = last
        last = found
        prices.append(found)
    out = ordered.copy()
    out["price_at_eur_mwh"] = prices
    return out


def _oespi_row(oespi: pd.DataFrame, year: int, month: int) -> pd.Series:
    rows = oespi.loc[(oespi["year_local"] == year) & (oespi["month_local"] == month)]
    if len(rows) != 1:
        raise ValueError(f"missing ÖSPI for {year}-{month:02d} (got {len(rows)})")
    return rows.iloc[0]


def ym_le(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left <= right


def lock_oespi_means(
    delivery_year: int,
    oespi: pd.DataFrame,
    cfg: StrategyCfg,
    data_last_month: tuple[int, int],
    drawn_oespi: dict[tuple[int, int], tuple[float, float]],
) -> tuple[float, float]:
    """Observed lock ÖSPI if past; drawn if future; never extrapolate (D-09).

    Implements: ST-402, D-09.
    """
    lock_year = delivery_year - 1
    bases: list[float] = []
    peaks: list[float] = []
    for month in cfg.lock_window_months:
        key = (lock_year, month)
        if ym_le(key, data_last_month):
            row = _oespi_row(oespi, lock_year, month)
            bases.append(_as_float(row["oespi_base"]))
            peaks.append(_as_float(row["oespi_peak"]))
            continue
        if key not in drawn_oespi:
            raise ValueError(f"future lock month {lock_year}-{month:02d} has no drawn ÖSPI")
        base, peak = drawn_oespi[key]
        bases.append(base)
        peaks.append(peak)
    return float(np.mean(bases)), float(np.mean(peaks))


def p_s3_forward(
    delivery_year: int,
    oespi: pd.DataFrame,
    anchors: Anchors,
    cfg: StrategyCfg,
    w_peak: float,
    data_last_month: tuple[int, int],
    drawn_oespi: dict[tuple[int, int], tuple[float, float]],
) -> float:
    """S3 lock price with mixed observed/drawn ÖSPI (ST-402).

    Implements: ST-105, ST-402, D-09.
    """
    base_m, peak_m = lock_oespi_means(delivery_year, oespi, cfg, data_last_month, drawn_oespi)
    indexed = blended_contract_price(
        anchors, base_m, peak_m, w_peak, peak_available=cfg.peak_available
    )
    return indexed + cfg.fixed_premium_eur_mwh


def _strategy_costs(s1: float, s2: float, s3: float, volume: float) -> dict[str, float]:
    out = {S1_ID: s1, S2_ID: s2, S3_ID: s3}
    for h, sid in HYBRID_IDS.items():
        out[sid] = h * s3 + (1.0 - h) * s1
    out["volume"] = volume
    return out


def _month_volume(hours: pd.DataFrame) -> float:
    return _as_float(hours["load_mwh"].sum())


def _cell_row(
    hy: int, hm: int, pool_year: int, strategy_id: str, volume: float, cost: float
) -> dict[str, object]:
    return {
        "horizon_year": hy,
        "horizon_month": hm,
        "pool_year": pool_year,
        "strategy_id": strategy_id,
        "volume_mwh": volume,
        "cost_eur": cost,
    }


def build_cost_cells(
    horizon_hours: pd.DataFrame,
    pool_hourly: pd.DataFrame,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    cfg: StrategyCfg,
    data_last_month: tuple[int, int],
    horizon: list[tuple[int, int]],
    *,
    drawn_oespi: dict[tuple[int, int], tuple[float, float]] | None = None,
) -> CostCells:
    """Precompute ``(horizon_month × pool_year × strategy)`` monthly costs.

    Grain count is ``len(horizon) × pool_years_present × 7`` when every horizon
    month has the same pool. Cell S1 equals mapped-hour ``Σ load×price``.
    Drawn prices and ÖSPI share ``pool_year`` (T-6).

    Implements: ST-406, D-07, T-6.
    """
    drawn_oespi = drawn_oespi or {}
    rows: list[dict[str, object]] = []
    for hy, hm in horizon:
        target = horizon_hours.loc[
            (horizon_hours["year_local"] == hy) & (horizon_hours["month_local"] == hm)
        ]
        if target.empty:
            raise ValueError(f"no horizon volume hours for {hy}-{hm:02d}")
        volume = _month_volume(target)
        p3 = p_s3_forward(hy, oespi, anchors, cfg, w_peak, data_last_month, drawn_oespi)
        pool_years = sorted(
            int(y) for y in pool_hourly.loc[pool_hourly["month_local"] == hm, "year_local"].unique()
        )
        if not pool_years:
            raise ValueError(f"no pool years for calendar month {hm}")
        for pool_year in pool_years:
            drawn = pool_hourly.loc[
                (pool_hourly["year_local"] == pool_year) & (pool_hourly["month_local"] == hm)
            ]
            mapped = map_month(drawn, target)
            s1 = _as_float((mapped["load_mwh"] * mapped["price_at_eur_mwh"]).sum())
            s2 = volume * p_s2(pool_year, hm, oespi, anchors, w_peak)
            s3 = volume * p3
            costs = _strategy_costs(s1, s2, s3, volume)
            for sid in STRATEGY_IDS:
                rows.append(_cell_row(hy, hm, pool_year, sid, volume, costs[sid]))
    return CostCells(pd.DataFrame(rows, columns=list(CELL_COLS)))


def _pool_for_month(cells: CostCells, month: int, allowed: set[int] | None) -> list[int]:
    years = {
        _as_int(y)
        for y in cells.frame.loc[cells.frame["horizon_month"] == month, "pool_year"].unique()
    }
    if allowed is not None:
        years &= allowed
    if not years:
        raise ValueError(f"empty year pool for calendar month {month}")
    return sorted(years)


def simulate(
    cells: CostCells,
    rng_seed: int,
    n_paths: int,
    *,
    allowed_years: set[int] | None = None,
) -> pd.DataFrame:
    """Bootstrap annual costs. One ``default_rng``; path-major, month-minor (D-08).

    Implements: ST-401, ST-405, D-08.
    """
    rng: Generator = np.random.default_rng(rng_seed)
    horizon = (
        cells.frame[["horizon_year", "horizon_month"]]
        .drop_duplicates()
        .sort_values(["horizon_year", "horizon_month"])
    )
    lookup = cells.frame.set_index(["horizon_year", "horizon_month", "pool_year", "strategy_id"])[
        "cost_eur"
    ]
    records: list[dict[str, object]] = []
    for path in range(n_paths):
        totals = dict.fromkeys(STRATEGY_IDS, 0.0)
        for rec in horizon.itertuples(index=False):
            hy = _as_int(rec.horizon_year)
            hm = _as_int(rec.horizon_month)
            pool = _pool_for_month(cells, hm, allowed_years)
            y_prime = int(pool[int(rng.integers(0, len(pool)))])
            for sid in STRATEGY_IDS:
                totals[sid] += _as_float(lookup.loc[(hy, hm, y_prime, sid)])
        row: dict[str, object] = {"path": path}
        row.update(totals)
        records.append(row)
    return pd.DataFrame(records)


def summarize(paths: pd.DataFrame) -> pd.DataFrame:
    """Mean/std/P5/P50/P95/CVaR95 per strategy (ADR-015).

    P-quantiles: ``numpy.quantile(..., method='linear')``.
    CVaR95: mean of the ``ceil(0.05 * N)`` highest annual costs.

    Implements: ST-403, ADR-015, D-11.
    """
    rows: list[dict[str, object]] = []
    n = len(paths)
    k = int(np.ceil(0.05 * n))
    for sid in STRATEGY_IDS:
        if sid not in paths.columns:
            continue
        costs = np.asarray(paths[sid], dtype=np.float64)
        q = np.quantile(costs, [0.05, 0.50, 0.95], method="linear")
        worst = np.sort(costs)[-k:] if k else costs
        rows.append(
            {
                "strategy_id": sid,
                "mean": float(costs.mean()),
                "std": float(costs.std(ddof=1)) if n > 1 else 0.0,
                "p5": float(q[0]),
                "p50": float(q[1]),
                "p95": float(q[2]),
                "cvar95": float(worst.mean()),
            }
        )
    return pd.DataFrame(rows)


def check_st602c(summary: pd.DataFrame) -> None:
    """Fail-closed: P95(S1) >= P95(S3) when both exist.

    Implements: ST-602.
    """
    ids = set(summary["strategy_id"].astype(str))
    if S1_ID not in ids or S3_ID not in ids:
        return
    p1 = _as_float(summary.loc[summary["strategy_id"] == S1_ID, "p95"].iloc[0])
    p3 = _as_float(summary.loc[summary["strategy_id"] == S3_ID, "p95"].iloc[0])
    if p1 < p3:
        raise RuntimeError(f"ST-602(c) fail: P95(S1) {p1} < P95(S3) {p3}")


def no_crisis_years(dates: pd.Series, labels: pd.Series, pool_years: Sequence[int]) -> set[int]:
    """Years whose December HMM label is not ``crisis`` (M5 D-10 calm-wins).

    Missing December → year excluded (log), never guessed.

    Implements: ST-401, D-12.
    """
    from epra.analytics.regimes import december_regime

    kept: set[int] = set()
    for year in pool_years:
        try:
            name = december_regime(year, dates, labels)
        except ValueError as exc:
            logger.info("no-crisis pool skip year %s: %s", year, exc)
            continue
        if name != "crisis":
            kept.add(year)
    return kept


def figure_forward_fan(paths: pd.DataFrame) -> Figure:
    """Horizontal box plot of path totals; P95 marked.

    Implements: ST-403, ST-502.
    """
    fig, ax = plt.subplots()
    ids = [sid for sid in STRATEGY_IDS if sid in paths.columns]
    data = [paths[sid].to_numpy(dtype=np.float64) for sid in ids]
    ax.boxplot(data, orientation="horizontal")
    ax.set_yticks(range(1, len(ids) + 1), ids)
    for i, sid in enumerate(ids, start=1):
        p95 = float(np.quantile(paths[sid], 0.95, method="linear"))
        ax.plot(p95, i, "o", color=STRATEGY_COLORS[sid])
    ax.set_xlabel("EUR (12-month total)")
    ax.set_title("Forward path cost distribution")
    fig.text(0.01, 0.02, ST502_SENTENCE, fontsize=7)
    return fig


def figure_risk_return(summary: pd.DataFrame) -> Figure:
    """Mean cost vs P95 scatter (ST-404).

    Implements: ST-404, ST-502.
    """
    fig, ax = plt.subplots()
    for rec in summary.itertuples(index=False):
        sid = str(rec.strategy_id)
        ax.scatter(
            _as_float(rec.mean),
            _as_float(rec.p95),
            color=STRATEGY_COLORS[sid],
            label=sid,
        )
    ax.set_xlabel("mean EUR")
    ax.set_ylabel("P95 EUR")
    ax.set_title("Risk-return (mean vs P95)")
    ax.legend()
    fig.text(0.01, 0.02, ST502_SENTENCE, fontsize=7)
    return fig


def _ssot_rows(summary: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rec in summary.itertuples(index=False):
        sid = str(rec.strategy_id)
        rows.append(
            {
                "key": f"p95_next12m_{sid}",
                "value": _as_float(rec.p95),
                "unit": "EUR",
                "tag": "SIMULATED",
                "produced_by": "epra.strategies.forward_risk",
            }
        )
        rows.append(
            {
                "key": f"cvar95_next12m_{sid}",
                "value": _as_float(rec.cvar95),
                "unit": "EUR",
                "tag": "SIMULATED",
                "produced_by": "epra.strategies.forward_risk",
            }
        )
    return rows


def _write_forward_md(
    uncond: pd.DataFrame, nocrisis: pd.DataFrame | None, settings: Settings
) -> None:
    parts = [
        "# Forward risk summary (ST-403)\n",
        ST502_SENTENCE,
        "\n\n## Unconditional\n\n",
        frame_to_markdown(uncond),
        "\n",
    ]
    if nocrisis is not None and not nocrisis.empty:
        parts.extend(["\n## No-crisis pool\n\n", frame_to_markdown(nocrisis), "\n"])
    write_markdown(strategies_dir(settings) / "s5_forward_risk.md", "".join(parts))


def run(
    settings: Settings,
    *,
    horizon_hours: pd.DataFrame | None = None,
    pool_hourly: pd.DataFrame | None = None,
    monthly_oespi: pd.DataFrame | None = None,
    anchors: Anchors | None = None,
    w_peak: float | None = None,
    cfg: StrategyCfg | None = None,
    data_last_month: tuple[int, int] | None = None,
    n_paths: int | None = None,
    dates: pd.Series | None = None,
    labels: pd.Series | None = None,
) -> pd.DataFrame:
    """Build cells, simulate unconditional + no-crisis, write artifacts.

    Inject frames in tests. Production loads marts (T6.10 wires Makefile).

    Implements: ST-401..406, D-03.
    """
    from epra.strategies.align import load_price_hourly, load_price_monthly, load_w_peak
    from epra.strategies.calibration import compute_anchors
    from epra.strategies.retrospective import _anchors_from_frame

    cfg = cfg or load_strategy_config()
    if pool_hourly is None:
        pool_hourly = load_price_hourly(settings)
    if monthly_oespi is None:
        monthly_oespi = load_price_monthly(settings)
    if w_peak is None:
        w_peak = load_w_peak(settings)
    if anchors is None:
        from epra.strategies.align import align_hourly, load_consumer_load

        aligned = align_hourly(load_consumer_load(settings), pool_hourly)
        anchors = _anchors_from_frame(
            compute_anchors(settings, cfg, aligned=aligned, monthly_oespi=monthly_oespi)
        )
    if data_last_month is None:
        data_last_month = (
            _as_int(pool_hourly["year_local"].max()),
            _as_int(
                pool_hourly.loc[
                    pool_hourly["year_local"] == pool_hourly["year_local"].max(),
                    "month_local",
                ].max()
            ),
        )
    if horizon_hours is None:
        horizon_hours = pool_hourly
    horizon = month_range_after(*data_last_month, cfg.forward.horizon_months)
    cells = build_cost_cells(
        horizon_hours,
        pool_hourly,
        monthly_oespi,
        anchors,
        w_peak,
        cfg,
        data_last_month,
        horizon,
    )
    n = n_paths if n_paths is not None else cfg.forward.n_paths
    paths = simulate(cells, cfg.forward.seed, n)
    uncond = summarize(paths)
    check_st602c(uncond)
    nocrisis_summary: pd.DataFrame | None = None
    if dates is not None and labels is not None:
        allowed = no_crisis_years(dates, labels, sorted(cells.frame["pool_year"].unique()))
        nocrisis_summary = summarize(simulate(cells, cfg.forward.seed, n, allowed_years=allowed))
    out = strategies_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    save_png(figure_forward_fan(paths), out / "s5_forward_fan.png", tag="SIMULATED")
    save_png(figure_risk_return(uncond), out / "s5_risk_return.png", tag="SIMULATED")
    _write_forward_md(uncond, nocrisis_summary, settings)
    upsert_ssot_parquet(
        _ssot_rows(uncond), processed_dir(settings) / "ssot_inputs_strategies.parquet"
    )
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.forward_risk`` (ST-002)."""
    import argparse
    import sys

    from epra.common.config import load_settings
    from epra.common.db import warehouse_path
    from epra.common.logging import setup

    parser = argparse.ArgumentParser(prog="python -m epra.strategies.forward_risk")
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
