# ADR-014: `ts_utc` is TIMESTAMPTZ in a UTC-pinned session — this satisfies DM-010 "TIMESTAMP (UTC)"
Date: 2026-09-30  |  Status: accepted

Deciders: audit follow-up (`.planning/AUDIT-2026-09-30.md` §2, marts contract)
Related: SPEC-02 DM-010/DM-011, SPEC-03 LP-003, SPEC-01 ING-005/ING-031, `dbt/profiles.yml`, `dbt/contracts/marts_contract.yml`, `dbt/tests/session_timezone_is_utc.sql`, trap T-1/T-4 (AGENTS.md §6)

## Context

SPEC-02 DM-010 says `ts_utc` "is stored as TIMESTAMP (UTC)"; SPEC-03 LP-003
describes the consumer-load output as `ts_utc (TIMESTAMP UTC)`. The
warehouse as built stores every `ts_utc` column as DuckDB
`TIMESTAMP WITH TIME ZONE` (TIMESTAMPTZ):

- the raw parquet contract requires tz-aware UTC timestamps at the
  ingestion boundary (ING-005, ING-031, trap T-4), which DuckDB reads as
  TIMESTAMPTZ;
- `dbt/profiles.yml` pins the DuckDB session `TimeZone` to `UTC`, because
  `date_trunc('hour', ts_utc)` on a TIMESTAMPTZ truncates in the session
  zone (without the pin, DuckDB uses the host zone and hourly staging
  aggregation silently shifted to Vienna-local hour boundaries).

The audit flagged the mismatch between the contract YAML (`TIMESTAMP WITH
TIME ZONE`) and the spec wording (`TIMESTAMP (UTC)`), and noted that the
session pin was load-bearing but untested.

Two options preserve the output contract (every `ts_utc` denotes the UTC
instant of the hour start):

1. Convert every `ts_utc` to a naive `TIMESTAMP` holding UTC wall-clock
   values. That requires a conversion at every source boundary
   (`ts_utc AT TIME ZONE 'UTC'` is a timezone-conversion call that DM-011
   forbids outside `dim_calendar`; a plain `::timestamp` cast silently
   depends on the session zone anyway), changes every join key, every mart
   type and every Python reader (which currently receives tz-aware UTC
   pandas timestamps, the T-4 invariant).
2. Keep TIMESTAMPTZ, pin the session to UTC, and test the pin.

## Decision

Option 2. `ts_utc` stays `TIMESTAMP WITH TIME ZONE` everywhere (raw
sources, staging, `dim_calendar`, `fct_price_hourly`,
`fct_consumer_load_hourly`). DM-010's "TIMESTAMP (UTC)" is read as "a
timestamp type whose value is the UTC instant"; a TIMESTAMPTZ read and
written in a session whose `TimeZone` is `UTC` satisfies it exactly — its
rendered value is the UTC wall clock and it carries no local offset.

- `dbt/profiles.yml` keeps `settings: {TimeZone: UTC}` (single pin, not
  per-model).
- `dbt/tests/session_timezone_is_utc.sql` fails `dbt build` if the session
  TimeZone is ever not `UTC`.
- The marts that load Python module outputs cast `ts_utc` to TIMESTAMPTZ
  (`fct_consumer_load_hourly`): a module that writes naive-UTC timestamps
  (LP-003's literal wording) is interpreted as UTC by the pinned session, a
  tz-aware UTC one passes through unchanged — either way the mart type is
  identical.
- `dbt/contracts/marts_contract.yml` records `TIMESTAMP WITH TIME ZONE` for
  every `ts_utc` column and cites this ADR.

## Consequences

- No data or join-key change; the M3 marts keep their current values.
- Python readers keep receiving tz-aware UTC timestamps (T-4 invariant).
- Anyone opening `epra.duckdb` outside dbt (DuckDB CLI, Python) must also
  run in UTC or convert explicitly before taking `date_trunc`/`::date` of a
  `ts_utc`; local calendar attributes must still come only from
  `dim_calendar` (DM-011). `epra.common.db.connect` should pin the same
  session TimeZone for Python readers (follow-up outside `dbt/`).

## Spec deviations

Wording-level only: SPEC-02 DM-010 / SPEC-03 LP-003 "TIMESTAMP (UTC)" is
implemented as TIMESTAMPTZ in a UTC-pinned session. The output contract —
`ts_utc` is the UTC instant and the universal join key — is unchanged.
