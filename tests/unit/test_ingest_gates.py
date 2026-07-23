"""Synthetic pass/fail tests for ING-080..085 validation gates (02-06 task 1).

Each gate function gets one passing and one failing synthetic case per
03_MODULES.md ("mandatory"). Fixtures are hand-built (never real market data)
so a "failing" case is *known* bad -- confirming the gate would actually stop
a bad pipeline (A-2).
"""

from __future__ import annotations

from calendar import isleap
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from epra.common.config import Settings, load_settings
from epra.ingest._io import write_month
from epra.ingest.calendar import build_calendar
from epra.ingest.exceptions import GateFailure
from epra.ingest.oespi import load_oespi
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
    gate_ing_103,
    gate_ing_111,
    run_gates,
)

_ALL_GATE_IDS = ("ING-080", "ING-081", "ING-082", "ING-083", "ING-084", "ING-085")
#: Full M1+M2 gate roster `run_gates` registers (03-06) -- used by the
#: aggregate `run_gates` tests to assert every gate appears exactly once.
_ALL_M1_M2_GATE_IDS = (*_ALL_GATE_IDS, "ING-094", "ING-103", "ING-111")

_OESPI_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "oespi" / "synthetic_oespi_monthly.csv"
)


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
# ING-103 -- ÖSPI series gates (03-05 task 2): continuity, positivity, crisis
# visibility (2022 peak >= 3x 2019 mean), month-over-month stability
# ---------------------------------------------------------------------------


def _clean_oespi() -> pd.DataFrame:
    """The committed synthetic ÖSPI series (2019-2023) -- a clean case gate_ing_103 PASSES."""
    return load_oespi(load_settings(), csv_path=_OESPI_FIXTURE)


def test_gate_ing_103_passes_clean_series() -> None:
    result = gate_ing_103(_clean_oespi())
    assert result.gate_id == "ING-103"
    assert result.passed is True


def test_gate_ing_103_fails_on_empty_input() -> None:
    empty = pd.DataFrame(columns=["oespi_base", "oespi_peak", "source_url", "retrieved_at"])
    result = gate_ing_103(empty)
    assert result.passed is False


def test_gate_ing_103_fails_on_month_gap() -> None:
    frame = _clean_oespi()
    frame = frame.drop(frame.index[30])  # drop an internal month (2021-07) -- creates a gap

    result = gate_ing_103(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "continuity", "ok"].all()


def test_gate_ing_103_fails_on_negative_value() -> None:
    frame = _clean_oespi()
    frame.loc[frame.index[0], "oespi_base"] = -5.0

    result = gate_ing_103(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "positivity", "ok"].all()


def test_gate_ing_103_fails_when_2022_peak_below_3x_2019_mean() -> None:
    frame = _clean_oespi()
    # Clamp every 2022 value to the Dec-2021 level (190) -- ratio to the 2019
    # mean (100) drops to 1.9x (< 3x), while the Dec21->Jan22 (0%) and
    # Dec22->Jan23 (~58%) transitions both stay within the +/-60% MoM band.
    frame.loc[frame.index.year == 2022, "oespi_base"] = 190.0

    result = gate_ing_103(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "crisis_visibility", "ok"].all()


def test_gate_ing_103_fails_on_mom_jump_exceeding_60_percent() -> None:
    frame = _clean_oespi()
    prev_value = frame.loc[frame.index[9], "oespi_base"]
    frame.loc[frame.index[10], "oespi_base"] = prev_value * 3  # +200% month-over-month

    result = gate_ing_103(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "mom_change", "ok"].all()


def test_gate_ing_103_input_mutation_is_avoided() -> None:
    frame = _clean_oespi()
    before = frame.copy()
    gate_ing_103(frame)
    pd.testing.assert_frame_equal(frame, before)


# ---------------------------------------------------------------------------
# ING-111 -- calendar spine gate (03-06 task 1): thin wrapper over
# `epra.ingest.calendar.build_calendar`, reusing the 03-02 assertions.
# ---------------------------------------------------------------------------

_CALENDAR_FIXED_END = date(2027, 12, 31)

_EMPTY_CALENDAR_COLUMNS = [
    "ts_utc",
    "date_local",
    "hour_local",
    "dow_local",
    "is_weekend",
    "is_holiday_at",
    "is_peak_hour",
    "year_local",
    "month_local",
]


def _clean_calendar() -> pd.DataFrame:
    """A valid ING-110 calendar spine -- `gate_ing_111` PASSES outright."""
    return build_calendar(load_settings(), end=_CALENDAR_FIXED_END)


def test_gate_ing_111_passes_on_valid_calendar_spine() -> None:
    result = gate_ing_111(_clean_calendar())
    assert result.gate_id == "ING-111"
    assert result.passed is True


def test_gate_ing_111_fails_on_empty_input() -> None:
    empty = pd.DataFrame(columns=_EMPTY_CALENDAR_COLUMNS)
    result = gate_ing_111(empty)
    assert result.passed is False


def test_gate_ing_111_fails_when_fixed_holiday_missing() -> None:
    frame = _clean_calendar().copy()
    mask = frame["date_local"] == date(2024, 1, 1)
    frame.loc[mask, "is_holiday_at"] = False

    result = gate_ing_111(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "fixed_holidays", "ok"].all()


def test_gate_ing_111_fails_when_peak_hour_wrong() -> None:
    frame = _clean_calendar().copy()
    # Flip the known non-holiday Monday 10:00 local hour to off-peak.
    mask = (frame["date_local"] == date(2024, 1, 8)) & (frame["hour_local"] == 10)
    frame.loc[mask, "is_peak_hour"] = False

    result = gate_ing_111(frame)
    assert result.passed is False
    assert result.evidence is not None
    assert not result.evidence.loc[result.evidence["check"] == "peak_hour_mon_sun", "ok"].all()


def test_gate_ing_111_input_mutation_is_avoided() -> None:
    frame = _clean_calendar()
    before = frame.copy()
    gate_ing_111(frame)
    pd.testing.assert_frame_equal(frame, before)


# ---------------------------------------------------------------------------
# run_gates -- loader + report writer integration (task 2, extended 03-06 for
# ING-094/103/111 wiring)
# ---------------------------------------------------------------------------


def _write_year(settings: Settings, dataset: str, value_col: str, year: int, value: float) -> None:
    """Write a full-year hourly frame to `data_raw/<dataset>/` split by calendar month."""
    frame = _year_hourly(year, value_col, value)
    months = frame["ts_utc"].dt.month
    for month in sorted(months.unique()):
        write_month(
            frame.loc[months == month], dataset, date(year, int(month), 1), "testhash", settings
        )


def _write_geosphere_frame(settings: Settings, frame: pd.DataFrame) -> None:
    """Write a full GeoSphere daily frame to `data_raw/geosphere_graz_daily/`, split by month."""
    dates = pd.to_datetime(frame["date"])
    for year, month in sorted({(int(d.year), int(d.month)) for d in dates}):
        month_mask = (dates.dt.year == year) & (dates.dt.month == month)
        write_month(
            frame.loc[month_mask],
            "geosphere_graz_daily",
            date(year, month, 1),
            "testhash",
            settings,
            key_column="date",
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

    # M2: plausible GeoSphere coverage (ING-094). ÖSPI (ING-103) and the
    # calendar (ING-111) need no seeding here -- `tmp_settings.paths.data_manual`
    # has no `oespi_monthly.csv` (informational skip, D-06), and
    # `build_calendar` derives its spine from the ENTSO-E data written above.
    _write_geosphere_frame(tmp_settings, _geosphere_year(2023, {7: 20.0, 1: 0.0}))

    run_gates(tmp_settings)  # must not raise

    report_path = (
        tmp_settings.paths.reports / "ingestion" / f"validation_{date.today():%Y-%m-%d}.md"
    )
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "ALL GATES PASSED" in content
    for gate_id in _ALL_M1_M2_GATE_IDS:
        assert content.count(gate_id) == 1
    assert "not yet transcribed" in content  # ÖSPI D-06 informational skip is visible


def test_run_gates_raises_on_m2_gate_failure_and_lists_all_ids_once(
    tmp_settings: Settings,
) -> None:
    """A failing M2 gate (GeoSphere, ING-094) still raises `GateFailure` and the
    report lists every M1+M2 gate id exactly once (T-02-13) -- confirms the
    03-06 wiring surfaces a real M2 failure, not just M1 failures."""
    for year in (2023, 2024, 2025):
        _write_year(tmp_settings, "entsoe_prices_at", "price_eur_mwh", year, value=100.0)
        _write_year(tmp_settings, "entsoe_prices_delu", "price_eur_mwh", year, value=40.0)
        _write_year(tmp_settings, "entsoe_load_at", "load_mw", year, value=7000.0)

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

    # Seed a genuine M2 (GeoSphere) failure: one temperature above the 42 degC ceiling.
    bad_geosphere = _geosphere_year(2023, {7: 20.0, 1: 0.0})
    bad_geosphere.loc[0, "tl_mittel_c"] = 50.0
    _write_geosphere_frame(tmp_settings, bad_geosphere)

    with pytest.raises(GateFailure) as excinfo:
        run_gates(tmp_settings)
    assert "ING-094" in str(excinfo.value)

    report_path = (
        tmp_settings.paths.reports / "ingestion" / f"validation_{date.today():%Y-%m-%d}.md"
    )
    content = report_path.read_text(encoding="utf-8")
    assert "GATE FAILURE" in content
    # Count section headers, not bare substring occurrences -- a FAILING
    # gate's own summary text may legitimately re-mention its gate id (e.g.
    # gate_ing_094's "N ING-094 check(s) failed"), so the "registered exactly
    # once" invariant (T-02-13) is about the one `### {gate_id} --` heading
    # `report.add()` produces per gate, not literal substring frequency.
    for gate_id in _ALL_M1_M2_GATE_IDS:
        assert content.count(f"### {gate_id} ") == 1


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
