"""Calendar hourly spine tests — DST correctness, Styrian holidays, and
timeutil-sourced peak flags (ING-110/111).

`build_calendar` is exercised with a fixed `end` throughout so these tests
never touch `latest_complete_month`/network (D-09). The full spine is built
once per module (module-scoped fixture) and reused across assertions to
avoid repeatedly constructing a ~79k-row frame.
"""

from __future__ import annotations

from datetime import date

import holidays
import pandas as pd
import pytest

from epra.common.config import load_settings
from epra.common.timeutil import local_hours_in_day
from epra.ingest import calendar as cal

_FIXED_END = date(2027, 12, 31)

_EXPECTED_COLUMNS = [
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


@pytest.fixture(scope="module")
def calendar_frame() -> pd.DataFrame:
    """Build the ING-110 spine once with a fixed `end` (D-09)."""
    settings = load_settings()
    return cal.build_calendar(settings, end=_FIXED_END)


def test_build_calendar_spine_covers_2019_through_end(calendar_frame: pd.DataFrame) -> None:
    assert list(calendar_frame.columns) == _EXPECTED_COLUMNS
    assert str(calendar_frame["ts_utc"].dt.tz) == "UTC"
    assert calendar_frame["ts_utc"].iloc[0] == pd.Timestamp("2019-01-01T00:00:00Z")
    assert calendar_frame["ts_utc"].iloc[-1] == pd.Timestamp("2027-12-31T23:00:00Z")
    # Hourly, contiguous, no gaps or duplicates.
    diffs = calendar_frame["ts_utc"].diff().iloc[1:]
    assert (diffs == pd.Timedelta(hours=1)).all()


def test_build_calendar_dst_rows(calendar_frame: pd.DataFrame) -> None:
    # 2024 last Sunday of March = spring-forward (23h local day); last Sunday
    # of October = fall-back (25h local day) — counted via timeutil, never
    # hand-derived (ING-080 semantics).
    spring = date(2024, 3, 31)
    fall = date(2024, 10, 27)
    counts = calendar_frame.groupby("date_local").size()
    assert counts.loc[spring] == local_hours_in_day(spring) == 23
    assert counts.loc[fall] == local_hours_in_day(fall) == 25


def test_build_calendar_ing_111_holiday_count_and_fixed_holidays(
    calendar_frame: pd.DataFrame,
) -> None:
    frame_2024 = calendar_frame[calendar_frame["year_local"] == 2024]
    holiday_dates = set(frame_2024.loc[frame_2024["is_holiday_at"], "date_local"])
    expected = holidays.Austria(subdiv="6", years=2024)
    assert len(holiday_dates) == len(expected)
    assert date(2024, 1, 1) in holiday_dates
    assert date(2024, 5, 1) in holiday_dates
    assert date(2024, 12, 25) in holiday_dates


def test_build_calendar_ing_111_peak_hours(calendar_frame: pd.DataFrame) -> None:
    def _row(d: date, hour: int) -> pd.Series:
        match = calendar_frame[
            (calendar_frame["date_local"] == d) & (calendar_frame["hour_local"] == hour)
        ]
        assert len(match) == 1
        return match.iloc[0]

    # Monday 2024-01-08 10:00 local, non-holiday -> peak.
    monday_row = _row(date(2024, 1, 8), 10)
    assert bool(monday_row["is_holiday_at"]) is False
    assert bool(monday_row["is_peak_hour"]) is True

    # Sunday 2024-01-07 10:00 local -> not peak (weekend).
    sunday_row = _row(date(2024, 1, 7), 10)
    assert bool(sunday_row["is_peak_hour"]) is False

    # Holiday weekday 2024-05-01 (Wed, Staatsfeiertag) 10:00 local -> not
    # peak even though it's a weekday (holiday-aware via timeutil, D-10).
    holiday_row = _row(date(2024, 5, 1), 10)
    assert bool(holiday_row["is_holiday_at"]) is True
    assert bool(holiday_row["is_peak_hour"]) is False


def test_styria_subdivision_code_is_6() -> None:
    # SG-10: assert the working Styria subdivision code exists on the
    # `holidays` package's Austria implementation.
    assert "6" in holidays.Austria.subdivisions
