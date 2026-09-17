"""Synthetic ST-601 annual matrix (engine contract, not market evidence).

Hand-computable 2022 month: volume 10 MWh each; S1=120, S2=110, S3=100,
S4_30=114, S4_50=110, S4_70=106 EUR. ``annual_summary`` derives unit/delta/rank.

Implements: ST-601, D-19.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from epra.strategies.align import STRATEGY_IDS
from epra.strategies.annual import annual_summary

DISCLAIMER = "SYNTHETIC engine contract (D-19 / ST-601). Not Austrian market evidence."
# Hand costs for one 2022 month (EUR), volume 10 MWh.
HAND_COST_EUR: dict[str, float] = {
    "S1": 120.0,
    "S2": 110.0,
    "S3": 100.0,
    "S4_30": 114.0,
    "S4_50": 110.0,
    "S4_70": 106.0,
}
VOLUME_MWH = 10.0


def synthetic_monthly_costs() -> pd.DataFrame:
    """One-month 2022 frame covering all dim_strategy ids."""
    rows = [
        {
            "year_local": 2022,
            "month_local": 1,
            "strategy_id": sid,
            "volume_mwh": VOLUME_MWH,
            "cost_eur": HAND_COST_EUR[sid],
            "unit_cost_eur_mwh": HAND_COST_EUR[sid] / VOLUME_MWH,
        }
        for sid in STRATEGY_IDS
    ]
    return pd.DataFrame(rows)


def synthetic_annual_payload() -> dict[str, Any]:
    """JSON-serializable annual matrix from ``annual_summary``."""
    annual = annual_summary(synthetic_monthly_costs())
    annual = annual.sort_values(["year_local", "strategy_id"]).reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for rec in annual.itertuples(index=False):
        rows.append(
            {
                "year_local": int(cast(Any, rec.year_local)),
                "strategy_id": str(rec.strategy_id),
                "volume_mwh": float(cast(Any, rec.volume_mwh)),
                "cost_eur": float(cast(Any, rec.cost_eur)),
                "unit_cost_eur_mwh": float(cast(Any, rec.unit_cost_eur_mwh)),
                "delta_vs_min_eur": float(cast(Any, rec.delta_vs_min_eur)),
                "rank": int(cast(Any, rec.rank)),
            }
        )
    return {"disclaimer": DISCLAIMER, "rows": rows}
