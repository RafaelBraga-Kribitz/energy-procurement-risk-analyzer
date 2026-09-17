"""T6.03/T6.04 S1-S4 monthly cost tests.

Implements: ST-101..107, ST-301, ST-502, ST-503.
"""

from __future__ import annotations

import pandas as pd
import pytest

from epra.common.config import load_strategy_config
from epra.strategies.calibration import Anchors
from epra.strategies.retrospective import (
    ST502_SENTENCE,
    cost_s1,
    cost_s2,
    cost_s3,
    cost_s4,
    p_s2,
    p_s3,
)

_ANCHORS = Anchors(p_ref_base=50.0, p_ref_peak=70.0, oespi_base_ref=100.0, oespi_peak_ref=100.0)
_W = 0.40
_BLEND = 50.0 * 0.60 + 70.0 * 0.40  # 58 at ÖSPI=ref


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


def _oespi_year(year: int, base: float, peak: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year_local": [year] * 12,
            "month_local": list(range(1, 13)),
            "oespi_base": [base] * 12,
            "oespi_peak": [peak] * 12,
        }
    )


def test_p_s2_at_ref_equals_blended_p_ref() -> None:
    oespi = _oespi_year(2021, 100.0, 100.0)
    assert p_s2(2021, 3, oespi, _ANCHORS, _W) == pytest.approx(_BLEND)


def test_p_s3_at_ref_premium_zero_equals_blend() -> None:
    cfg = load_strategy_config().model_copy(update={"fixed_premium_eur_mwh": 0.0})
    oespi = pd.concat([_oespi_year(2021, 100.0, 100.0), _oespi_year(2022, 100.0, 100.0)])
    assert p_s3(2022, oespi, _ANCHORS, cfg, w_peak=_W) == pytest.approx(_BLEND)


def test_st503_p_s3_2022_ignores_2021_june() -> None:
    cfg = load_strategy_config().model_copy(update={"fixed_premium_eur_mwh": 0.0})
    oespi = _oespi_year(2021, 100.0, 100.0)
    oespi.loc[oespi["month_local"] == 6, ["oespi_base", "oespi_peak"]] = 9999.0
    assert p_s3(2022, oespi, _ANCHORS, cfg, w_peak=_W) == pytest.approx(_BLEND)


def test_lock_window_missing_raises() -> None:
    cfg = load_strategy_config()
    oespi = _oespi_year(2021, 100.0, 100.0).loc[lambda d: d["month_local"] != 8]
    with pytest.raises(ValueError, match="lock window incomplete"):
        p_s3(2022, oespi, _ANCHORS, cfg, w_peak=_W)


def test_peak_available_false_uses_base_only() -> None:
    oespi = _oespi_year(2021, 100.0, 200.0)
    assert p_s2(2021, 1, oespi, _ANCHORS, _W, peak_available=False) == pytest.approx(50.0)


def test_st602b_hybrid_between_legs() -> None:
    s1 = pd.DataFrame(
        {
            "year_local": [2022],
            "month_local": [1],
            "strategy_id": ["S1"],
            "volume_mwh": [10.0],
            "cost_eur": [100.0],
            "unit_cost_eur_mwh": [10.0],
        }
    )
    s3 = pd.DataFrame(
        {
            "year_local": [2022],
            "month_local": [1],
            "strategy_id": ["S3"],
            "volume_mwh": [10.0],
            "cost_eur": [80.0],
            "unit_cost_eur_mwh": [8.0],
        }
    )
    s4 = cost_s4(s1, s3, 0.50)
    cost = float(s4["cost_eur"].iloc[0])
    assert 80.0 <= cost <= 100.0
    assert cost == pytest.approx(90.0)
    assert str(s4["strategy_id"].iloc[0]) == "S4_50"


def test_st502_sentence_mentions_oespi_and_limitations() -> None:
    assert "ÖSPI" in ST502_SENTENCE
    assert "LIMITATIONS" in ST502_SENTENCE


def test_cost_s2_s3_use_volume_times_price() -> None:
    cfg = load_strategy_config().model_copy(update={"fixed_premium_eur_mwh": 0.0})
    monthly = pd.DataFrame({"year_local": [2022], "month_local": [1], "volume_mwh": [2.0]})
    oespi = pd.concat([_oespi_year(2021, 100.0, 100.0), _oespi_year(2022, 100.0, 100.0)])
    s2 = cost_s2(monthly, oespi, _ANCHORS, _W)
    s3 = cost_s3(monthly, oespi, _ANCHORS, cfg, w_peak=_W)
    assert float(s2["cost_eur"].iloc[0]) == pytest.approx(2.0 * _BLEND)
    assert float(s3["cost_eur"].iloc[0]) == pytest.approx(2.0 * _BLEND)
