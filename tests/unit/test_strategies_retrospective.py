"""T6.03 S1 monthly spot cost tests.

Implements: ST-101, ST-301.
"""

from __future__ import annotations

import pandas as pd
import pytest

from epra.strategies.retrospective import cost_s1


def test_cost_s1_hand_computed_month_to_the_cent() -> None:
    hourly = pd.DataFrame(
        {
            "ts_utc": [
                pd.Timestamp("2022-01-01 00:00:00", tz="UTC"),
                pd.Timestamp("2022-01-01 01:00:00", tz="UTC"),
            ],
            "load_mwh": [1.0, 2.0],
            "price_at_eur_mwh": [10.0, 20.0],
            "year_local": [2022, 2022],
            "month_local": [1, 1],
        }
    )
    out = cost_s1(hourly)
    assert len(out) == 1
    assert str(out["strategy_id"].iloc[0]) == "S1"
    assert float(out["volume_mwh"].iloc[0]) == pytest.approx(3.0)
    assert float(out["cost_eur"].iloc[0]) == pytest.approx(50.0)
    assert float(out["unit_cost_eur_mwh"].iloc[0]) == pytest.approx(50.0 / 3.0)


def test_cost_s1_rejects_null_prices() -> None:
    hourly = pd.DataFrame(
        {
            "load_mwh": [1.0],
            "price_at_eur_mwh": [None],
            "year_local": [2022],
            "month_local": [1],
        }
    )
    with pytest.raises(ValueError, match="NULL prices"):
        cost_s1(hourly)
