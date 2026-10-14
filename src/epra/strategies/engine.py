"""Pure strategy cost formulas S1-S4 (SPEC-05 §3). No I/O, no randomness.

The retrospective (Q1) and the forward bootstrap (Q3) both price through these
functions, so a formula exists exactly once.

- ST-101 S1 cost = Σ load × spot (precomputed per month as ``spot_cost_eur``).
- ST-102/103 S2 price = p_ref_base × base/base_ref × (1−w) + p_ref_peak ×
  peak/peak_ref × w, per month; cost = volume × price. ST-104 base-only mode.
- ST-105/106 S3 price = the same blend over the MEAN index of the lock window
  (months of Y−1) + ``fixed_premium_eur_mwh``; one price for all of Y.
- ST-107 S4_h cost = h × volume × p_S3 + (1−h) × S1 cost (uniform split).
- ST-503 no lookahead: S3 for year Y reads ONLY the Y−1 lock-window rows.

Implements: ST-101..107, ST-501, ST-503.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from epra.strategies.calibration import Anchors

COST_COLUMNS = [
    "year_local",
    "month_local",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
    "unit_cost_eur_mwh",
]


@dataclass(frozen=True)
class StrategyParams:
    """Everything a strategy price depends on besides market data."""

    anchors: Anchors
    w_peak: float
    fixed_premium_eur_mwh: float
    lock_window_months: tuple[int, ...]
    hybrid_ratios: tuple[float, ...]
    peak_available: bool


def hybrid_id(ratio: float) -> str:
    """``0.30`` → ``"S4_30"`` (dim_strategy ids)."""
    return f"S4_{round(ratio * 100)}"


def strategy_ids(params: StrategyParams) -> list[str]:
    """S1, S2, S3, then the hybrids in config order (dim_strategy grid)."""
    return ["S1", "S2", "S3", *(hybrid_id(h) for h in params.hybrid_ratios)]


def indexed_price(
    oespi_base: np.ndarray | pd.Series | float,
    oespi_peak: np.ndarray | pd.Series | float,
    params: StrategyParams,
) -> np.ndarray:
    """ST-102 blended EUR/MWh price for given index values (vectorized).

    Implements: ST-102, ST-104.
    """
    a = params.anchors
    base_leg = a.p_ref_base * np.asarray(oespi_base, dtype=float) / a.oespi_base_ref
    if not params.peak_available:
        return np.asarray(base_leg)
    peak_leg = a.p_ref_peak * np.asarray(oespi_peak, dtype=float) / a.oespi_peak_ref
    return np.asarray(base_leg * (1.0 - params.w_peak) + peak_leg * params.w_peak)


def lock_window(oespi: pd.DataFrame, year: int, params: StrategyParams) -> pd.DataFrame:
    """The ÖSPI rows of the S3 lock window for delivery year ``year`` (Y−1 months).

    Implements: ST-105, ST-503 (only Y−1 lock-window rows are ever selected).
    """
    rows = oespi[
        (oespi["year_local"] == year - 1) & oespi["month_local"].isin(params.lock_window_months)
    ]
    if len(rows) != len(params.lock_window_months) or rows[["oespi_base"]].isna().any().any():
        raise ValueError(f"S3 lock window for {year} incomplete in ÖSPI ({len(rows)} rows)")
    return rows


def lock_price(oespi: pd.DataFrame, year: int, params: StrategyParams) -> float:
    """ST-105 fixed price for delivery year ``year``, premium included (EUR/MWh).

    Implements: ST-105, ST-503.
    """
    rows = lock_window(oespi, year, params)
    blended = indexed_price(rows["oespi_base"].mean(), rows["oespi_peak"].mean(), params)
    return float(blended) + params.fixed_premium_eur_mwh


def monthly_costs(
    spot: pd.DataFrame, oespi: pd.DataFrame, params: StrategyParams, years: list[int]
) -> pd.DataFrame:
    """Cost per (year, month, strategy) for ``years`` — the ST-001 output frame.

    ``spot`` holds ``year_local, month_local, volume_mwh, spot_cost_eur`` with
    NULL-price hours already removed from both (ST-101), so every strategy
    prices the identical volume (ST-501).

    Implements: ST-101..107, ST-301 (monthly grain), ST-501.
    """
    months = spot[spot["year_local"].isin(years)].merge(
        oespi, on=["year_local", "month_local"], how="left", validate="one_to_one"
    )
    missing = months[["oespi_base", "oespi_peak" if params.peak_available else "oespi_base"]]
    if missing.isna().any().any():
        raise ValueError("ÖSPI missing for a retrospective month — S2 undefined")
    s3_price = months["year_local"].map({y: lock_price(oespi, y, params) for y in years})
    volume = months["volume_mwh"]
    s3_cost = volume * s3_price
    costs = {
        "S1": months["spot_cost_eur"],
        "S2": volume * indexed_price(months["oespi_base"], months["oespi_peak"], params),
        "S3": s3_cost,
    }
    for ratio in params.hybrid_ratios:
        costs[hybrid_id(ratio)] = ratio * s3_cost + (1.0 - ratio) * months["spot_cost_eur"]
    frames = [
        months[["year_local", "month_local", "volume_mwh"]].assign(
            strategy_id=sid, cost_eur=np.asarray(cost, dtype=float)
        )
        for sid, cost in costs.items()
    ]
    out = pd.concat(frames, ignore_index=True)
    out["unit_cost_eur_mwh"] = out["cost_eur"] / out["volume_mwh"]
    order = {sid: i for i, sid in enumerate(strategy_ids(params))}
    out = out.assign(_order=out["strategy_id"].map(order)).sort_values(
        ["year_local", "month_local", "_order"]
    )
    return out[COST_COLUMNS].reset_index(drop=True)


def annual_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    """ST-301 ``strategy_annual_summary``: year × strategy with delta-vs-min and rank.

    Implements: ST-301.
    """
    annual = monthly.groupby(["year_local", "strategy_id"], sort=False, as_index=False)[
        ["volume_mwh", "cost_eur"]
    ].sum()
    annual = annual.rename(columns={"year_local": "year"})
    annual["unit_cost_eur_mwh"] = annual["cost_eur"] / annual["volume_mwh"]
    annual["delta_vs_min_eur"] = annual["cost_eur"] - annual.groupby("year")["cost_eur"].transform(
        "min"
    )
    annual["rank"] = annual.groupby("year")["cost_eur"].rank(method="min").astype(int)
    return annual[
        [
            "year",
            "strategy_id",
            "volume_mwh",
            "cost_eur",
            "unit_cost_eur_mwh",
            "delta_vs_min_eur",
            "rank",
        ]
    ]


def wrong_strategy_cost(annual: pd.DataFrame) -> pd.Series:
    """ST-302: max − min annual cost across strategies, per year (EUR).

    Implements: ST-302.
    """
    by_year = annual.groupby("year")["cost_eur"]
    return (by_year.max() - by_year.min()).rename("wrong_strategy_cost_eur")
