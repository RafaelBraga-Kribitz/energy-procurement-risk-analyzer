"""Synthetic pass/fail tests for ING-080..085 validation gates (02-06 task 1).

Each gate function gets one passing and one failing synthetic case per
03_MODULES.md ("mandatory"). Fixtures are hand-built (never real market data)
so a "failing" case is *known* bad -- confirming the gate would actually stop
a bad pipeline (A-2).
"""

from __future__ import annotations

from calendar import isleap

import pandas as pd
import pytest

from epra.ingest.exceptions import GateFailure
from epra.ingest.validate import (
    GateResult,
    ValidationReport,
    gate_ing_080,
    gate_ing_081,
    gate_ing_082,
    gate_ing_083,
    gate_ing_084,
    gate_ing_085,
)

_ALL_GATE_IDS = ("ING-080", "ING-081", "ING-082", "ING-083", "ING-084", "ING-085")


def _year_hourly(year: int, value_col: str, value: float = 50.0) -> pd.DataFrame:
    """Full real-calendar-year hourly UTC frame -- one row per UTC hour, no gaps."""
    periods = (366 if isleap(year) else 365) * 24
    idx = pd.date_range(f"{year}-01-01", periods=periods, freq="h", tz="UTC")
    return pd.DataFrame({"ts_utc": idx, value_col: value})


# ---------------------------------------------------------------------------
# GateResult / ValidationReport framework
# ---------------------------------------------------------------------------


def test_gate_result_render_markdown_with_and_without_evidence() -> None:
    passed = GateResult("ING-999", True, "ok")
    assert "PASS" in passed.render_markdown()

    failed = GateResult("ING-999", False, "bad", pd.DataFrame({"a": [1]}))
    rendered = failed.render_markdown()
    assert "FAIL" in rendered
    assert "1" in rendered


def test_validation_report_all_pass_does_not_raise() -> None:
    report = ValidationReport()
    report.add(GateResult("ING-080", True, "ok"))
    report.add(GateResult("ING-081", True, "ok"))
    assert report.all_passed is True
    report.raise_if_failed()  # must not raise


def test_validation_report_raises_gate_failure_naming_failed_gate_ids() -> None:
    report = ValidationReport()
    report.add(GateResult("ING-080", True, "ok"))
    report.add(GateResult("ING-081", False, "out of bounds"))
    with pytest.raises(GateFailure) as excinfo:
        report.raise_if_failed()
    assert "ING-081" in str(excinfo.value)
    assert "ING-080" not in str(excinfo.value).split(":")[0]


def test_validation_report_lists_every_gate_exactly_once() -> None:
    report = ValidationReport()
    for gate_id in _ALL_GATE_IDS:
        report.add(GateResult(gate_id, True, "ok"))
    rendered = report.render_markdown()
    for gate_id in _ALL_GATE_IDS:
        assert rendered.count(gate_id) == 1


# ---------------------------------------------------------------------------
# ING-080 -- hour coverage per zone-year + DST 23/25 check
# ---------------------------------------------------------------------------


def test_gate_ing_080_passes_on_full_year_coverage() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh")
    result = gate_ing_080({"entsoe_prices_at": at_prices})
    assert result.gate_id == "ING-080"
    assert result.passed is True


def test_gate_ing_080_fails_when_missing_hours_exceed_24() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh")
    # Drop 30 consecutive hours well away from any DST transition.
    drop_start = pd.Timestamp("2023-07-01", tz="UTC")
    drop_end = pd.Timestamp("2023-07-02 06:00", tz="UTC")
    mask = (at_prices["ts_utc"] >= drop_start) & (at_prices["ts_utc"] < drop_end)
    at_prices = at_prices.loc[~mask]

    result = gate_ing_080({"entsoe_prices_at": at_prices})
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "coverage", "ok"].all()


def test_gate_ing_080_input_mutation_is_avoided() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh")
    before = at_prices.copy()
    gate_ing_080({"entsoe_prices_at": at_prices})
    pd.testing.assert_frame_equal(at_prices, before)


# ---------------------------------------------------------------------------
# ING-081 -- hourly AT price plausibility [-500, 5000] EUR/MWh
# ---------------------------------------------------------------------------


def test_gate_ing_081_passes_within_bounds() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh", value=50.0)
    result = gate_ing_081(at_prices)
    assert result.passed is True


def test_gate_ing_081_fails_when_price_exceeds_ceiling() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh", value=50.0)
    at_prices.loc[0, "price_eur_mwh"] = 6000.0  # above 5000 EUR/MWh ceiling
    result = gate_ing_081(at_prices)
    assert result.passed is False
    assert result.evidence is not None
    assert len(result.evidence) == 1


# ---------------------------------------------------------------------------
# ING-082 -- AT annual mean plausibility table
# ---------------------------------------------------------------------------


def test_gate_ing_082_passes_within_annual_mean_table() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh", value=100.0)  # within [70, 140]
    result = gate_ing_082(at_prices)
    assert result.passed is True


def test_gate_ing_082_fails_when_annual_mean_outside_table() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh", value=500.0)  # far above [70, 140]
    result = gate_ing_082(at_prices)
    assert result.passed is False


# ---------------------------------------------------------------------------
# ING-083 -- negative prices required in 2023/2024/2025
# ---------------------------------------------------------------------------


def _three_year_prices(value: float = 50.0) -> pd.DataFrame:
    frames = [_year_hourly(year, "price_eur_mwh", value=value) for year in (2023, 2024, 2025)]
    return pd.concat(frames, ignore_index=True)


def test_gate_ing_083_passes_when_each_year_has_a_negative_price() -> None:
    combined = _three_year_prices()
    for year in (2023, 2024, 2025):
        idx = combined.loc[combined["ts_utc"].dt.year == year].index[0]
        combined.loc[idx, "price_eur_mwh"] = -5.0
    result = gate_ing_083(combined)
    assert result.passed is True


def test_gate_ing_083_fails_when_a_year_has_no_negative_price() -> None:
    combined = _three_year_prices()  # all positive -- 2024/2025 never go negative
    idx_2023 = combined.loc[combined["ts_utc"].dt.year == 2023].index[0]
    combined.loc[idx_2023, "price_eur_mwh"] = -5.0
    result = gate_ing_083(combined)
    assert result.passed is False


# ---------------------------------------------------------------------------
# ING-084 -- AT load plausibility (hourly + annual mean bands)
# ---------------------------------------------------------------------------


def test_gate_ing_084_passes_within_bands() -> None:
    at_load = _year_hourly(2023, "load_mw", value=7000.0)
    result = gate_ing_084(at_load)
    assert result.passed is True


def test_gate_ing_084_fails_when_hourly_load_exceeds_ceiling() -> None:
    at_load = _year_hourly(2023, "load_mw", value=7000.0)
    at_load.loc[0, "load_mw"] = 15000.0  # above 13000 MW ceiling
    result = gate_ing_084(at_load)
    assert result.passed is False


# ---------------------------------------------------------------------------
# ING-085 -- price/load join coverage >=99.5% per year
# ---------------------------------------------------------------------------


def test_gate_ing_085_passes_on_full_join_coverage() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh", value=50.0)
    at_load = _year_hourly(2023, "load_mw", value=7000.0)
    result = gate_ing_085(at_prices, at_load)
    assert result.passed is True


def test_gate_ing_085_fails_when_join_coverage_below_threshold() -> None:
    at_prices = _year_hourly(2023, "price_eur_mwh", value=50.0)
    at_load = _year_hourly(2023, "load_mw", value=7000.0).iloc[:-100]  # drop ~1.1% of hours
    result = gate_ing_085(at_prices, at_load)
    assert result.passed is False
