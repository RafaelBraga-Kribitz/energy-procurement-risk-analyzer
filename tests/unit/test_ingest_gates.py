"""Synthetic pass/fail tests for ING-080..085 validation gates (02-06 task 1).

Each gate function gets one passing and one failing synthetic case per
03_MODULES.md ("mandatory"). Fixtures are hand-built (never real market data)
so a "failing" case is *known* bad -- confirming the gate would actually stop
a bad pipeline (A-2).
"""

from __future__ import annotations

from calendar import isleap
from datetime import date

import pandas as pd
import pytest

from epra.common.config import Settings
from epra.ingest._io import write_month
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
    gate_ing_094,
    run_gates,
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


# ---------------------------------------------------------------------------
# ING-094 -- GeoSphere coverage/range/seasonal-mean gate (03-04 task 2)
# ---------------------------------------------------------------------------


def _geosphere_year(year: int, month_value: dict[int, float] | None = None) -> pd.DataFrame:
    """Full real-calendar-year daily frame -- one row per day, no gaps.

    `month_value` overrides the per-month temperature (e.g. `{7: 20.0}` for a
    plausible July mean); every other month defaults to 10.0 degC (well
    within the [-30, 42] range).
    """
    overrides = month_value or {}
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    temps = [overrides.get(int(d.month), 10.0) for d in days]
    return pd.DataFrame(
        {
            "date": days,
            "station_id": "30",
            "tl_mittel_c": temps,
            "parameter_raw": [str(t) for t in temps],
        }
    )


def test_gate_ing_094_passes_on_full_coverage_and_plausible_data() -> None:
    frame = _geosphere_year(2023, {7: 20.0, 1: 0.0})  # July/Jan means inside bounds
    result = gate_ing_094(frame)
    assert result.gate_id == "ING-094"
    assert result.passed is True


def test_gate_ing_094_fails_on_empty_input() -> None:
    empty = pd.DataFrame(columns=["date", "station_id", "tl_mittel_c", "parameter_raw"])
    result = gate_ing_094(empty)
    assert result.passed is False


def test_gate_ing_094_fails_when_coverage_below_99_percent() -> None:
    frame = _geosphere_year(2023, {7: 20.0, 1: 0.0})
    # Drop a 60-day chunk out of the middle of the year -- min/max date (the
    # coverage denominator) stay the same, so this is a real gap, not a
    # shrunk window (RESEARCH Pitfall 6: denominator = days in window).
    frame = frame.drop(frame.index[100:160]).reset_index(drop=True)

    result = gate_ing_094(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "coverage", "ok"].all()


def test_gate_ing_094_fails_when_temperature_out_of_range() -> None:
    frame = _geosphere_year(2023, {7: 20.0, 1: 0.0})
    frame.loc[0, "tl_mittel_c"] = 50.0  # above the 42 degC ceiling

    result = gate_ing_094(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "range", "ok"].all()


def test_gate_ing_094_fails_when_july_mean_outside_range() -> None:
    frame = _geosphere_year(2023, {7: 5.0, 1: 0.0})  # July mean 5 -- below [15, 30]

    result = gate_ing_094(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "july_mean", "ok"].all()


def test_gate_ing_094_fails_when_january_mean_outside_range() -> None:
    frame = _geosphere_year(2023, {7: 20.0, 1: 20.0})  # January mean 20 -- above [-10, 8]

    result = gate_ing_094(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "january_mean", "ok"].all()


# ---------------------------------------------------------------------------
# run_gates -- loader + report writer integration (task 2)
# ---------------------------------------------------------------------------


def _write_year(settings: Settings, dataset: str, value_col: str, year: int, value: float) -> None:
    """Write a full-year hourly frame to `data_raw/<dataset>/` split by calendar month."""
    frame = _year_hourly(year, value_col, value)
    months = frame["ts_utc"].dt.month
    for month in sorted(months.unique()):
        write_month(
            frame.loc[months == month], dataset, date(year, int(month), 1), "testhash", settings
        )


def test_run_gates_passes_and_writes_report_on_good_synthetic_data(
    tmp_settings: Settings,
) -> None:
    for year in (2023, 2024, 2025):
        _write_year(tmp_settings, "entsoe_prices_at", "price_eur_mwh", year, value=100.0)
        _write_year(tmp_settings, "entsoe_prices_delu", "price_eur_mwh", year, value=40.0)
        _write_year(tmp_settings, "entsoe_load_at", "load_mw", year, value=7000.0)

    # Inject one negative AT price per year (ING-083) without moving the
    # annual mean (100.0) meaningfully out of any year's [70,140] band.
    at_prices_root = tmp_settings.paths.data_raw / "entsoe_prices_at"
    for year in (2023, 2024, 2025):
        jan_path = at_prices_root / str(year) / f"entsoe_prices_at_{year}-01.parquet"
        frame = pd.read_parquet(jan_path)
        frame.loc[0, "price_eur_mwh"] = -5.0
        write_month(
            frame.drop(columns=["ingested_at_utc", "source", "request_hash"]),
            "entsoe_prices_at",
            date(year, 1, 1),
            "testhash",
            tmp_settings,
        )

    run_gates(tmp_settings)  # must not raise

    report_path = (
        tmp_settings.paths.reports / "ingestion" / f"validation_{date.today():%Y-%m-%d}.md"
    )
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "ALL GATES PASSED" in content
    for gate_id in _ALL_GATE_IDS:
        assert gate_id in content


def test_run_gates_raises_and_still_writes_report_on_incomplete_data(
    tmp_settings: Settings,
) -> None:
    # Only January 2023 -- massively short of full-year coverage, and 2024/2025
    # have no data at all (ING-083 also fails).
    frame = _year_hourly(2023, "price_eur_mwh", value=100.0)
    jan_only = frame.loc[frame["ts_utc"].dt.month == 1]
    write_month(jan_only, "entsoe_prices_at", date(2023, 1, 1), "testhash", tmp_settings)

    with pytest.raises(GateFailure):
        run_gates(tmp_settings)

    report_path = (
        tmp_settings.paths.reports / "ingestion" / f"validation_{date.today():%Y-%m-%d}.md"
    )
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "GATE FAILURE" in content


def test_run_gates_creates_reports_ingestion_dir_if_missing(tmp_settings: Settings) -> None:
    assert not (tmp_settings.paths.reports / "ingestion").exists()
    with pytest.raises(GateFailure):
        run_gates(tmp_settings)  # no data at all -> every gate fails, but dir must be created
    assert (tmp_settings.paths.reports / "ingestion").exists()
