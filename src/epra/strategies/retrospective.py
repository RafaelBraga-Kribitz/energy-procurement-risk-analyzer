"""Retrospective engine — what each strategy actually cost, 2021-2025 (M6, Q1).

Binding contract: SPEC-05 §3 (strategy formulas S1-S4), §5 (ST-301..304).
S1 hourly join uses pre-aligned frames (NULL-price hours already dropped).

Implements (partial, T6.03): ST-101, ST-301. S2–S4 and run() follow in T6.04+.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from epra.common.config import Settings

_MSG = "M6 not implemented yet — build per SPEC-05 §§3-5 (see module docstring)"
S1_ID = "S1"
COST_COLS = (
    "year_local",
    "month_local",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
    "unit_cost_eur_mwh",
)


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


def run(settings: Settings) -> None:
    """Compute cost(strategy, year, month) for 2021-2025 + sensitivities."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.retrospective`` (ST-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
