---
phase: EPRA-04-m3-dbt-warehouse
plan: 02
subsystem: database
tags: [dbt, dbt-duckdb, duckdb, sql]

# Dependency graph
requires:
  - phase: EPRA-04-m3-dbt-warehouse plan 01
    provides: dbt/models/sources.yml (raw/raw_manual source definitions), generate_schema_name macro, month_spine/accepted_range macros
provides:
  - dbt/models/staging/stg_prices_at_native.sql, stg_prices_delu_native.sql — DM-020 single-point deduped native MTU price views
  - dbt/models/staging/stg_prices_at_hourly.sql, stg_prices_delu_hourly.sql — hour-grain mean price with n_subhours (Pitfall 4)
  - dbt/models/staging/stg_load_at_hourly.sql — hour-grain load MW mean (ING-051)
  - dbt/models/staging/stg_gen_at_hourly.sql — hour x psr_type generation, kind='aggregated' only (SG-17)
  - dbt/models/staging/stg_weather_graz_daily.sql — daily date_local/tavg_c rename
  - dbt/models/staging/stg_oespi_monthly.sql — monthly month_local/oespi_base/oespi_peak from CSV
  - dbt/models/staging/staging.yml — DM-060 unique/not_null generic tests + §3-citing descriptions
  - dbt/tests/predup_count_prices.sql — DM-020 pre-dedup duplicate-count warn test
  - dbt/macros/test_unique_combination_of_columns.sql — hand-rolled composite-key generic test (zero dbt_utils dependency)
  - dbt/profiles.yml settings.TimeZone=UTC — DuckDB session timezone pin (correctness fix, see Deviations)
affects: [EPRA-04-m3-dbt-warehouse plans 03-08 (dim_calendar/dim_strategy, marts, dbt test suite, CI fixture bootstrap)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Staging hourly-mean models always select count(*) as n_subhours alongside avg() — never a bare mean (Pitfall 4, DM-064 downstream guard)"
    - "dbt-duckdb profiles.yml settings: {TimeZone: UTC} pins every session's DuckDB TimeZone so date_trunc('hour'/'month', ts_utc) on TIMESTAMPTZ columns truncates in UTC, not the host OS's local zone"
    - "Composite-grain-key uniqueness tests hand-rolled as a generic test macro (group by + count(*) > 1) instead of adding dbt_utils, consistent with 04-01's zero-package-dependency posture (ADR-001)"

key-files:
  created:
    - dbt/models/staging/stg_prices_at_native.sql
    - dbt/models/staging/stg_prices_delu_native.sql
    - dbt/models/staging/stg_prices_at_hourly.sql
    - dbt/models/staging/stg_prices_delu_hourly.sql
    - dbt/models/staging/stg_load_at_hourly.sql
    - dbt/models/staging/stg_gen_at_hourly.sql
    - dbt/models/staging/stg_weather_graz_daily.sql
    - dbt/models/staging/stg_oespi_monthly.sql
    - dbt/models/staging/staging.yml
    - dbt/tests/predup_count_prices.sql
    - dbt/macros/test_unique_combination_of_columns.sql
  modified:
    - dbt/profiles.yml

key-decisions:
  - "Rule 1 bug fix: dbt/profiles.yml pins settings.TimeZone=UTC — DuckDB's default session TimeZone is the host OS local zone (confirmed live: 'Europe/Vienna' on this machine), so date_trunc('hour', ts_utc) on a TIMESTAMPTZ column was silently truncating to Vienna-local hour boundaries instead of UTC ones; DST-transition hours showed n_subhours=8 instead of 4 before the pin. This is a warehouse-level session config fix, not a per-model AT TIME ZONE call (which DM-011 reserves for local-attribute derivation)."
  - "Rule 3 blocking-adjacent: hand-rolled dbt/macros/test_unique_combination_of_columns.sql because dbt-core ships no native combination-of-columns generic test (only dbt_utils has one) and this project deliberately carries zero dbt package dependencies (ADR-001) — used for stg_gen_at_hourly's composite [ts_utc, psr_type] grain key."
  - "stg_oespi_monthly parses the CSV's 'YYYY-MM' month string via strptime(..., '%Y-%m')::date to the first-of-month DATE grain key (no separate calendar dependency needed at this layer)."
  - "predup_count_prices.sql sums duplicate rows (n_rows - 1) per UTC month x zone across BOTH entsoe_prices_at and entsoe_prices_delu raw sources (union), reading the RAW source directly rather than the deduped native view, per DM-020 defense-in-depth."

patterns-established:
  - "Every staging model's header comment states its Implements: DM-xxx/SG-xx citation, continuing the 04-01 convention."
  - "Hourly-mean staging models group by date_trunc('hour', ts_utc) and always carry n_subhours = count(*) in the same select."

requirements-completed: [REQ-DWH-01, DM-005, DM-020, SG-16, SG-17]

coverage:
  - id: D1
    description: "Four price staging views (stg_prices_at_native/delu_native/at_hourly/delu_hourly) build on real local raw data with DM-020 single-point dedup and n_subhours-carrying hourly means"
    requirement: "DM-005"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select stg_prices_at_native stg_prices_delu_native stg_prices_at_hourly stg_prices_delu_hourly (exit 0); manual query confirms n_subhours uniformly 4 post-TimeZone-pin (was 8 at DST-transition hours before the fix)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Load/generation/weather/OESPI staging views build with exact §3 columns, the SG-17 aggregated-only generation filter, and no timezone-conversion calls"
    requirement: "SG-17"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select stg_load_at_hourly stg_gen_at_hourly stg_weather_graz_daily stg_oespi_monthly (exit 0); grep confirms kind='aggregated' filter and column names; grep -i 'AT TIME ZONE' returns no matches"
        status: pass
    human_judgment: false
  - id: D3
    description: "staging.yml pins unique/not_null on every grain key (DM-060) and the DM-020 duplicate-count singular test warns without failing the build"
    requirement: "DM-020"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select staging (exit 0, 25/25 PASS); uv run dbt build --select staging predup_count_prices (exit 0, WARN=1 with 124 real duplicate rows found, build still green)"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-24
status: complete
---

# Phase EPRA-04 Plan 02: Staging Models (8 views) Summary

**Eight SPEC-02 §3 staging views over real ENTSO-E/GeoSphere/OESPI raw data — DM-020 single-point dedup, n_subhours-carrying hourly means, and a live DuckDB session-timezone bug (Vienna-local hour truncation) caught and fixed before it could silently corrupt every downstream hourly aggregation**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-07-24T08:42:37Z
- **Tasks:** 3/3
- **Files modified:** 12 (11 created + `dbt/profiles.yml`)

## Accomplishments
- Four price staging views (`stg_prices_at_native`/`stg_prices_delu_native`/`stg_prices_at_hourly`/`stg_prices_delu_hourly`) build green on 178,936 real native price rows per zone, deduped via the single sanctioned DM-020 `qualify row_number()` rule, hourly means uniformly carrying `n_subhours=4` (PT15M) after the timezone fix
- Four remaining staging views (`stg_load_at_hourly`, `stg_gen_at_hourly`, `stg_weather_graz_daily`, `stg_oespi_monthly`) build green on real data with exact §3 columns; `stg_gen_at_hourly` correctly filters `kind='aggregated'` (SG-17), dropping raw `consumption` rows
- `staging.yml` pins `unique`/`not_null` on all 8 grain keys (DM-060); full `dbt build --select staging` is 25/25 PASS
- `predup_count_prices.sql` reads the RAW price sources (not the deduped native view) and WARNs — never fails — on 124 real pre-dedup duplicate rows found across the ingest window, proving the DM-020 defense-in-depth test is live and correctly non-blocking
- **Live correctness bug caught and fixed:** DuckDB's default session `TimeZone` is the host OS's local zone (`Europe/Vienna` on this machine), which made `date_trunc('hour', ts_utc)` on the `TIMESTAMP WITH TIME ZONE` `ts_utc` column truncate to Vienna-local hour boundaries instead of UTC — invisible on most hours but exposed at DST transitions (`n_subhours=8` instead of `4`). Fixed at the source with `dbt/profiles.yml`'s `settings.TimeZone: UTC`, verified by re-running the build and confirming `n_subhours` is now uniformly `4` at every DST-transition hour checked (2019–2023 fall-backs).

## Task Commits

Each task was committed atomically:

1. **Task 1: Price staging — native dedup + hourly mean with n_subhours** - `07f7d7b` (feat)
2. **Task 2: Load, generation, weather, ÖSPI staging** - `49a84f9` (feat)
3. **Task 3: staging.yml generic tests + DM-020 pre-dedup duplicate-count warn** - `ee7e125` (feat)

## Files Created/Modified
- `dbt/models/staging/stg_prices_at_native.sql` - native MTU AT price passthrough, DM-020 single-point dedup
- `dbt/models/staging/stg_prices_delu_native.sql` - native MTU DE-LU price passthrough, DM-020 single-point dedup
- `dbt/models/staging/stg_prices_at_hourly.sql` - hour-grain AT price mean + n_subhours
- `dbt/models/staging/stg_prices_delu_hourly.sql` - hour-grain DE-LU price mean + n_subhours
- `dbt/models/staging/stg_load_at_hourly.sql` - hour-grain AT load MW mean
- `dbt/models/staging/stg_gen_at_hourly.sql` - hour x psr_type AT generation, aggregated-only (SG-17)
- `dbt/models/staging/stg_weather_graz_daily.sql` - daily Graz temperature rename (date_local, tavg_c)
- `dbt/models/staging/stg_oespi_monthly.sql` - monthly ÖSPI index from CSV (month_local, oespi_base, oespi_peak)
- `dbt/models/staging/staging.yml` - DM-060 unique/not_null generic tests + DM-005/§3-citing descriptions on all 8 models
- `dbt/tests/predup_count_prices.sql` - DM-020 pre-dedup duplicate-count warn singular test (severity='warn')
- `dbt/macros/test_unique_combination_of_columns.sql` - hand-rolled composite-column generic test (zero dbt_utils dependency)
- `dbt/profiles.yml` - added `settings: {TimeZone: UTC}` to the dev target (session-timezone correctness fix)

## Decisions Made
- **Rule 1 (bug):** Pinned `dbt/profiles.yml` `settings.TimeZone: UTC`. DuckDB's session `TimeZone` silently defaults to the host OS's local zone, and `date_trunc('hour'/'month', ts_utc)` on a `TIMESTAMP WITH TIME ZONE` column truncates *in the session timezone*, not UTC. Without this pin, every hourly/monthly staging aggregation in this warehouse would have been silently offset by the local UTC±N hour boundary on machines outside UTC — a correctness bug that would only surface as subtly-wrong hour buckets, most visibly at DST transitions. Fixed once, warehouse-wide, at the connection-settings level (not per-model `AT TIME ZONE`, which DM-011 reserves exclusively for local-attribute derivation that staging must never do).
- **Rule 3 (blocking-adjacent):** Hand-rolled `test_unique_combination_of_columns` macro because dbt-core has no built-in composite-column uniqueness test (only `dbt_utils.unique_combination_of_columns`, and this project carries zero dbt package dependencies per ADR-001/04-01). Used exactly once, for `stg_gen_at_hourly`'s `[ts_utc, psr_type]` grain key.
- `stg_oespi_monthly` parses the CSV's `"YYYY-MM"` string month column via `strptime(month, '%Y-%m')::date` to the first-of-month `DATE` grain key required by SPEC-02 §3 — no calendar-table join needed at this layer.
- `predup_count_prices.sql` unions both `entsoe_prices_at` and `entsoe_prices_delu` raw sources and reports duplicate counts per UTC-month x zone (reading the RAW source directly, never the already-deduped native view), consistent with "defense-in-depth" — it independently detects a spike the DM-020 dedup rule would otherwise silently absorb.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DuckDB session TimeZone defaulted to host-local zone, silently shifting hourly aggregation boundaries**
- **Found during:** Task 1 (price staging build verification)
- **Issue:** After `dbt build --select` of the four price views succeeded, a manual row-count/`n_subhours` spot-check revealed 5 hours per year (the fall-back DST transition, e.g. 2019-10-27 02:00 Vienna-local) with `n_subhours=8` instead of the expected `4`. Root cause: DuckDB's default session `TimeZone` is the host OS's local zone (`Europe/Vienna`), and `date_trunc('hour', ts_utc)` on a `TIMESTAMP WITH TIME ZONE` column truncates in that session timezone — not UTC — even though `ts_utc` itself is a correct UTC instant. This affects every hourly/monthly `date_trunc` in the staging layer, not just prices.
- **Fix:** Added `settings: {TimeZone: UTC}` to `dbt/profiles.yml`'s `dev` target (dbt-duckdb passes this dict through as `SET key = value` on every connection/cursor), forcing UTC truncation warehouse-wide without touching model SQL.
- **Files modified:** `dbt/profiles.yml`
- **Verification:** Re-ran `dbt build --select stg_prices_at_native stg_prices_delu_native stg_prices_at_hourly stg_prices_delu_hourly`; re-queried `n_subhours` distribution — now uniformly `4` including at every DST-transition hour (2019–2023 checked). Also confirmed via `duckdb.connect(...); current_setting('TimeZone')` returning `'UTC'` when queried through the pinned profile.
- **Committed in:** `07f7d7b` (Task 1 commit)

**2. [Rule 3 - Blocking] No native dbt-core composite-column uniqueness test**
- **Found during:** Task 3 (staging.yml generic tests)
- **Issue:** `stg_gen_at_hourly`'s grain key is the composite `[ts_utc, psr_type]`, but dbt-core ships only single-column `unique`/`not_null` generic tests — combination-of-columns uniqueness requires `dbt_utils`, which this project deliberately excludes (ADR-001, 04-01).
- **Fix:** Hand-rolled `dbt/macros/test_unique_combination_of_columns.sql` following the same `{% test name(model, ...) %}` convention as 04-01's `accepted_range` macro — groups by the given column list and flags any combination appearing more than once.
- **Files modified:** `dbt/macros/test_unique_combination_of_columns.sql`, `dbt/models/staging/staging.yml`
- **Verification:** `dbt build --select staging` — `unique_combination_of_columns_stg_gen_at_hourly_ts_utc__psr_type` test PASSes on real data.
- **Committed in:** `ee7e125` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** The TimeZone fix is essential for correctness — without it, every downstream mart built on hourly/monthly staging aggregations would carry silently-wrong hour/month boundaries on any machine not already in UTC. The composite-test macro is a small, ADR-001-consistent addition with no scope creep.

## Issues Encountered
None beyond the auto-fixed items above.

## User Setup Required

None - no external service configuration required; all four raw datasets and the OESPI CSV were already present locally from M1/M2.

## Next Phase Readiness

All 8 SPEC-02 §3 staging views build green on real local data with exact grains/columns/units, single-point DM-020 dedup, `n_subhours`-carrying hourly means, and zero local-timezone-attribute derivation (DM-011). The DuckDB session-timezone pin in `dbt/profiles.yml` benefits every subsequent plan (04-03 dim_calendar/dim_strategy onward) automatically — no further action needed there. `predup_count_prices.sql` is live and correctly non-blocking. No blockers for 04-03 (dim_calendar + dim_strategy).

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-07-24*
