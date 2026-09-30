# ADR-017: The ING-110 calendar spine uses Europe/Vienna local-day bounds
Date: 2026-09-30  |  Status: accepted

## Context
ING-110 describes `calendar.parquet` as "one row per hour UTC 2019-01-01 → end
of forward-risk window". `calendar.py` read that as UTC-day bounds, so the
spine started at 2019-01-01 00:00 UTC and ended at 23:00 UTC on the end day.
The first local hour of the analysis window (2019-01-01 00:00 Europe/Vienna =
2018-12-31 23:00 UTC) was therefore missing. `fct_price_hourly` uses
`dim_calendar` as its row spine, so the warehouse showed local 2019 with 8759
hours while the raw validation counted 8760, and it emitted a 1-hour local
year at the far end (audit 2026-09-30, §5). DM-012 says a calendar year always
means the local year, and 2019 is the SPEC-05 reference year, so its first
hour is not optional.

## Decision
`build_calendar` emits one row per hour, keyed by `ts_utc` (still UTC, as
ING-005 requires), from 00:00 Europe/Vienna on `settings.window.start_date`
through the last local hour of the end day. The bounds are computed as UTC
instants, so the 23-hour and 25-hour DST days come out right by construction.
The column set and types are unchanged.

## Consequences
- Every local year in the spine is complete: 2019 has 8760 hours and 2024 has
  8784. There is no trailing 1-hour year.
- The first `ts_utc` is `2018-12-31T23:00Z`. That is the same UTC-boundary hour
  the ENTSO-E backfill already ingests and ADR-006 already buckets into local
  2019.
- `data/raw/calendar/calendar.parquet` must be regenerated (`make calendar`)
  before the next `make warehouse` on real data.
- The fixture bootstrap already used local-day bounds (`_vienna_hour_index`),
  so CI output does not change.

## Spec deviations
ING-110 (it literally reads "per hour UTC 2019-01-01"). The output contract is
preserved: same file, same columns, hourly UTC key. Only the first and last
hour of the window move to local-day boundaries, as DM-012 requires.
