"""T6.02 ST-201..204 calibration anchor tests.

Implements: ST-201..204, T-5, D-06.
"""

from __future__ import annotations

import inspect

import pandas as pd
import pytest

from epra.common.config import Settings, load_strategy_config
from epra.strategies.align import AlignedVolumes
from epra.strategies.calibration import (
    IncompleteReferenceYearError,
    anchors_from_frames,
    compute_anchors,
    p_ref_peak,
)


def _hourly_2019() -> pd.DataFrame:
    """Two hours: off-peak 40 EUR/MWh load 1; peak 80 EUR/MWh load 3."""
    ts = [
        pd.Timestamp("2019-06-03 10:00:00", tz="UTC"),
        pd.Timestamp("2019-06-03 12:00:00", tz="UTC"),
    ]
    return pd.DataFrame(
        {
            "ts_utc": ts,
            "load_mwh": [1.0, 3.0],
            "price_at_eur_mwh": [40.0, 80.0],
            "year_local": [2019, 2019],
            "month_local": [6, 6],
            "is_peak_hour": [False, True],
        }
    )


def _oespi_2019() -> pd.DataFrame:
    months = list(range(1, 13))
    return pd.DataFrame(
        {
            "year_local": [2019] * 12,
            "month_local": months,
            "oespi_base": [100.0 + m for m in months],
            "oespi_peak": [110.0 + m for m in months],
        }
    )


def test_st202_docstring_has_spec_sentence() -> None:
    doc = inspect.getdoc(p_ref_peak)
    assert doc is not None
    assert "rescaled by the consumer's realized-vs-base ratio" in doc
    assert "internally consistent" in doc
    assert "base/peak" in doc


def test_synthetic_2019_anchors_match_hand_calc(tmp_settings: Settings) -> None:
    # p_ref_base = (40*1 + 80*3) / 4 = 70
    # mean all hours = (40+80)/2 = 60 (unweighted)
    # mean peak hours = 80
    # p_ref_peak = 80 * (70/60) = 280/3
    hourly = _hourly_2019()
    oespi = _oespi_2019()
    aligned = AlignedVolumes(hourly=hourly, monthly=pd.DataFrame(), dropped_hours=0)
    cfg = load_strategy_config()
    frame = compute_anchors(tmp_settings, cfg, aligned=aligned, monthly_oespi=oespi)
    assert float(frame["p_ref_base"].iloc[0]) == pytest.approx(70.0)
    assert float(frame["p_ref_peak"].iloc[0]) == pytest.approx(80.0 * (70.0 / 60.0))
    expected_base = sum(100.0 + m for m in range(1, 13)) / 12
    expected_peak = sum(110.0 + m for m in range(1, 13)) / 12
    assert float(frame["oespi_base_ref"].iloc[0]) == pytest.approx(expected_base)
    assert float(frame["oespi_peak_ref"].iloc[0]) == pytest.approx(expected_peak)


def test_incomplete_2019_raises() -> None:
    hourly = _hourly_2019()
    hourly["year_local"] = 2022
    with pytest.raises(IncompleteReferenceYearError, match="2019"):
        anchors_from_frames(hourly, _oespi_2019(), reference_year=2019)


def test_peak_below_base_is_stop() -> None:
    hourly = _hourly_2019()
    hourly["is_peak_hour"] = [True, False]
    hourly["price_at_eur_mwh"] = [20.0, 80.0]
    # p_ref_base = (20*1 + 80*3)/4 = 65; mean all=50; mean peak=20; p_ref_peak=20*(65/50)=26 < 65
    with pytest.raises(AssertionError, match="p_ref_peak"):
        anchors_from_frames(hourly, _oespi_2019(), reference_year=2019)
