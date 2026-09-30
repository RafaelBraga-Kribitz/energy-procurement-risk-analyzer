"""Time handling — the single most dangerous bug class in this project (T-1).

Doctrine (Charter glossary, DM-010..012, ING-005): everything STORED is UTC
(``ts_utc``); everything ANALYTIC is Europe/Vienna local. These helpers are the
only sanctioned conversion points outside dbt's ``dim_calendar``.

Implements: supports ING-005, ING-031, ING-110 (peak-hour rule), ING-080 (DST
hour counts), ING-030 (month chunking).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

VIENNA = ZoneInfo("Europe/Vienna")

#: Peak-hour definition (Charter glossary): Mon-Fri 08:00-20:00 Europe/Vienna,
#: non-holiday (ING-110). Constants named so no module retypes the numbers.
PEAK_START_HOUR = 8
PEAK_END_HOUR = 20  # exclusive


def to_utc(ts: datetime) -> datetime:
    """Convert a tz-aware datetime to UTC. Naive input is a bug — raise (T-4).

    Implements: ING-005, ING-031 (UTC at the ingestion boundary).
    """
    if ts.tzinfo is None:
        raise ValueError("naive datetime passed to to_utc(); timestamps must be tz-aware")
    return ts.astimezone(UTC)


def to_local(ts: datetime) -> datetime:
    """Convert a tz-aware datetime to Europe/Vienna local time.

    Implements: DM-012 (local-year semantics), ING-031 (Vienna request bounds).
    """
    if ts.tzinfo is None:
        raise ValueError("naive datetime passed to to_local(); timestamps must be tz-aware")
    return ts.astimezone(VIENNA)


def is_peak_hour(ts_local: datetime, *, is_holiday: bool = False) -> bool:
    """True if ``ts_local`` falls in a peak hour: Mon-Fri, 08-20 local, not a holiday.

    ``ts_local`` must be tz-aware in Europe/Vienna (convert with :func:`to_local`).
    Implements: ING-110 ``is_peak_hour``.
    """
    if ts_local.tzinfo is None:
        raise ValueError("naive datetime passed to is_peak_hour(); convert via to_local()")
    if is_holiday:
        return False
    return ts_local.weekday() < 5 and PEAK_START_HOUR <= ts_local.hour < PEAK_END_HOUR


def local_hours_in_day(d: date) -> int:
    """Number of local clock hours in local day ``d`` (23/24/25 across DST).

    Implements: ING-080 (DST-aware expected hour counts).
    """
    start = datetime(d.year, d.month, d.day, tzinfo=VIENNA)
    next_day = d + timedelta(days=1)
    end = datetime(next_day.year, next_day.month, next_day.day, tzinfo=VIENNA)
    # Subtract in UTC: same-tzinfo subtraction ignores UTC offsets (stdlib rule),
    # which would silently yield 24 h on DST days.
    return round((end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 3600)


def today_local() -> date:
    """Today's calendar date in Europe/Vienna — never the machine-local date (T-1).

    Implements: ING-041 (lookback anchored on the Vienna day), ING-042 (month
    boundaries evaluated in local time).
    """
    return datetime.now(VIENNA).date()


def month_start(d: date) -> date:
    """First day of ``d``'s month.

    Implements: ING-003 (monthly file grain), ING-042 (month arithmetic).
    """
    return d.replace(day=1)


def next_month(d: date) -> date:
    """First day of the month after ``d``'s month.

    Implements: ING-003, ING-030 (exclusive month bounds for chunking).
    """
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def iter_month_starts(start: date, end: date) -> Iterator[date]:
    """Yield the first day of every month from ``start``'s month up to and
    including ``end``'s month.

    Implements: ING-003 (per-month parquet files), ING-030 (request chunking).
    """
    current = month_start(start)
    last = month_start(end)
    while current <= last:
        yield current
        current = next_month(current)
