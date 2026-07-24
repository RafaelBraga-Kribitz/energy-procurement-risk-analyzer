---
phase: EPRA-04-m3-dbt-warehouse
plan: 04
subsystem: database
tags: [dbt, dbt-duckdb, duckdb, sql]

# Dependency graph
requires:
  - phase: EPRA-04-m3-dbt-warehouse plan 03
    provides: dbt/models/marts/dim_calendar.sql (ts_utc-keyed local attributes, is_peak_hour, season, hdd_18/cdd_22 spine every fct_* mart joins on)
provides:
  - dbt/models/marts/fct_price_hourly.sql — SG-05 full enumeration, dim_calendar-spined hour-grain price/load mart
  - dbt/models/marts/fct_price_daily.sql — local day-grain price aggregation, holiday-aware peak (NULL on no-peak days)
  - dbt/models/marts/fct_price_monthly.sql — local month-grain price aggregation + ÖSPI join
  - dbt/models/marts/fct_generation_monthly.sql — local month x psr_type generation (gen_gwh, share_of_total)
  - dbt/models/marts/facts_price.yml — DM-060 unique/not_null + DM-061 accepted-range tests on the four marts
  - docs/ADR/ADR-011_holiday-aware-peak.md — SG-14 one-holiday-aware-is_peak_hour decision
  - LIMITATIONS.md §2 ÖSPI-peak-vs-internal-peak-convention entry
affects: [EPRA-04-m3-dbt-warehouse plan 06 (M3 exit-gate schema contract diff-checks these 4 marts + DM-062/064/065 tests reference fct_price_hourly/fct_price_monthly)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every price mart is spined on dim_calendar (left join staging views onto it, never the reverse) so ts_utc/date_local is never NULL even where a source dataset is momentarily missing (DM-050)"
    - "Peak-price aggregation always uses `avg(...) filter (where is_peak_hour)` — the empty-input SQL semantics (zero matching rows -> NULL) IS the SG-14/ADR-011 no-peak-day contract, not a special-cased branch"
    - "Generic-test arguments in this project's dbt YAML now use the dbt 1.12 nested `arguments:` property (not top-level args) to avoid MissingArgumentsPropertyInGenericTestDeprecation"

key-files:
  created:
    - dbt/models/marts/fct_price_hourly.sql
    - dbt/models/marts/fct_price_daily.sql
    - dbt/models/marts/fct_price_monthly.sql
    - dbt/models/marts/fct_generation_monthly.sql
    - dbt/models/marts/facts_price.yml
    - docs/ADR/ADR-011_holiday-aware-peak.md
    - .planning/phases/EPRA-04-m3-dbt-warehouse/deferred-items.md
  modified:
    - LIMITATIONS.md
    - dbt/macros/test_accepted_range.sql

key-decisions:
  - "ADR-011: exactly one is_peak_hour (dim_calendar, holiday-aware ING-110) drives price_peak_eur_mwh everywhere; price_peak_eur_mwh is NULL (not 0) on local days/months with zero peak hours — verified on real holiday dates (2019-06-10, 2019-06-20, 2020-10-26, 2021-05-01, 2021-05-13)."
  - "fct_price_daily joins stg_weather_graz_daily directly (on date_local) to source tavg_c, since dim_calendar itself only exposes the derived hdd_18/cdd_22, not the raw temperature — this is a same-grain source join, not a timezone-conversion call."
  - "fct_price_monthly joins stg_oespi_monthly by extracting year/month from its DATE month_local key, matching against the mart's own year_local/month_local grouping columns."
  - "Column names price_min/price_max/price_std (no _eur_mwh suffix) used verbatim per SPEC-02 §5's literal contract text, since 04-06's schema diff-check is byte-exact against that contract."
  - "Rule 1 bug fix: nested all new generic-test arguments (accepted_range, unique_combination_of_columns) in facts_price.yml under dbt 1.12's arguments: property to eliminate MissingArgumentsPropertyInGenericTestDeprecation warnings on this plan's own file; the pre-existing same-class warning in staging.yml (04-02, out of scope) is logged to deferred-items.md rather than touched."

patterns-established:
  - "Price/generation marts never recompute local attributes or peak-hour classification — they consume dim_calendar's is_peak_hour/date_local/year_local/month_local verbatim via a join, continuing the DM-011 single-source-of-truth convention from 04-03."

requirements-completed: [REQ-DWH-01, DM-050, DM-061, SG-05, SG-14]

coverage:
  - id: D1
    description: "fct_price_hourly emits exactly the SG-05 enumeration, spined on dim_calendar so ts_utc is never NULL, builds green on real local data"
    requirement: "DM-050"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select fct_price_hourly (exit 0); grep confirms spread_at_delu_eur_mwh/is_negative_price/all 11 dim_calendar attribute names present and zero timezone-conversion calls; manual query confirms row count 78,888 matches dim_calendar's full spine with 44,733/45,261 non-null price/load rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "fct_price_daily/fct_price_monthly aggregate holiday-aware is_peak_hour (NULL on no-peak days/months), fct_price_monthly joins ÖSPI, ADR-011 + LIMITATIONS §2 recorded"
    requirement: "SG-14"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select fct_price_daily fct_price_monthly (exit 0); manual query on real data confirms price_peak_eur_mwh IS NULL on 2019-06-10/06-20, 2020-10-26, 2021-05-01/05-13 (Austrian weekday holidays) while price_base_eur_mwh remains populated; fct_price_monthly has 109 rows with 92 oespi_base/oespi_peak non-null (matches 92-month ÖSPI coverage from 04-06 M2 close-out); docs/ADR/ADR-011_holiday-aware-peak.md and LIMITATIONS.md §2 both present"
        status: pass
    human_judgment: false
  - id: D3
    description: "fct_generation_monthly computes gen_gwh/share_of_total correctly; facts_price.yml pins DM-060/DM-061 tests green on all four marts"
    requirement: "DM-061"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build --select fct_price_hourly fct_price_daily fct_price_monthly fct_generation_monthly (19/19 PASS: 4 models + 15 generic tests, 0 error, 0 warn); manual query confirms share_of_total sums to ~1.0 (0.9999999999999999-1.0 floating-point) per year_local/month_local across 806 rows / 13 psr_types; full-project dbt build re-run: 50 PASS / 1 pre-existing non-blocking WARN (predup_count_prices, unrelated to this plan) / 0 ERROR"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-24
status: complete
---

# Phase EPRA-04 Plan 04: Price/Generation Marts (fct_price_hourly/daily/monthly, fct_generation_monthly) Summary

**Four price/generation marts built off real local raw data — the SG-05 frozen hourly enumeration spined on `dim_calendar`, holiday-aware peak pricing with the SG-14/ADR-011 NULL-on-no-peak-days contract verified on real Austrian holiday dates, ÖSPI join, and DM-060/DM-061 generic tests all green**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-24T08:57:53Z
- **Tasks:** 3/3
- **Files modified:** 9 (7 created + 2 modified: LIMITATIONS.md, dbt/macros/test_accepted_range.sql)

## Accomplishments
- `fct_price_hourly` builds green with the exact SG-05 enumeration (`ts_utc, price_at_eur_mwh, price_delu_eur_mwh, spread_at_delu_eur_mwh, load_at_mw, is_negative_price` + all 11 dim_calendar attributes), spined on `dim_calendar` so every one of the 78,888 calendar hours is present and `ts_utc` is never NULL (DM-050), with zero timezone-conversion calls
- `fct_price_daily`/`fct_price_monthly` aggregate the ONE holiday-aware `is_peak_hour` (never a separate Mon-Fri-08-20-ignoring-holidays rule) — verified on real data that `price_peak_eur_mwh` is genuinely `NULL` (not 0, not the base price) on five real Austrian weekday holidays (2019-06-10 Corpus Christi, 2019-06-20 Fronleichnam-adjacent, 2020-10-26 National Day, 2021-05-01 Labour Day, 2021-05-13 Ascension), the SG-14/ADR-011 empty-input contract
- `fct_price_monthly` left-joins `stg_oespi_monthly` for `oespi_base`/`oespi_peak` (109 monthly rows, 92 with ÖSPI coverage matching the real transcribed window)
- `fct_generation_monthly` computes `gen_gwh = sum(gen_mw)/1000` and `share_of_total` per local month x psr_type across 806 rows / 13 psr_types; spot-checked `share_of_total` sums to ~1.0 (floating-point) in every sampled month
- `docs/ADR/ADR-011_holiday-aware-peak.md` records the SG-14 decision (Context/Decision/Consequences/Spec deviations); `LIMITATIONS.md` §2 gets a new paragraph documenting the ÖSPI-peak vs. internal-peak convention gap
- `facts_price.yml` pins DM-060 unique/not_null on all four marts' grain keys (composite keys via the 04-02 hand-rolled `unique_combination_of_columns` macro) and DM-061 accepted ranges: `price_at_eur_mwh` [-500, 5000], `load_at_mw` [3000, 13000], `tavg_c` [-30, 42], `oespi_base` > 0 (min_value 0.01) — 19/19 PASS (4 models + 15 generic tests)
- Full-project `dbt build` re-run after all three tasks: 50 PASS / 1 WARN (the pre-existing, non-blocking `predup_count_prices` DM-020 warn from 04-02, unrelated to this plan) / 0 ERROR — no regression to staging, `dim_calendar`, or `dim_strategy`

## Task Commits

Each task was committed atomically:

1. **Task 1: fct_price_hourly — SG-05 full enumeration, dim_calendar-joined** - `44cf0e8` (feat)
2. **Task 2: fct_price_daily + fct_price_monthly (holiday-aware peak, ÖSPI join) + ADR-011 + LIMITATIONS §2** - `a287798` (feat)
3. **Task 3: fct_generation_monthly + facts_price.yml (DM-060/DM-061 tests)** - `d9af2ce` (feat)

## Files Created/Modified
- `dbt/models/marts/fct_price_hourly.sql` - SG-05 enumeration, dim_calendar-spined
- `dbt/models/marts/fct_price_daily.sql` - daily aggregates, holiday-aware peak NULL-on-no-peak-days
- `dbt/models/marts/fct_price_monthly.sql` - monthly base/peak/offpeak + ÖSPI join
- `dbt/models/marts/fct_generation_monthly.sql` - gen_gwh + share_of_total
- `dbt/models/marts/facts_price.yml` - DM-060 keys + DM-061 accepted ranges for the four marts
- `docs/ADR/ADR-011_holiday-aware-peak.md` - SG-14 holiday-aware peak decision + ÖSPI-convention caveat
- `LIMITATIONS.md` - §2 entry on the ÖSPI-peak vs internal-peak convention note
- `dbt/macros/test_accepted_range.sql` - docstring usage example updated to the nested `arguments:` form (Rule 1)
- `.planning/phases/EPRA-04-m3-dbt-warehouse/deferred-items.md` - new file logging one out-of-scope discovery

## Decisions Made
- **Rule 1 (bug):** dbt 1.12 emits `MissingArgumentsPropertyInGenericTestDeprecation` for generic-test arguments passed as top-level YAML keys instead of nested under `arguments:`. Fixed in `facts_price.yml` (my own new file) for both `accepted_range` and `unique_combination_of_columns` invocations, and updated the `test_accepted_range.sql` macro's usage docstring to match. The pre-existing identical pattern in `staging.yml` (04-02, already committed, not in this plan's `files_modified`) is out of scope per the scope-boundary rule — logged to `deferred-items.md` instead of touched.
- `fct_price_daily` sources `tavg_c` via a direct join to `stg_weather_graz_daily` on `date_local`, since `dim_calendar` only carries the derived `hdd_18`/`cdd_22` (not the raw temperature) — a same-grain source join, not a timezone-conversion call, so DM-011 is unaffected.
- `fct_price_monthly` joins `stg_oespi_monthly` by extracting the year/month components from its `DATE` `month_local` key and matching against the mart's own `year_local`/`month_local` grouping columns (no shared date-typed key exists between the two).
- Used the literal SPEC-02 §5 column names `price_min`, `price_max`, `price_std` (no `_eur_mwh` suffix) rather than a more verbose-but-consistent alternative, since 04-06's schema-contract diff check is byte-exact against the spec text.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] dbt 1.12 generic-test argument deprecation warning**
- **Found during:** Task 3 (facts_price.yml build verification)
- **Issue:** The first `dbt build` of the four marts with their new tests logged 6 `MissingArgumentsPropertyInGenericTestDeprecation` warnings — dbt 1.12 deprecates passing generic-test parameters (`min_value`/`max_value`/`combination_of_columns`) as top-level YAML keys under a test name; they must be nested under an `arguments:` property.
- **Fix:** Rewrote all 5 `accepted_range`/`unique_combination_of_columns` invocations in `facts_price.yml` to nest their parameters under `arguments:`, and updated the `test_accepted_range.sql` macro's usage-example docstring to match. Re-running the build dropped the deprecation count from 6 to 1 (the 1 remaining is the pre-existing, out-of-scope `staging.yml` occurrence from 04-02).
- **Files modified:** `dbt/models/marts/facts_price.yml`, `dbt/macros/test_accepted_range.sql`
- **Verification:** `dbt build --select fct_price_hourly fct_price_daily fct_price_monthly fct_generation_monthly --show-all-deprecations --no-partial-parse` — confirmed the single remaining deprecation instance names `stg_gen_at_hourly`/`staging.yml`, not any file this plan touches.
- **Committed in:** `d9af2ce` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Purely a forward-compatibility fix within this plan's own new file; no scope creep, no behavior change to any mart's data.

## Issues Encountered
None beyond the auto-fixed item above.

## User Setup Required

None — all inputs (`dim_calendar`, the 8 staging views, `stg_oespi_monthly`) were already present from 04-02/04-03.

## Next Phase Readiness

The four price/generation marts (`fct_price_hourly`, `fct_price_daily`, `fct_price_monthly`, `fct_generation_monthly`) are built, tested, and documented — four of the six marts the M3 exit-gate schema contract (04-06) will diff-check. `docs/ADR/ADR-011` and `LIMITATIONS.md` §2 are ready for 04-06's documentation-completeness checks. No blockers for 04-05 (`fct_consumer_load_hourly`/`fct_procurement_cost_monthly`, which this plan deliberately did not touch — those files remain 04-05's exclusive territory).

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-07-24*

## Self-Check: PASSED

All 9 created/modified files found on disk; all 3 commit hashes (`44cf0e8`, `a287798`, `d9af2ce`) found in git log.
