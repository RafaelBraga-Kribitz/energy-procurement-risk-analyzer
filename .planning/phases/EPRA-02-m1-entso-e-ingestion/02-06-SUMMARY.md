---
phase: EPRA-02-m1-entso-e-ingestion
plan: 06
subsystem: infra
tags: [validation, data-quality, pandas, entsoe, dst, cli]

# Dependency graph
requires:
  - phase: EPRA-02-04
    provides: entsoe.hourly_mean, entsoe.py Appendix-A parsers
  - phase: EPRA-02-05
    provides: entsoe ingest_dataset/backfill orchestration, _io.write_month
provides:
  - GateResult/ValidationReport gate framework (src/epra/ingest/validate.py)
  - gate_ing_080..085 pure gate functions with synthetic pass/fail tests
  - run_gates loader (glob raw parquet -> hourly_mean -> gates -> markdown report)
  - validate.main() CLI and wired `make validate-ingest`
affects: [M2-geosphere-oespi, M3-dbt-warehouse]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gate function signature: gate_ing_XXX(hourly_df(s)) -> GateResult, pure, no I/O, no mutation"
    - "ValidationReport aggregates GateResults, renders markdown, raise_if_failed() on any failure (EN-061)"
    - "run_gates aggregates raw parquet to hourly mean BEFORE gating (avoids ING-080 false-missing-hours on PT15M data)"

key-files:
  created:
    - tests/unit/test_ingest_gates.py
  modified:
    - src/epra/ingest/validate.py
    - Makefile
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "ING-080 DST correctness check counts hourly-aggregated ROWS whose Europe/Vienna local date equals the last Sunday of March/October (not distinct hour-of-day labels), matching timeutil.local_hours_in_day's own row-count semantics -- verified empirically (23/25) against a real full-year UTC hourly grid before implementing"
  - "ING-080/081/082/084/085 return passed=False with an explanatory summary when given empty input, rather than vacuously passing -- 'no data' is itself a real problem, never silently skipped"
  - "gate_ing_082 fails a year not present in the SPEC-01 table at all (not just out-of-range) -- a new year needs the table extended via ADR, never silently passed through"
  - "run_gates gates only the three hourly ENTSO-E datasets with a §8 gate defined (entsoe_prices_at, entsoe_prices_delu, entsoe_load_at); entsoe_gen_at has no §8 gate and is excluded"

patterns-established:
  - "Gate framework: GateResult (frozen dataclass: gate_id, passed, summary, evidence) + ValidationReport (add/render_markdown/raise_if_failed), reusable for M2 GeoSphere/ÖSPI gates"

requirements-completed: [REQ-ING-01, ING-080, ING-081, ING-082, ING-083, ING-084, ING-085]

coverage:
  - id: D1
    description: "gate_ing_080 (hour coverage per zone-year, <=24 missing) + DST 23/25 correctness check via timeutil.local_hours_in_day"
    requirement: "ING-080"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_080_passes_on_full_year_coverage"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_080_fails_when_missing_hours_exceed_24"
        status: pass
    human_judgment: false
  - id: D2
    description: "gate_ing_081 hourly AT price plausibility [-500, 5000] EUR/MWh"
    requirement: "ING-081"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_081_passes_within_bounds"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_081_fails_when_price_exceeds_ceiling"
        status: pass
    human_judgment: false
  - id: D3
    description: "gate_ing_082 AT annual mean plausibility table (SPEC-01 SS8, per-year ranges)"
    requirement: "ING-082"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_082_passes_within_annual_mean_table"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_082_fails_when_annual_mean_outside_table"
        status: pass
    human_judgment: false
  - id: D4
    description: "gate_ing_083 negative prices required in 2023/2024/2025"
    requirement: "ING-083"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_083_passes_when_each_year_has_a_negative_price"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_083_fails_when_a_year_has_no_negative_price"
        status: pass
    human_judgment: false
  - id: D5
    description: "gate_ing_084 AT load plausibility (hourly 3000-13000 MW, annual mean 6000-9000 MW)"
    requirement: "ING-084"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_084_passes_within_bands"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_084_fails_when_hourly_load_exceeds_ceiling"
        status: pass
    human_judgment: false
  - id: D6
    description: "gate_ing_085 price/load join coverage >=99.5% per year"
    requirement: "ING-085"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_085_passes_on_full_join_coverage"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_085_fails_when_join_coverage_below_threshold"
        status: pass
    human_judgment: false
  - id: D7
    description: "run_gates loads raw parquet, aggregates to hourly mean, runs ING-080..085, writes reports/ingestion/validation_<date>.md, raises GateFailure on any failure"
    requirement: "REQ-ING-01"
    verification:
      - kind: integration
        ref: "tests/unit/test_ingest_gates.py#test_run_gates_passes_and_writes_report_on_good_synthetic_data"
        status: pass
      - kind: integration
        ref: "tests/unit/test_ingest_gates.py#test_run_gates_raises_and_still_writes_report_on_incomplete_data"
        status: pass
      - kind: integration
        ref: "tests/unit/test_ingest_gates.py#test_run_gates_creates_reports_ingestion_dir_if_missing"
        status: pass
    human_judgment: false
  - id: D8
    description: "validate.main() CLI + make validate-ingest wired to python -m epra.ingest.validate"
    requirement: "REQ-ING-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_stubs_fail_loudly.py (validate rows removed -- no stub remains)"
        status: pass
      - kind: manual_procedural
        ref: "uv run python -m epra.ingest.validate (manual run against real, empty data_raw/ -- correctly fails loud with exit 1, all six gates report 'no data supplied')"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-07-21
status: complete
---

# Phase EPRA-02 Plan 06: ENTSO-E Validation Gate Framework Summary

**ING-080..085 pure gate functions + GateResult/ValidationReport framework + run_gates loader/report-writer + wired `make validate-ingest` CLI, all with synthetic pass/fail unit test coverage.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-07-21T21:40:00Z
- **Completed:** 2026-07-21T22:25:00Z
- **Tasks:** 3
- **Files modified:** 3 (`src/epra/ingest/validate.py`, `Makefile`, `tests/unit/test_stubs_fail_loudly.py`) + 1 created (`tests/unit/test_ingest_gates.py`)

## Accomplishments

- Implemented `GateResult` (frozen dataclass) and `ValidationReport` (`render_markdown`, `raise_if_failed`) exactly per `03_MODULES.md`'s `epra.ingest.validate` contract
- Implemented all six SPEC-01 §8 gate functions (`gate_ing_080`..`gate_ing_085`) as pure functions, each with one passing and one failing synthetic unit test (12 tests total), plus 3 framework tests and 2 extra robustness tests (input-mutation-avoided, empty-input handling)
- Implemented `run_gates(settings)`: globs monthly raw parquet for `entsoe_prices_at`/`entsoe_prices_delu`/`entsoe_load_at`, aggregates each to hourly mean via `entsoe.hourly_mean` (reused, not reimplemented) BEFORE gating, registers all six gates in order, writes `reports/ingestion/validation_<date>.md`, and raises `GateFailure` naming every failed gate id
- Implemented `validate.main()` CLI and wired `Makefile`'s `validate-ingest` target to `uv run python -m epra.ingest.validate`
- Removed the two M1 `validate.run_gates`/`validate.main` rows from `tests/unit/test_stubs_fail_loudly.py` — no validate stubs remain

## Task Commits

Each task was committed atomically:

1. **Task 1: GateResult, ValidationReport, pure gate functions** - `2c9cbea` (feat)
2. **Task 2: run_gates loader and report writer** - `3c660b8` (feat)
3. **Task 3: validate CLI and Makefile** - `57b1232` (feat)

**Plan metadata:** (this commit, following SUMMARY.md write)

## Files Created/Modified

- `src/epra/ingest/validate.py` - `GateResult`, `ValidationReport`, `gate_ing_080..085`, `run_gates`, `_load_hourly`, `_write_report`, `main` (full M1 validation gate framework, replacing the M1 stub)
- `tests/unit/test_ingest_gates.py` - 22 synthetic unit/integration tests (framework, 6 gates x pass/fail, `run_gates` loader/report-writer integration)
- `Makefile` - `validate-ingest` target now invokes the real CLI instead of the M1 "not implemented" stub
- `tests/unit/test_stubs_fail_loudly.py` - removed `("M1", validate.run_gates, ...)` and `("M1", validate.main, ...)` rows and the now-unused `validate` import

## Decisions Made

- ING-080's DST correctness check counts hourly-aggregated ROWS whose Europe/Vienna local date equals the last-Sunday-of-March/October date (not distinct hour-of-day labels 0-23) — this is the semantics that actually yields 23/25, matching `timeutil.local_hours_in_day`. Verified empirically against a real full-year UTC hourly `pd.date_range` before writing the implementation (see environment_notes verification in this session: march count 23, oct count 25).
- Gates that receive empty/no input return `passed=False` with an explanatory summary rather than vacuously passing — absence of data is itself a real problem (A-2: never silently skip).
- `gate_ing_082` treats a year outside the documented SPEC-01 §8 table as a failure (not a skip) — extending the table for a new year requires an ADR, never a silent code change.
- `run_gates` gates the three hourly ENTSO-E datasets that have a §8 gate defined; `entsoe_gen_at` (generation) has no §8 gate and is excluded from the M1 loader, per the plan's "M1 scope only" instruction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Typed-empty DataFrame for datasets with no ingested data yet**
- **Found during:** Task 2 (integration test `test_run_gates_raises_and_still_writes_report_on_incomplete_data`)
- **Issue:** `_load_hourly`'s original empty-frame fallback (`pd.DataFrame(columns=["ts_utc", value_col])`) produced `object`-dtype columns, causing `AttributeError: Can only use .dt accessor with datetimelike values` inside `gate_ing_084` when a dataset (e.g. AT load) has zero ingested months.
- **Fix:** Changed the empty fallback to explicit `datetime64[ns, UTC]`/`float64` typed empty Series, and added explicit `if frame.empty: return GateResult(..., False, "no ... data supplied ...")` early-return guards to `gate_ing_081` and `gate_ing_084` (mirroring the "no rows" guards already present in `gate_ing_080`/`082`/`085`) so an empty input is a clean, correctly-typed failure rather than a crash or a vacuous pass.
- **Files modified:** `src/epra/ingest/validate.py`
- **Verification:** `test_run_gates_raises_and_still_writes_report_on_incomplete_data` and `test_run_gates_creates_reports_ingestion_dir_if_missing` pass; full suite green.
- **Committed in:** `3c660b8` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix, Rule 1)
**Impact on plan:** Necessary for correctness (empty-dataset handling is a real M1 scenario before backfill has run for all four datasets). No scope creep — fix stayed entirely within `validate.py`, the plan's own `files_modified`.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `make validate-ingest` is fully wired and runnable; manually verified against the current (empty) `data_raw/` tree — correctly reports all six gates as `FAIL` ("no data supplied") and exits 1, confirming fail-loud behavior before any real backfill has run.
- ENTSO-E validation gate framework (`GateResult`/`ValidationReport`) is a reusable pattern for M2's GeoSphere (`ING-094`) and ÖSPI (`ING-101`/`ING-103`) gates.
- Once a real ENTSO-E backfill (`make backfill`) is run against `data/raw/`, `make validate-ingest` should be re-run and the resulting `reports/ingestion/validation_<date>.md` committed per AGENTS.md's M1 gate ("run `make validate-ingest`, commit the validation report") — this is the ROADMAP's phase-2 success criterion 3, now unblocked by this plan but not yet exercised against real data (no token-consuming backfill was run in this plan, per scope).
- Full test suite: 129 tests, only the pre-existing unrelated `test_entsoe_token_fails_fast_when_unset` flake fails (logged since `02-02`, out of scope); 95.77% coverage. `mypy --strict` clean across all 30 source files. `ruff check` clean; `ruff format --check` clean on all files touched by this plan (one pre-existing, unrelated formatting drift in `tests/unit/test_aggregate_hourly.py` persists from `02-05`, reconfirmed out of scope — see `deferred-items.md`).

---
*Phase: EPRA-02-m1-entso-e-ingestion*
*Completed: 2026-07-21*

## Self-Check: PASSED

- FOUND: src/epra/ingest/validate.py
- FOUND: tests/unit/test_ingest_gates.py
- FOUND: .planning/phases/EPRA-02-m1-entso-e-ingestion/02-06-SUMMARY.md
- FOUND: commit 2c9cbea (Task 1)
- FOUND: commit 3c660b8 (Task 2)
- FOUND: commit 57b1232 (Task 3)
