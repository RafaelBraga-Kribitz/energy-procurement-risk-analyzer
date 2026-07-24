---
phase: EPRA-04-m3-dbt-warehouse
plan: 06
subsystem: database
tags: [dbt, dbt-duckdb, duckdb, sql, python, pytest, pyyaml]

# Dependency graph
requires:
  - phase: EPRA-04-m3-dbt-warehouse plan 04
    provides: dbt/models/marts/fct_price_hourly.sql, fct_price_daily.sql, fct_price_monthly.sql, fct_generation_monthly.sql (the SG-05/DM-050 marts these tests assert over)
  - phase: EPRA-04-m3-dbt-warehouse plan 05
    provides: dbt/models/marts/fct_consumer_load_hourly.sql, fct_procurement_cost_monthly.sql (the two future/stand-in marts included in the no-gap test and the schema contract)
provides:
  - dbt/tests/fct_price_hourly_row_count_per_year.sql — DM-062 8760/8784 +/-24 row-count boundary, scoped to calendar-complete years
  - dbt/tests/reconcile_price_monthly_2022_08.sql — DM-064 hardcoded 2022-08 reconciliation, 0.01 tolerance
  - dbt/tests/dst_hour_counts_fct_price_hourly.sql — DM-065 hardcoded 2024-03-31 (23h) / 2024-10-27 (25h) DST adjacency
  - dbt/tests/no_gap_monthly_marts.sql — DM-050 month_spine-based gap check across all 3 monthly marts
  - dbt/tests/freshness_stg_prices_at_hourly.sql — DM-066 var-gated freshness (disabled by default)
  - dbt/contracts/marts_contract.yml — D-07 hand-authored 6-mart name+DuckDB-type schema contract
  - tests/unit/test_marts_contract.py — D-07 pytest information_schema.columns diff test
affects: [EPRA-04-m3-dbt-warehouse plans 07-08 (build-report script and CI dbt-check job read the same dbt build + this contract test as the M3 exit gate); future M5/M6 phases (any mart column rename/retype will be caught by this contract test before it silently breaks downstream analytics)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DM-062's row-count test scopes to 'calendar-complete' years (min(date_local)=local Jan-1 AND max(date_local)=local Dec-31 for that year_local group), computed purely from the mart's own data -- not an external ingestion-window constant -- so dim_calendar's intentional forward-risk-horizon extension (a genuine partial-year artifact at the calendar's edge) doesn't trip a false DM-062 anomaly, mirroring the project's existing ADR-006 'complete years within the ingested window' convention"
    - "marts_contract.yml's top-level keys are the 6 mart names directly (no wrapper key) so tests/unit/test_marts_contract.py can parametrize via sorted(contract) with zero extra unwrapping"
    - "no_gap_monthly_marts.sql checks each monthly mart's own min/max month independently (three separate month_spine CTEs unioned with a mart_name discriminator column) rather than assuming all three marts share one identical window"

key-files:
  created:
    - dbt/tests/fct_price_hourly_row_count_per_year.sql
    - dbt/tests/reconcile_price_monthly_2022_08.sql
    - dbt/tests/dst_hour_counts_fct_price_hourly.sql
    - dbt/tests/no_gap_monthly_marts.sql
    - dbt/tests/freshness_stg_prices_at_hourly.sql
    - dbt/contracts/marts_contract.yml
    - tests/unit/test_marts_contract.py
  modified: []

key-decisions:
  - "Rule 1 bug fix (Task 1): the literal DM-062 row-count test, run over ALL year_local groups unmodified, fails on the real local warehouse -- dim_calendar's forward-risk horizon (SPEC-05) extends to a lone single-hour year_local=2028 artifact (the calendar's very last row). Scoped the test to 'calendar-complete' years only (min/max date_local must equal that year's local Jan-1/Dec-31), computed from the mart's own data so the CI fixture window (D-03, fully bounded 2022-2024) is unaffected and every year in it still runs the check unmodified."
  - "marts_contract.yml uses a flat top-level mapping (mart name -> {columns: [...]}) rather than a version-tagged/wrapped structure, so tests/unit/test_marts_contract.py's parametrize(sorted(contract)) needs no unwrapping step -- matches the plan's own illustrative pytest shape."
  - "fct_procurement_cost_monthly's year_local/month_local are contractually BIGINT (not INTEGER like every dim_calendar-derived year_local/month_local elsewhere) because that mart is a thin loader straight off the processed stand-in parquet, not a dim_calendar join -- captured verbatim from the real built warehouse's information_schema.columns, not assumed."

patterns-established:
  - "Any future DM-06x-style singular test that groups by a calendar-derived year/month boundary should apply the same complete-year/complete-month guard against dim_calendar's intentional forward-risk-horizon extension, rather than assuming every year_local group in a dim_calendar-spined mart is necessarily a full calendar year."

requirements-completed: [REQ-DWH-01, DM-050, DM-062, DM-064, DM-065, DM-066, D-07]

coverage:
  - id: D1
    description: "Five singular dbt tests (DM-062 row-count boundary, DM-064 2022-08 reconciliation, DM-065 DST adjacency, DM-050 no-gap month spine across 3 monthly marts, DM-066 var-gated freshness) all pass on real local data; freshness is skipped by default and fires correctly when the var is explicitly set"
    requirement: "DM-050"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt build (63 PASS / 1 pre-existing WARN 'predup_count_prices' unrelated to this plan / 0 ERROR); cd dbt && uv run dbt build --vars '{check_freshness: true}' --select freshness_stg_prices_at_hourly confirms the test fires (FAIL 1, real last price data is from 2024-02-19, >40 days old) when explicitly enabled, and is absent entirely from the default dbt build output"
        status: pass
    human_judgment: false
  - id: D2
    description: "dbt/contracts/marts_contract.yml hand-authored, parses via yaml.safe_load, enumerates all 6 marts with name+exact DuckDB canonical type per column, fct_price_hourly matches the SG-05 17-column frozen enumeration exactly, lives outside model-paths"
    requirement: "D-07"
    verification:
      - kind: other
        ref: "uv run python -c \"import yaml,pathlib; d=yaml.safe_load(...); assert set(d) == {6 mart names}; assert len(d['fct_price_hourly']['columns'])==17\" -- passes; dbt/contracts/ is not listed in dbt_project.yml's model-paths (['models'])"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/unit/test_marts_contract.py diffs information_schema.columns (schema='marts') against the contract for all 6 marts via epra.common.db.connect(read_only=True) and yaml.safe_load; passes against the real built warehouse; fails loudly (naming the mart + offending column) when a contract column is renamed, then cleanly reverted"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/unit/test_marts_contract.py::test_mart_schema_matches_contract[fct_price_hourly|fct_price_daily|fct_price_monthly|fct_generation_monthly|fct_consumer_load_hourly|fct_procurement_cost_monthly] -- uv run pytest tests/unit/test_marts_contract.py -m \"not live\" --no-cov: 6 passed"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-24
status: complete
---

# Phase EPRA-04 Plan 06: DM-050/062/064/065/066 Test Suite + D-07 Schema Contract Summary

**The M3 exit-gate test set: five singular dbt tests (row-count boundary, 2022-08 reconciliation, DST adjacency, no-gap month spine, var-gated freshness) plus a hand-authored 6-mart schema contract and its byte-exact pytest diff test — all verified green against this repository's real 2019-2028 (calendar horizon) warehouse**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-24T09:36Z
- **Tasks:** 3/3
- **Files modified:** 7 (all created)

## Accomplishments
- Five singular dbt tests wired: `fct_price_hourly_row_count_per_year.sql` (DM-062, 8760/8784 ±24, scoped to calendar-complete years), `reconcile_price_monthly_2022_08.sql` (DM-064, hardcoded 2022-08, 0.01 tolerance), `dst_hour_counts_fct_price_hourly.sql` (DM-065, hardcoded 2024-03-31/2024-10-27), `no_gap_monthly_marts.sql` (DM-050, `month_spine`-based gap check across `fct_price_monthly`/`fct_generation_monthly`/`fct_procurement_cost_monthly`), and `freshness_stg_prices_at_hourly.sql` (DM-066, `config(enabled=var('check_freshness', false))` — confirmed absent from a normal `dbt build` and confirmed to FAIL correctly when `--vars '{check_freshness: true}'` is passed against real stale price data)
- Full `dbt build` on real local data: **63 PASS / 1 pre-existing WARN (`predup_count_prices`, unrelated) / 0 ERROR**
- `dbt/contracts/marts_contract.yml` hand-authored from the real built warehouse's `information_schema.columns` — all 6 marts, each column's exact DuckDB canonical type string, `fct_price_hourly` matching the SG-05 17-column frozen enumeration exactly; lives outside `dbt_project.yml`'s `model-paths` on purpose (Pitfall 3)
- `tests/unit/test_marts_contract.py` parametrizes over the 6 marts, diffs `information_schema.columns` against the contract via `epra.common.db.connect(read_only=True)` and `yaml.safe_load` (never `yaml.load`) — 6/6 pass against the real warehouse; drift-proof exercised (temporarily renamed one contract column, confirmed the test failed naming `fct_price_hourly`'s `price_at_eur_mwh` column, then reverted with a clean `git diff`)
- Full non-live pytest suite after all three tasks: **251 passed, 2 skipped, 1 deselected**, coverage 94.89% (well above the 80% gate)

## Task Commits

Each task was committed atomically:

1. **Task 1: Singular dbt tests — DM-062/064/065 + DM-050 no-gap + DM-066 freshness** - `b67dd36` (feat)
2. **Task 2: marts_contract.yml — hand-authored 6-mart schema contract (D-07)** - `411d8c8` (feat)
3. **Task 3: test_marts_contract.py — information_schema diff vs contract (D-07)** - `1f25aa6` (test)

## Files Created/Modified
- `dbt/tests/fct_price_hourly_row_count_per_year.sql` - DM-062 row-count boundary, scoped to calendar-complete years
- `dbt/tests/reconcile_price_monthly_2022_08.sql` - DM-064 hardcoded 2022-08 reconciliation
- `dbt/tests/dst_hour_counts_fct_price_hourly.sql` - DM-065 hardcoded DST adjacency
- `dbt/tests/no_gap_monthly_marts.sql` - DM-050 month-spine gap check, 3 monthly marts
- `dbt/tests/freshness_stg_prices_at_hourly.sql` - DM-066 var-gated freshness (disabled by default)
- `dbt/contracts/marts_contract.yml` - D-07 hand-authored 6-mart name+type contract
- `tests/unit/test_marts_contract.py` - D-07 pytest information_schema diff test

## Decisions Made
- **Rule 1 (bug fix):** Scoped the DM-062 row-count test to "calendar-complete" years (a year_local group qualifies only if the mart contains a row for both its local Jan-1 and local Dec-31) after discovering that the literal, unscoped version fails on the real warehouse due to `dim_calendar`'s intentional forward-risk-horizon extension producing a lone single-hour `year_local=2028` artifact at the calendar's edge. This mirrors the project's existing ADR-006 "complete years within the ingested window" convention from M1/M2's ingestion gates, and is computed entirely from the mart's own `date_local` column — no external ingestion-window constant — so it's a no-op change for the fully-bounded CI fixture window (D-03, 2022-2024).
- `marts_contract.yml`'s top-level structure is a flat `{mart_name: {columns: [...]}}` mapping (no `version`/wrapper key), matching the plan's own illustrative `parametrize(sorted(contract))` pytest shape exactly, rather than the initially-drafted `{version, marts: {...}}` nested structure.
- Captured `fct_procurement_cost_monthly.year_local`/`month_local` as `BIGINT` (not `INTEGER`) in the contract — verified directly against the real built warehouse's `information_schema.columns`, since that mart loads straight off `source('raw_processed', ...)` rather than joining `dim_calendar`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DM-062 row-count test failed on real data due to the calendar's forward-risk-horizon boundary**
- **Found during:** Task 1 (`dbt build` verification)
- **Issue:** The literal DM-062 test (group all `fct_price_hourly` rows by `year_local`, flag any year outside 8760/8784 ±24) failed with `year_local=2028` having only 1 row (expected 8784) — `dim_calendar`'s SPEC-05 forward-risk horizon extends the calendar spine to exactly `2028-01-01`, producing a genuine but non-anomalous 1-hour partial "year" at the very edge.
- **Fix:** Added a "calendar-complete year" filter (a year_local group's `min(date_local)`/`max(date_local)` must equal that year's local Jan-1/Dec-31) before applying the ±24 tolerance check — excludes only genuine boundary-edge partial years, not real missing-hour anomalies.
- **Files modified:** `dbt/tests/fct_price_hourly_row_count_per_year.sql` (this plan's own new file only)
- **Verification:** `cd dbt && uv run dbt build` — 63 PASS / 1 pre-existing WARN / 0 ERROR (previously 1 ERROR, 11 SKIP from downstream-of-failure).
- **Committed in:** `b67dd36` (Task 1 commit)

**2. [Rule 3 - Blocking] mypy rejected `fetchone()`'s `tuple | None` return without a narrowing check**
- **Found during:** Task 3 (`uv run mypy tests/unit/test_marts_contract.py`)
- **Issue:** `con.execute(...).fetchone()` is typed `tuple[Any, ...] | None`; unpacking directly (`(count,) = ...`) is a `[misc]` mypy error since `None` isn't iterable.
- **Fix:** Assigned to `row`, added an explicit `if row is None: return False` before indexing `row[0]`.
- **Files modified:** `tests/unit/test_marts_contract.py`
- **Verification:** `uv run mypy tests/unit/test_marts_contract.py` — Success, no issues.
- **Committed in:** `1f25aa6` (Task 3 commit)

**3. [Rule 3 - Blocking] ruff flagged an unused `pathlib.Path` import**
- **Found during:** Task 3 (`uv run ruff check tests/unit/test_marts_contract.py`)
- **Issue:** `Path` was imported but never referenced (only `REPO_ROOT` from `epra.common.config` was needed to build `CONTRACT_PATH`).
- **Fix:** Removed the unused import.
- **Files modified:** `tests/unit/test_marts_contract.py`
- **Verification:** `uv run ruff check tests/unit/test_marts_contract.py` — All checks passed.
- **Committed in:** `1f25aa6` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three fixes are confined to this plan's own new files; no scope creep, no changes to any prior plan's marts or dbt config. The DM-062 scoping fix is necessary for correctness against real data (the literal spec-text test would otherwise permanently fail the M3 exit gate on this repository's real warehouse due to an unrelated, already-established calendar-horizon design decision from 04-01/04-03).

## Issues Encountered
- Running `uv run pytest tests/unit/test_marts_contract.py -m "not live" -x` in isolation (the plan's own literal verify command) exits 1 due to this repo's project-wide `--cov-fail-under=80` pytest config applying to the narrow single-file subset (6.98% coverage of the full `epra` package when only this one test file runs) — this is pre-existing, project-wide behavior confirmed identical when running any other single narrow test file (e.g. `tests/test_raw_contracts.py` alone also exits 1 the same way), not something introduced by or fixable within this plan's files. The actual test outcome (what the acceptance criteria cares about) is unambiguous: "6 passed" with zero assertion failures. The full non-live suite (`uv run pytest -m "not live"`) passes coverage comfortably (94.89%).

## User Setup Required

None — all inputs (real local warehouse, the four price/generation marts from 04-04, the two future marts from 04-05) were already present and built.

## Next Phase Readiness

The M3 exit-gate test set (DM-050/062/064/065/066) and the D-07 schema contract + diff test are complete and green on real local data. `dbt build` is 63 PASS / 1 pre-existing WARN / 0 ERROR; `tests/unit/test_marts_contract.py` is 6/6 pass. Ready for 04-07 (build-report writer, D-02) and 04-08 (CI fixture bootstrap + `dbt-check` job, D-04) to consume this same test suite as the M3 close-out gate. No blockers.

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-07-24*

## Self-Check: PASSED

All 7 created files found on disk; all 3 commit hashes (`b67dd36`, `411d8c8`, `1f25aa6`) found in git log.
