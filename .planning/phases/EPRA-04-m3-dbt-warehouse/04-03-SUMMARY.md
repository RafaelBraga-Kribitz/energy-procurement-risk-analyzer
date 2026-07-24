---
phase: EPRA-04-m3-dbt-warehouse
plan: 03
subsystem: database
tags: [dbt, dbt-duckdb, duckdb, sql]

# Dependency graph
requires:
  - phase: EPRA-04-m3-dbt-warehouse plan 02
    provides: dbt/models/staging/stg_weather_graz_daily.sql (date_local, tavg_c join input); dbt/profiles.yml settings.TimeZone=UTC (session timezone pin)
provides:
  - dbt/models/marts/dim_calendar.sql — hour-grain calendar dimension (SPEC-02 §4): ts_utc, date_local, year_local, month_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour, season, hdd_18, cdd_22
  - dbt/models/marts/dims.yml — DM-060 unique/not_null tests on dim_calendar.ts_utc and dim_strategy.strategy_id
affects: [EPRA-04-m3-dbt-warehouse plans 04-08 (fct_* marts join dim_calendar on ts_utc; fct_procurement_cost_monthly FKs to dim_strategy)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dim_calendar loads local calendar attributes verbatim from source('raw_calendar','calendar') — zero timezone-conversion calls at the mart layer (DM-011); every fct_* mart attaches local attributes only via a join to dim_calendar, never by recomputing them"
    - "Degree-days (hdd_18/cdd_22) are computed once per local day from daily weather and left-joined on date_local so the value repeats identically across all 24 local hours — never recomputed per-hour from a (nonexistent) hourly temperature"
    - "dims.yml is a dedicated YAML file for dimension-level generic tests, kept separate from the fct_* YAMLs added in 04-04/04-05 to avoid cross-plan file conflicts"

key-files:
  created:
    - dbt/models/marts/dim_calendar.sql
    - dbt/models/marts/dims.yml
  modified: []

key-decisions:
  - "No deviations from plan — dim_calendar builds exactly per SPEC-02 §4 contract with zero timezone-conversion calls, and dims.yml pins DM-060 tests on both dimension keys as specified."

patterns-established:
  - "Every mart-layer model's header comment states its Implements: DM-xxx / SPEC-02 §n citation and explicitly documents WHY no timezone-conversion call is used, continuing the project-wide spec-ID citation convention."

requirements-completed: [REQ-DWH-01, DM-011, DM-012, DM-060]

coverage:
  - id: D1
    description: "dim_calendar builds on real local data with the full SPEC-02 §4 column set (calendar attributes + season + hdd_18/cdd_22), zero timezone-conversion calls, and correct DST edge-hour counts"
    requirement: "DM-011"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select dim_calendar (exit 0); grep -i 'AT TIME ZONE|timezone(|::timestamptz' dim_calendar.sql (no matches); manual query: date_local=2024-03-31 has 23 rows, date_local=2024-10-27 has 25 rows, zero duplicate ts_utc across 78,888 total rows, zero NULL hdd_18/cdd_22 (weather covers the full window)"
        status: pass
    human_judgment: false
  - id: D2
    description: "dims.yml pins DM-060 unique/not_null on dim_calendar.ts_utc and dim_strategy.strategy_id, making dim_strategy a trustworthy DM-063 FK target"
    requirement: "DM-060"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select dim_calendar dim_strategy (exit 0, 6/6 PASS: 1 model + 1 seed + 4 generic tests — unique/not_null green on both keys)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-24
status: complete
---

# Phase EPRA-04 Plan 03: dim_calendar + dims.yml (DM-060) Summary

**Hour-grain `dim_calendar` — the single source of local calendar truth every fct_* mart will join on — built from the ING-110 calendar parquet with season and weather-derived degree-days, zero timezone-conversion calls (DM-011), plus DM-060 unique/not_null pinned on both dimension keys**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-24T08:48:52Z
- **Tasks:** 2/2
- **Files modified:** 2 (both created)

## Accomplishments
- `dim_calendar` builds green on real local data (78,888 rows, 2019-01-01 through the forward-risk horizon), loading `ts_utc, date_local, year_local, month_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour` verbatim from `source('raw_calendar','calendar')` with **zero** timezone-conversion calls (confirmed by grep for `AT TIME ZONE`/`timezone(`/`::timestamptz` — no matches)
- `season` computed as `'winter'` for `month_local in (11,12,1,2,3)` else `'summer'` (Austrian energy convention); `hdd_18 = greatest(0, 18 - tavg_c)` and `cdd_22 = greatest(0, tavg_c - 22)` left-joined from `stg_weather_graz_daily` on `date_local`, repeating the daily value across all 24 local hours
- DST adjacency verified directly on real data: `date_local = 2024-03-31` has exactly 23 rows (spring-forward), `date_local = 2024-10-27` has exactly 25 rows (fall-back), and zero duplicate `ts_utc` values across the full table — confirms the ING-110 calendar source and the mart-layer passthrough correctly encode both DST edge hours (DM-012)
- Weather coverage is complete across the built window: zero NULL `hdd_18`/`cdd_22` rows, so the left join's NULL-preserving behavior (documented for days lacking weather) was exercised but not triggered on this real dataset
- `dims.yml` pins `unique` + `not_null` on `dim_calendar.ts_utc` and `dim_strategy.strategy_id` — full `dbt build --select dim_calendar dim_strategy` is 6/6 PASS (1 model, 1 seed, 4 generic tests)
- Full-project `dbt build` re-run after both tasks: 31 PASS / 1 WARN (the pre-existing, non-blocking DM-020 `predup_count_prices` warn from 04-02, unrelated to this plan) / 0 ERROR — confirms no regression to the 8 staging views or their tests

## Task Commits

Each task was committed atomically:

1. **Task 1: dim_calendar — calendar load + weather join, no TZ calls (DM-011)** - `a1b349d` (feat)
2. **Task 2: dims.yml — unique/not_null on dim_calendar + dim_strategy (DM-060)** - `b728556` (feat)

## Files Created/Modified
- `dbt/models/marts/dim_calendar.sql` - hour-grain calendar dimension: ING-110 calendar columns + season + hdd_18/cdd_22, zero TZ calls
- `dbt/models/marts/dims.yml` - DM-060 unique/not_null generic tests on `dim_calendar.ts_utc` and `dim_strategy.strategy_id`

## Decisions Made
- No deviations — plan executed exactly as written. Both tasks' acceptance criteria were met on the first build with real local data; no auto-fixes or architectural questions arose.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - all inputs (calendar parquet, `stg_weather_graz_daily`, `dim_strategy` seed) were already present from 04-01/04-02.

## Next Phase Readiness

`dim_calendar` is ready for every `fct_*` mart in 04-04 to join on `ts_utc` for local attributes (`year_local`, `month_local`, `hour_local`, `dow_local`, `is_weekend`, `is_holiday_at`, `is_peak_hour`, `season`, `hdd_18`, `cdd_22`). `dim_strategy` is now a validated DM-060/DM-063 FK target for `fct_procurement_cost_monthly` in 04-05. No blockers for 04-04.

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-07-24*

## Self-Check: PASSED

Both created files (`dbt/models/marts/dim_calendar.sql`, `dbt/models/marts/dims.yml`) found on disk; both commit hashes (`a1b349d`, `b728556`) found in git log.
