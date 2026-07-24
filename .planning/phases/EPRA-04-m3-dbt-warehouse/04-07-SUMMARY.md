---
phase: EPRA-04-m3-dbt-warehouse
plan: 07
subsystem: database
tags: [duckdb, dbt, pandas, python, make]

# Dependency graph
requires:
  - phase: EPRA-04-m3-dbt-warehouse plan 04
    provides: dbt/models/marts/fct_price_hourly.sql, fct_price_monthly.sql (the DM-062/DM-064 sanity numbers this report queries)
  - phase: EPRA-04-m3-dbt-warehouse plan 05
    provides: dbt/models/marts/fct_consumer_load_hourly.sql, fct_procurement_cost_monthly.sql (the two stand-in marts this report flags)
  - phase: EPRA-04-m3-dbt-warehouse plan 06
    provides: dbt/tests/reconcile_price_monthly_2022_08.sql, fct_price_hourly_row_count_per_year.sql (the DM-062/064 dbt tests this report's queries mirror as read-only sanity numbers, not re-enforced pass/fail gates)
provides:
  - src/epra/warehouse/{__init__.py,report.py} — D-02 build-report writer: ModelBuildResult/BuildReport (GateResult/ValidationReport reuse), build_report(settings) reading the warehouse read-only, _write_report() writing reports/warehouse/dbt_build_<date>.md, main() CLI
  - tests/unit/test_warehouse_report.py — 8 network-free unit tests on constructed inputs
  - Makefile transform: un-stubbed to `cd dbt && dbt build`; new warehouse: target (transform + report)
affects: [EPRA-04-m3-dbt-warehouse plan 08 (phase close-out commits the runtime reports/warehouse/dbt_build_<date>.md this plan's code generates, and wires make warehouse/transform into the CI dbt-check job)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-02 build-report writer is informational sanity-checking layered on top of an already-green dbt build -- it reads (never recomputes/re-gates) the DM-050/062/064 numbers the dbt tests (04-06) already enforce at build time, reusing validate.py's GateResult/ValidationReport render_markdown shape verbatim (renamed ModelBuildResult/BuildReport here)"
    - "make warehouse composes make transform (dbt build) + python -m epra.warehouse.report as two independently-runnable Makefile targets, mirroring the ingest -> validate-ingest two-step convention from M1/M2"

key-files:
  created:
    - src/epra/warehouse/__init__.py
    - src/epra/warehouse/report.py
    - tests/unit/test_warehouse_report.py
  modified:
    - Makefile
    - .gitignore

key-decisions:
  - "The report's DM-062/DM-050 rows are purely informational (raw per-year row counts, min/max/count-of-months) -- they deliberately do NOT re-implement the +/-24 tolerance / calendar-complete-year / no-gap boundary logic already owned by the 04-06 dbt tests, keeping this module strictly read-only per the plan's own prohibition (no recomputing mart values in Python)."
  - "The 2022-08 reconciliation row (DM-064) and the stand-in-mart flag row (D-05/D-06) DO carry a passed/PASS-FAIL semantic (delta <= 0.01 tolerance; always-True informational flag respectively) since those are the two sanity numbers the plan explicitly asks the report to surface as first-class content, not gate re-derivations."
  - "main()'s failure mode is a read failure (duckdb.Error -- e.g. dbt build hasn't populated the marts schema yet), not a data-anomaly failure -- mirroring validate.main()'s exit-code shape but with a different failure trigger, since DM-06x anomaly detection already belongs to the dbt build itself."

requirements-completed: [REQ-DWH-01, DM-060, D-02]

coverage:
  - id: D1
    description: "src/epra/warehouse/report.py's ModelBuildResult/BuildReport dataclasses render markdown (PASS/FAIL + optional evidence fence) exactly mirroring validate.py's GateResult/ValidationReport shape, network-free and unit-tested on constructed inputs"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_warehouse_report.py::test_model_build_result_render_markdown_pass_no_evidence, ::test_model_build_result_render_markdown_fail_with_evidence, ::test_model_build_result_render_markdown_empty_evidence_omits_fence, ::test_build_report_render_markdown_aggregates_all_results, ::test_build_report_all_passed_property -- uv run pytest tests/unit/test_warehouse_report.py -m \"not live\" --no-cov: 8 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_report(settings) opens epra.common.db.connect(read_only=True), queries per-year fct_price_hourly row counts (DM-062), monthly-mart month coverage (DM-050) across the 3 monthly marts, and the 2022-08 fct_price_monthly vs mean-of-hourly reconciliation delta (DM-064); _write_report() writes reports/warehouse/dbt_build_<date>.md under settings.paths.reports; verified end-to-end against the real local warehouse via make warehouse"
    requirement: "DM-060"
    verification:
      - kind: other
        ref: "make warehouse on real local data: dbt build 63 PASS / 1 pre-existing WARN (predup_count_prices) / 0 ERROR, then writes reports/warehouse/dbt_build_2026-07-24.md; report content confirms 10 years of fct_price_hourly counts, 3 monthly marts' month coverage, and the 2022-08 delta=0.0000 (monthly_base_eur_mwh=482.7263 == hourly_mean_eur_mwh=482.7263)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The report flags fct_consumer_load_hourly and fct_procurement_cost_monthly as 'stand-in (M4/M6 pending)' (D-05/D-06)"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/unit/test_warehouse_report.py::test_stand_in_marts_flagged_in_render; grep 'stand-in (M4/M6 pending)' src/epra/warehouse/report.py confirms both mart names present"
        status: pass
    human_judgment: false
  - id: D4
    description: "make transform runs cd dbt && dbt build (un-stubbed from the loud-fail placeholder); make warehouse builds then writes the D-02 report; all:/refresh: wiring intact; the M4-M7 stubs unchanged"
    requirement: "D-02"
    verification:
      - kind: other
        ref: "grep 'all: transform profile analyze simulate ssot export report' and 'refresh: ingest validate-ingest all' in Makefile confirm wiring intact; make warehouse run above confirms both transform and warehouse targets green on real data"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-24
status: complete
---

# Phase EPRA-04 Plan 07: D-02 Build-Report Writer + Makefile Operator Interface Summary

**`src/epra/warehouse/report.py` reads the built warehouse read-only and renders `reports/warehouse/dbt_build_<date>.md` (per-year row counts, month coverage, 2022-08 reconciliation delta, stand-in-mart flags) reusing `validate.py`'s `GateResult`/`ValidationReport` shape; `make transform` un-stubbed to `dbt build`, `make warehouse` builds then reports — both verified green on the real local warehouse**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-07-24T09:47:32Z
- **Tasks:** 2/2
- **Files modified:** 5 (3 created: `src/epra/warehouse/{__init__.py,report.py}`, `tests/unit/test_warehouse_report.py`; 2 modified: `Makefile`, `.gitignore`)

## Accomplishments
- `src/epra/warehouse/report.py` defines `ModelBuildResult`/`BuildReport` — a verbatim structural reuse of `validate.py`'s `GateResult`/`ValidationReport` (`render_markdown` with PASS/FAIL header + optional `evidence.to_string(index=False)` fence)
- `build_report(settings)` opens `epra.common.db.connect(settings, read_only=True)` and queries the built `marts` schema for: per-year `fct_price_hourly` row counts (DM-062), month coverage across the 3 monthly marts (DM-050), and the 2022-08 `fct_price_monthly.price_base_eur_mwh` vs mean-of-`fct_price_hourly.price_at_eur_mwh` reconciliation delta (DM-064) — plus a static row flagging `fct_consumer_load_hourly`/`fct_procurement_cost_monthly` as `stand-in (M4/M6 pending)` (D-05/D-06)
- `_write_report()` writes `reports/warehouse/dbt_build_<date>.md` under `settings.paths.reports` (copy-adapted from `validate._write_report`); `main()` mirrors `validate.main()`'s CLI/logging/exit-code shape, returning 1 only on a `duckdb.Error` read failure (e.g. `dbt build` not yet run)
- `tests/unit/test_warehouse_report.py`: 8 network-free unit tests on constructed `ModelBuildResult`/`BuildReport` inputs — PASS/FAIL rendering with and without evidence, report aggregation, the 2022-08 delta row, the stand-in-mart flag text, and the `_write_report` write path (via a `tmp_path`-redirected `Settings.paths.reports`)
- `Makefile`: `transform:` un-stubbed to `cd dbt && $(UV) run dbt build`; new `warehouse:` target runs `transform` then `python -m epra.warehouse.report`; `all:`/`refresh:` wiring and the still-stubbed M4-M7 targets left untouched
- Verified end-to-end on this repository's real local warehouse: `make warehouse` → `dbt build` 63 PASS / 1 pre-existing WARN (`predup_count_prices`, unrelated) / 0 ERROR, then wrote `reports/warehouse/dbt_build_2026-07-24.md` reporting 10 years of `fct_price_hourly` counts (2019-2028, including the calendar-horizon's 1-row 2028 boundary artifact), 3 monthly marts' min/max/month-count, and the 2022-08 delta = `0.0000` (`482.7263` both sides)
- `ruff check`/`ruff format --check`/`mypy` all clean on this plan's own files; project-wide `mypy` (32 source files) also clean

## Task Commits

Each task was committed atomically:

1. **Task 1: warehouse.report — build-report writer (GateResult/ValidationReport reuse)** - `a9a34d7` (feat)
2. **Task 2: Makefile transform un-stub + warehouse target** - `a350a96` (feat)

## Files Created/Modified
- `src/epra/warehouse/__init__.py` - new package docstring
- `src/epra/warehouse/report.py` - `ModelBuildResult`/`BuildReport`, `build_report()`, `_write_report()`, `main()`
- `tests/unit/test_warehouse_report.py` - 8 network-free unit tests (render + write path)
- `Makefile` - `transform:` un-stubbed to `dbt build`; new `warehouse:` target
- `.gitignore` - `reports/warehouse/*.log` carve-out (Rule 2, mirrors `reports/ingestion/*.log`)

## Decisions Made
- The DM-062 (per-year row counts) and DM-050 (month coverage) report rows are deliberately presentation-only — raw counts/min/max, no re-implementation of the 04-06 dbt tests' `+/-24`/calendar-complete-year/no-gap boundary logic — keeping `report.py` strictly a read-only consumer of an already-green `dbt build`, per the plan's own "must NOT recompute mart values in Python" prohibition.
- The 2022-08 reconciliation row (DM-064) and the stand-in-mart flag row (D-05/D-06) do carry a `passed` PASS/FAIL semantic (0.01-tolerance delta check; always-`True` informational flag) since the plan explicitly asks the report to surface these two numbers as first-class content, not as gate re-derivations.
- `main()`'s only failure path is a `duckdb.Error` read failure (e.g. the `marts` schema not yet populated) — DM-06x data-anomaly detection stays owned by the dbt build's own tests, not duplicated here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `reports/warehouse/*.log` to `.gitignore`**
- **Found during:** Task 2 (`make warehouse` verification)
- **Issue:** `main()`'s `common_logging.setup(logfile=...)` writes an operational `dbt_build_<date>.log` file into `reports/warehouse/` on every run — the existing `.gitignore` only carved out `reports/ingestion/*.log`, so this new log file would sit untracked with no ignore rule (the task-commit protocol's "never leave generated files untracked" step).
- **Fix:** Added `reports/warehouse/*.log` to `.gitignore`, mirroring the existing ingestion-log carve-out; the `reports/warehouse/dbt_build_<date>.md` report itself is intentionally left untracked in this plan (committed at 04-08 per this plan's own `artifacts_produced`).
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` after `make warehouse` shows only `reports/warehouse/` as an untracked directory (the `.log` file is now ignored; the `.md` report is deliberately deferred to 04-08).
- **Committed in:** `a350a96` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical -- `.gitignore` carve-out)
**Impact on plan:** Purely a housekeeping addition to keep the working tree clean after running the new `make warehouse` target; no change to `report.py`'s behavior or the plan's deliverables.

## Issues Encountered
- Running `uv run pytest tests/unit/test_warehouse_report.py -m "not live" -x` in isolation (the plan's own literal verify command) exits 1 due to this repo's project-wide `--cov-fail-under=80` pytest config applying to the narrow single-file subset (10% coverage of the full `epra` package when only this one new test file runs) — this is the same pre-existing, project-wide behavior already documented in 04-06's SUMMARY for any single narrow test file, not something introduced by or fixable within this plan's files. The unambiguous test outcome (`uv run pytest tests/unit/test_warehouse_report.py -m "not live" --no-cov`) is **8 passed, 0 failed**.
- `make lint`'s `ruff format --check src tests scripts` reports two pre-existing 04-05 files (`scripts/bootstrap_fixture_warehouse.py`, `tests/unit/test_bootstrap_fixture_warehouse.py`) would be reformatted — out of scope for this plan (not in `files_modified`); logged to `deferred-items.md`. `uv run ruff format --check src/epra/warehouse tests/unit/test_warehouse_report.py` (this plan's own files) is clean.

## User Setup Required

None — the build report reads the already-built local warehouse (from 04-01..04-06); no external services or credentials needed.

## Next Phase Readiness

The D-02 build-report writer and the `make transform`/`make warehouse` operator interface are both live and verified green against this repository's real local warehouse. `reports/warehouse/dbt_build_2026-07-24.md` sits untracked in the working tree, ready for 04-08's phase close-out to commit it (per this plan's own `artifacts_produced` deferral) alongside wiring `make warehouse`/`transform` into the CI `dbt-check` job and the fixture-bootstrap generator from 04-05. No blockers.

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-07-24*

## Self-Check: PASSED

All 5 created/modified files found on disk (`src/epra/warehouse/__init__.py`, `src/epra/warehouse/report.py`, `tests/unit/test_warehouse_report.py`, `Makefile`, `.gitignore`); both commit hashes (`a9a34d7`, `a350a96`) found in git log.
