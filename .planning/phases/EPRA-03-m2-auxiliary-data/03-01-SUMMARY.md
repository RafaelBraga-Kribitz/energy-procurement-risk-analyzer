---
phase: EPRA-03-m2-auxiliary-data
plan: 01
subsystem: ingest
tags: [pandas, pyarrow, write_month, key_column, geosphere, tdd]

# Dependency graph
requires:
  - phase: EPRA-02-m1-entso-e-ingestion
    provides: "_io.write_month() atomic raw-parquet writer (ING-003/004/005/070) and its ts_utc validation contract"
provides:
  - "write_month(..., *, key_column='ts_utc') — additive keyword-only parameter, default preserves ts_utc byte-for-byte"
  - "_validate_date_key() — tz-naive date-grain validator for GeoSphere-shaped datasets"
  - "_validate_ts_utc_key() — existing tz-aware-UTC validator, relocated unchanged"
  - "_month_bounds() — shared calendar-month bounds helper for both key modes"
affects: [EPRA-03-04-geosphere-ingest]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Validation dispatcher keyed on key_column, both branches sharing one atomic-write/provenance tail (single writer, WR-03)"

key-files:
  created: []
  modified:
    - src/epra/ingest/_io.py
    - tests/unit/test_io.py

key-decisions:
  - "key_column promoted from an implicit-only ts_utc anchor to a keyword-only parameter defaulting to \"ts_utc\" (additive, no add-alongside module) — assumption_delta_decision from the plan"
  - "Date-key path applies zero tz assertions (matches SPEC-01 §7 GeoSphere date contract); tz assertions remain scoped only to the ts_utc branch"
  - "Shared _month_bounds() helper factored out so both validators compute the same [month_start, month_end) window from one place"

patterns-established:
  - "Adding a new write-key grain to _io.write_month means adding a private _validate_<grain>_key() branch to the existing dispatcher, never a second writer module"

requirements-completed: [REQ-ING-01, ING-003, ING-004]

coverage:
  - id: D1
    description: "write_month accepts an additive key_column='ts_utc' keyword; existing ts_utc callers unchanged"
    requirement: "REQ-ING-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_default_key_column_still_rejects_missing_ts_utc"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_default_key_column_still_rejects_naive_ts_utc"
        status: pass
    human_judgment: false
  - id: D2
    description: "write_month(..., key_column='date') accepts a plain date-keyed frame and enforces calendar-month bounds with no tz assertion"
    requirement: "ING-003"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_date_key_happy_path"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_date_key_applies_no_timezone_assertion"
        status: pass
    human_judgment: false
  - id: D3
    description: "Missing key column raises ContractError; out-of-month rows raise ValueError — for both ts_utc and date key modes"
    requirement: "ING-004"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_date_key_rejects_missing_date_column"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_date_key_rejects_out_of_month_rows"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_rejects_missing_ts_utc_column"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_rejects_out_of_month_rows"
        status: pass
    human_judgment: false
  - id: D4
    description: "ING-004 provenance columns and ING-003 atomic os.replace write unchanged for both key modes; round-trip preserves fixed column order"
    requirement: "ING-004"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_round_trip_both_key_modes_preserve_provenance_order"
        status: pass
    human_judgment: false
  - id: D5
    description: "M1 ts_utc callers (entsoe orchestration, ingest gates, raw contracts) remain green with zero call-site changes to entsoe.py"
    verification:
      - kind: unit
        ref: "uv run pytest tests/unit/test_io.py tests/unit/test_entsoe_orchestration.py tests/unit/test_ingest_gates.py tests/test_raw_contracts.py -m 'not live' (93 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-22
status: complete
---

# Phase EPRA-03 Plan 01: write_month key_column dispatcher Summary

**write_month() gains an additive, keyword-only key_column parameter ("ts_utc" default) so GeoSphere's date-grain data reuses the same ING-003/004 atomic writer without a second writer module or a fabricated ts_utc column.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2
- **Files modified:** 2 (`src/epra/ingest/_io.py`, `tests/unit/test_io.py`)

## Accomplishments
- `write_month(frame, dataset, month, request_hash, settings, *, key_column="ts_utc")` — new keyword-only parameter, default behavior byte-for-byte identical to before
- New `_validate_date_key()` validator: enforces presence + calendar-month bounds for a plain `date` key, with zero timezone assertions (per SPEC-01 §7 GeoSphere contract)
- Existing tz-aware-UTC logic relocated unchanged into `_validate_ts_utc_key()` (renamed only, no behavior change)
- New shared `_month_bounds()` helper computing `[month_start, month_end)` once for both validators
- 10 new/updated tests in `tests/unit/test_io.py`: date-key happy path, missing-column ContractError, out-of-month ValueError, no-tz-assertion check, ts_utc/date round-trip invariant, and explicit default-path regression assertions
- Confirmed via RED/GREEN cycle: tests fail with `TypeError: write_month() got an unexpected keyword argument 'key_column'` against the pre-change module, then pass after the dispatcher lands
- Zero edits to `src/epra/ingest/entsoe.py` — all M1 ts_utc call sites unaffected

## Task Commits

Each task was committed per the TDD RED/GREEN cycle:

1. **Task 1 (RED): Add failing tests for key_column dispatcher** - `58c69ca` (test)
2. **Task 1 (GREEN): Parameterize write_month with key_column dispatcher** - `1d7f1f5` (feat)

_Task 2 (backward-compatibility regression) added no further code changes — its required regression assertions (`test_write_month_default_key_column_still_rejects_missing_ts_utc`, `test_write_month_default_key_column_still_rejects_naive_ts_utc`) were authored as part of Task 1's RED commit above; Task 2 consisted of running and confirming the four M1 suites stay green with zero edits to `entsoe.py` (verified, no diff produced — see Deviations)._

**Plan metadata:** (this commit)

## Files Created/Modified
- `src/epra/ingest/_io.py` — added `key_column` param, `_validate_date_key()`, `_month_bounds()`, renamed `_validate_ts_utc` to `_validate_ts_utc_key`
- `tests/unit/test_io.py` — added `_geosphere_daily_frame()` fixture helper and 10 new test cases for the key_column dispatcher and backward-compat regression

## Decisions Made
- Promoted `key_column` to a keyword-only parameter defaulting to `"ts_utc"` rather than adding a second writer function, per the plan's `assumption_delta_decision` and RESEARCH "Don't Hand-Roll" guidance
- Factored the calendar-month bounds computation into a single `_month_bounds()` helper shared by both validators to avoid duplicating that logic per key mode

## Deviations from Plan

None - plan executed exactly as written. Task 2 required no additional source/test edits beyond what Task 1's TDD RED phase already produced (the plan's Task 2 action item was itself "add one explicit regression assertion", which was folded into the single RED test commit rather than split into a separate later commit — the assertions exist and pass, and `entsoe.py` was confirmed untouched via `git diff --stat` against the pre-plan HEAD).

## TDD Gate Compliance

RED gate: `test(03-01): add failing tests for write_month key_column dispatcher` (`58c69ca`) — confirmed failing before implementation (`TypeError: write_month() got an unexpected keyword argument 'key_column'`, reproduced by reverting `_io.py` to HEAD and re-running).
GREEN gate: `feat(03-01): parameterize write_month with key_column dispatcher` (`1d7f1f5`) — all 21 tests in `test_io.py` pass after implementation.
REFACTOR gate: not needed — implementation required no cleanup pass beyond the initial GREEN commit.

## Issues Encountered
None.

## Verification Results

- `uv run pytest tests/unit/test_io.py -m "not live" -x --no-cov` — 21 passed
- `uv run pytest tests/unit/test_io.py tests/unit/test_entsoe_orchestration.py tests/unit/test_ingest_gates.py tests/test_raw_contracts.py -m "not live" --no-cov` — 93 passed (M1 unaffected, zero edits to `entsoe.py`)
- `uv run ruff check src/epra/ingest/_io.py tests/unit/test_io.py` — all checks passed
- `uv run mypy` (full project) — success, no issues in 30 source files
- `uv run pytest -m "not live" -q` (full suite) — 185 passed, coverage 96.06% (>= 80% gate)

Note: running `tests/unit/test_io.py` alone (without `--no-cov`) trips the project-wide `--cov-fail-under=80` gate on the single-file subset (expected — the same condition documented in `02-02-SUMMARY.md`; the full suite run above proves real coverage is 96%).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `write_month(..., key_column="date")` is ready for GeoSphere ingest (03-04) to call directly with its `geosphere_graz_daily` dataset and `date`-shaped frame
- No blockers for downstream plans in this wave

---
*Phase: EPRA-03-m2-auxiliary-data*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: src/epra/ingest/_io.py
- FOUND: tests/unit/test_io.py
- FOUND: .planning/phases/EPRA-03-m2-auxiliary-data/03-01-SUMMARY.md
- FOUND: 58c69ca (test commit)
- FOUND: 1d7f1f5 (feat commit)
- FOUND: 728e2de (docs/SUMMARY commit)
