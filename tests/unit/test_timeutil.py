"""Timezone handling tests — trap T-1 is the most dangerous bug class."""

from datetime import UTC, date, datetime

import pytest

from epra.common.timeutil import (
    VIENNA,
    is_peak_hour,
    iter_month_starts,
    local_hours_in_day,
    month_start,
    next_month,
    to_local,
    to_utc,
)


def test_naive_datetimes_are_rejected() -> None:
    naive = datetime(2024, 1, 8, 12, 0)
    with pytest.raises(ValueError, match="naive"):
        to_utc(naive)
    with pytest.raises(ValueError, match="naive"):
        to_local(naive)
    with pytest.raises(ValueError, match="naive"):
        is_peak_hour(naive)


def test_utc_local_round_trip() -> None:
    local = datetime(2024, 7, 1, 14, 0, tzinfo=VIENNA)  # CEST = UTC+2
    utc = to_utc(local)
    assert utc.hour == 12
    assert utc.tzinfo == UTC
    assert to_local(utc) == local


def test_peak_hour_definition() -> None:
    # Charter glossary / ING-110: Mon-Fri 08:00-20:00 Europe/Vienna, non-holiday.
    monday = datetime(2024, 1, 8, 14, 0, tzinfo=VIENNA)
    assert is_peak_hour(monday)
    assert not is_peak_hour(monday.replace(hour=7))
    assert is_peak_hour(monday.replace(hour=8))  # boundary: inclusive start
    assert is_peak_hour(monday.replace(hour=19))
    assert not is_peak_hour(monday.replace(hour=20))  # boundary: exclusive end
    sunday = datetime(2024, 1, 7, 14, 0, tzinfo=VIENNA)
    assert not is_peak_hour(sunday)
    # A weekday holiday is off-peak (e.g. Wed 2024-05-01, Staatsfeiertag).
    holiday = datetime(2024, 5, 1, 14, 0, tzinfo=VIENNA)
    assert not is_peak_hour(holiday, is_holiday=True)


def test_dst_day_hour_counts() -> None:
    # ING-080 DST correctness: last Sunday of March = 23 h, October = 25 h.
    assert local_hours_in_day(date(2024, 3, 31)) == 23
    assert local_hours_in_day(date(2024, 10, 27)) == 25
    assert local_hours_in_day(date(2024, 6, 15)) == 24


def test_month_helpers() -> None:
    assert month_start(date(2022, 8, 17)) == date(2022, 8, 1)
    assert next_month(date(2022, 12, 5)) == date(2023, 1, 1)
    assert next_month(date(2022, 8, 17)) == date(2022, 9, 1)
    months = list(iter_month_starts(date(2019, 1, 15), date(2019, 4, 2)))
    assert months == [date(2019, 1, 1), date(2019, 2, 1), date(2019, 3, 1), date(2019, 4, 1)]
