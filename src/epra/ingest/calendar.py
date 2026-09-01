"""Calendar generation — hourly spine with Austrian/Styrian holidays (M2).

Binding contract: SPEC-01 §11. Key points:

- Output ``data/raw/calendar/calendar.parquet``, one row per UTC hour from
  2019-01-01 to the end of the forward-risk window, columns (ING-110):
  ``ts_utc, date_local (Europe/Vienna), hour_local, dow_local (0=Mon),
  is_weekend, is_holiday_at, is_peak_hour, year_local, month_local``.
- Holidays via the ``holidays`` package, ``subdiv='6'`` for Styria (ING-110).
- Peak rule is ``epra.common.timeutil.is_peak_hour`` — do not re-implement
  (D-10).
- Tests (ING-111): 2024 national holiday count; Jan 1 / May 1 / Dec 25 always
  holidays; peak definition checked on a known Monday and Sunday.
- Persisted as a SINGLE parquet file (not monthly-partitioned like the
  ENTSO-E datasets) — the whole spine is cheap enough to keep as one file
  and downstream (dbt ``dim_calendar``, SPEC-02 §4) reads it whole anyway.

Implements: ING-110, ING-111; feeds dim_calendar (SPEC-02 §4).
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from datetime import date, timedelta

import pandas as pd
from holidays.countries.austria import Austria

from epra.common.config import Settings, load_settings
from epra.common.timeutil import VIENNA, is_peak_hour, next_month
from epra.ingest._io import _dataset_root
from epra.ingest.entsoe import latest_complete_month

logger = logging.getLogger(__name__)

#: Forward-risk coverage horizon (SG-15/D-08): SPEC-05's forward simulation
#: needs 12 months ahead plus a 6-month cushion so the calendar spine never
#: has to be rebuilt mid-simulation-window. Hardcoded here — calendar.py is
#: an M2 module and must not import any M6 forward-simulation config
#: (RESEARCH Pitfall 3).
_FORWARD_HORIZON_MONTHS = 18


def _default_end(settings: Settings) -> date:
    """``latest_complete_month(settings)`` advanced by
    ``_FORWARD_HORIZON_MONTHS`` months, expressed as the LAST day of the
    resulting month (D-09)."""
    month_cursor = latest_complete_month(settings)
    for _ in range(_FORWARD_HORIZON_MONTHS):
        month_cursor = next_month(month_cursor)
    return next_month(month_cursor) - timedelta(days=1)


def build_calendar(settings: Settings, end: date | None = None) -> pd.DataFrame:
    """Return the hourly calendar frame per ING-110.

    One row per UTC hour from 2019-01-01 00:00 UTC through the last UTC
    hour of ``end`` (inclusive). ``end`` defaults to
    ``latest_complete_month(settings) + _FORWARD_HORIZON_MONTHS`` months
    (D-08/D-09); pass a fixed ``end`` for deterministic tests.

    Implements: ING-110.
    """
    resolved_end = end if end is not None else _default_end(settings)

    # Use stdlib `timedelta`, not `pd.Timedelta(hours=...)` — the latter hits
    # a pandas 2.3.3 "generic unit" DeprecationWarning on the bare-kwarg
    # constructor path (upstream quirk, unrelated to this logic).
    end_of_day_naive = pd.Timestamp(resolved_end) + timedelta(hours=23)
    ts_utc = pd.date_range(start="2019-01-01", end=end_of_day_naive, freq="h", tz="UTC")

    local = ts_utc.tz_convert(VIENNA)
    date_local = local.date
    dow_local = local.dayofweek

    at_holidays = Austria(subdiv="6", years=range(2019, resolved_end.year + 1))
    holiday_dates = set(at_holidays.keys())
    # Avoid Index.isin: pandas-stubs types DatetimeIndex.date → Index as MultiIndex,
    # so isin(set[date]) fails mypy --strict (arg-type). Same predicate via membership.
    is_holiday_at = [d in holiday_dates for d in date_local]

    # Never re-derive the Mon-Fri 08-20 rule locally (D-10) — call the
    # sanctioned timeutil helper per row.
    is_peak = [
        is_peak_hour(local_ts.to_pydatetime(), is_holiday=bool(holiday))
        for local_ts, holiday in zip(local, is_holiday_at, strict=True)
    ]

    return pd.DataFrame(
        {
            "ts_utc": ts_utc,
            "date_local": date_local,
            "hour_local": local.hour,
            "dow_local": dow_local,
            "is_weekend": dow_local >= 5,
            "is_holiday_at": is_holiday_at,
            "is_peak_hour": is_peak,
            "year_local": local.year,
            "month_local": local.month,
        }
    )


def _parse_cli_date(text: str) -> date:
    """``argparse`` ``type=`` callback: reject anything not YYYY-MM-DD
    (mirrors ``epra.ingest.entsoe._parse_cli_date``, T-02-10)."""
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {text!r}; expected YYYY-MM-DD") from exc


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.calendar [--end YYYY-MM-DD]`` (ING-002).

    ``--end`` defaults to the dynamic ``latest_complete_month() +
    _FORWARD_HORIZON_MONTHS`` months (D-09); pass a fixed value for
    deterministic/manual runs. Writes a SINGLE parquet file — not
    monthly-partitioned, not via ``_io.write_month``. Returns 0 on success.
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.ingest.calendar",
        description="Build the hourly UTC calendar spine with Vienna-local "
        "attributes and Styrian holidays (ING-110).",
    )
    parser.add_argument(
        "--end",
        type=_parse_cli_date,
        default=None,
        help="Fixed end date (YYYY-MM-DD). Default: dynamic (D-09).",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    frame = build_calendar(settings, args.end)

    path = _dataset_root("calendar", settings) / "calendar.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, engine="pyarrow")
    logger.info("calendar: wrote %d rows to %s", len(frame), path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
