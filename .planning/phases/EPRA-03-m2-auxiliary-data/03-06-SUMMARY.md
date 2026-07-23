---
phase: EPRA-03-m2-auxiliary-data
plan: 06
subsystem: ingest
tags: [validation, gates, geosphere, oespi, calendar, entsoe]

# Dependency graph
requires:
  - phase: EPRA-03-m2-auxiliary-data (03-02, 03-04, 03-05)
    provides: calendar spine (ING-110/111), GeoSphere ingest + ING-094 gate, ÖSPI loader + ING-103 gate
provides:
  - gate_ing_111 thin GateResult wrapper over the calendar assertions (holiday count, fixed holidays, Mon/Sun peak-hour correctness)
  - run_gates extended to load GeoSphere daily parquet, the ÖSPI CSV (guarded for absence), and the calendar spine, registering ING-094/103/111 alongside ING-080..085 in one aggregate report
  - live-data validation run: GeoSphere station 30 pulled 2019-01→2023-12 (60 monthly parquet files), make validate-ingest exits 0 with ALL GATES PASSED across all 9 registered gates, report committed at reports/ingestion/validation_2026-07-23.md
  - ADR-008 ÖSPI series pick confirmed by the user against the live AEA publication
affects: [phase-4-m3-dbt-warehouse, phase-6-m6-limitations-close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "run_gates I/O loaders stay in run_gates; gate_ing_* functions remain pure over already-loaded DataFrames (gate_ing_111 follows this)"
    - "Missing real human-transcribed data (ÖSPI) degrades a gate to a non-fatal informational PASS rather than crashing run_gates or CI (D-06)"

key-files:
  created: []
  modified:
    - src/epra/ingest/validate.py
    - tests/unit/test_ingest_gates.py
    - tests/conftest.py
    - reports/ingestion/validation_2026-07-23.md
    - LIMITATIONS.md
    - .planning/phases/EPRA-03-m2-auxiliary-data/deferred-items.md

key-decisions:
  - "gate_ing_111 is a thin wrapper reusing the 03-02 calendar assertions verbatim — no new validation logic, only report-surface uniformity"
  - "A missing data/manual/oespi_monthly.csv degrades run_gates' ING-103 result to a non-crashing informational PASS (D-06) instead of raising, so CI stays network-free and transcription-free while still rendering all 9 gates in the aggregate report"
  - "ADR-008 ÖSPI series pick (AEA continuously-published strompreisindex page) confirmed by the user against the live publication — no correction needed"
  - "Real ÖSPI double-entry reconciliation (ING-101) is deliberately deferred past this plan's close — entry1/entry2 CSVs exist locally but are unreconciled; documented as a design-sanctioned human-only deferral in LIMITATIONS.md §6 and deferred-items.md, not treated as a gate failure or phase blocker"

patterns-established:
  - "Aggregate validation reports (reports/ingestion/validation_<date>.md) list every registered gate exactly once (T-02-13) and are committed as human/local checkpoint artifacts, never CI-gated on live network or human transcription (D-06)"

requirements-completed: []

coverage:
  - id: D1
    description: "gate_ing_111 wrapper + wiring ING-094/103/111 into run_gates so one report covers all M1+M2 gates"
    requirement: "ING-094"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py (gate_ing_111 pass/fail pair + run_gates aggregate test)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Live GeoSphere pull (station 30, 2019-01→2023-12, 60 monthly parquet files) and make validate-ingest exit 0 (ALL GATES PASSED) on real data, report committed"
    requirement: "ING-111"
    verification:
      - kind: manual_procedural
        ref: "make validate-ingest — reports/ingestion/validation_2026-07-23.md, all 9 gates PASS"
        status: pass
    human_judgment: true
    rationale: "Live network pull and the resulting real-data validation run are a human/local checkpoint (D-06/D-07) — not reproducible from CI, requires operator confirmation of the live GeoSphere pull and ADR-008 series pick against the live AEA publication."
  - id: D3
    description: "ÖSPI double-entry reconciliation (ING-101) — real reconciled data/manual/oespi_monthly.csv"
    requirement: "ING-101"
    verification: []
    human_judgment: true
    rationale: "Deliberately deferred — double-entry transcription/reconciliation is a human-only operation (D-03) not performed in this close-out per explicit instruction; entry1/entry2 CSVs exist unreconciled, ING-103 soft-passes informationally. Documented in LIMITATIONS.md and deferred-items.md with exact resolution steps; REQ-ING-01 final closure left to phase verification."

# Metrics
duration: 15min
completed: 2026-07-23
status: complete
---

# Phase EPRA-03 Plan 06: M2 Ingestion Validation Assembly Summary

**run_gates now renders one aggregate report over all 9 M1+M2 gates (ING-080..085, 094, 103, 111); live GeoSphere pull + real-data validate-ingest run exits 0 (ALL GATES PASSED), with ÖSPI double-entry reconciliation explicitly deferred and documented.**

## Performance

- **Duration:** ~15 min close-out (continuation from resolved human checkpoint)
- **Completed:** 2026-07-23
- **Tasks:** 2 (Task 1 autonomous gate wiring; Task 2 human checkpoint — real data)
- **Files modified:** 6 (validate.py, test_ingest_gates.py, conftest.py, validation report, LIMITATIONS.md, deferred-items.md)

## Accomplishments

- `gate_ing_111(calendar_frame)` added to `src/epra/ingest/validate.py` as a thin `GateResult` wrapper over the 03-02 calendar assertions (2024 Styrian holiday count, fixed holidays, Mon/Sun peak-hour correctness); empty input fails per A-2.
- `run_gates` extended to load the GeoSphere daily parquet glob, the ÖSPI CSV (guarded for absence — degrades to informational PASS rather than raising, D-06), and the calendar spine, registering `ING-094`, `ING-103`, `ING-111` alongside `ING-080..085` — every gate listed exactly once (T-02-13).
- `tests/unit/test_ingest_gates.py` extended with a `gate_ing_111` pass/fail pair and a `run_gates` aggregate test asserting all M1+M2 gate ids appear exactly once.
- `tests/conftest.py`: `tmp_settings` fixture now also redirects `data_manual` so the aggregate `run_gates` tests never depend on the real repo's `data/manual` state.
- Human checkpoint resolved: ADR-008 ÖSPI series pick confirmed by the user against the live AEA publication; live GeoSphere pull completed (station 30, 2019-01-01→2023-12-31, 60 monthly parquet files under `data/raw/geosphere_graz_daily/`, gitignored); `make validate-ingest` exits 0 with **ALL GATES PASSED** across all 9 registered gates; report committed at `reports/ingestion/validation_2026-07-23.md`.
- One deferral recorded (design-sanctioned, not a gate failure): the real reconciled `data/manual/oespi_monthly.csv` does not exist yet — the two double-entry transcription files (`oespi_monthly_entry1.csv`, `oespi_monthly_entry2.csv`) exist locally but are unreconciled. `ING-103` currently soft-passes with an informational message per D-06. Documented in `LIMITATIONS.md` §6 and `.planning/phases/EPRA-03-m2-auxiliary-data/deferred-items.md` with exact resolution steps.

## Task Commits

Each task was committed atomically (this continuation only verified and closed out — no new production code commits were made):

1. **Task 1: gate_ing_111 wrapper + wire ING-094/103/111 into run_gates** - `4f36c2c` (feat)
2. **Task 2: Human checkpoint — real ÖSPI reconciliation status + live GeoSphere pull + validate-ingest on real data** - `9ded31e` (docs — validation report commit)

**Plan metadata:** (this commit) `docs(03-06): complete M2 assembly plan`

## Files Created/Modified

- `src/epra/ingest/validate.py` - `gate_ing_111` wrapper added; `run_gates` extended to load GeoSphere/ÖSPI/calendar data and register ING-094/103/111
- `tests/unit/test_ingest_gates.py` - `gate_ing_111` pass/fail pair + `run_gates` aggregate wiring test
- `tests/conftest.py` - `tmp_settings` fixture redirects `data_manual` for aggregate test isolation
- `reports/ingestion/validation_2026-07-23.md` - real-data validation report, ALL GATES PASSED (committed at `9ded31e`)
- `LIMITATIONS.md` - §6 updated with the ÖSPI double-entry reconciliation deferral and exact resolution steps
- `.planning/phases/EPRA-03-m2-auxiliary-data/deferred-items.md` - deferral entry added for this close-out

## Decisions Made

- `gate_ing_111` reuses the 03-02 calendar assertions verbatim as a thin wrapper — no new validation logic, keeping the report-surface uniform with ING-080..094/103.
- Missing real ÖSPI CSV degrades `run_gates`' ING-103 result to a non-crashing informational PASS (D-06) so CI remains network-free and transcription-free, while the aggregate report still lists all 9 gates exactly once.
- ADR-008's AEA continuously-published strompreisindex page pick was confirmed correct by the user against the live publication — no ADR correction needed.
- ÖSPI double-entry reconciliation (ING-101) is deliberately left unresolved at this close-out per explicit operator instruction (human-only operation, D-03) — recorded as a limitation, not silently dropped or fabricated.

## Deviations from Plan

None - plan executed exactly as written across both tasks (autonomous gate wiring + human checkpoint). This continuation agent performed no additional code changes; it verified the two prior commits, recorded the deferred ÖSPI reconciliation item in `LIMITATIONS.md` and `deferred-items.md`, and produced this close-out SUMMARY.

## Issues Encountered

None. The human checkpoint (Task 2) resolved cleanly: `make validate-ingest` exits 0 with ALL GATES PASSED across all 9 registered gates (ING-080..085, ING-094, ING-103, ING-111) on real data.

## User Setup Required

None - no external service configuration required beyond the already-resolved `ENTSOE_API_TOKEN` (Phase 2) and the live GeoSphere pull performed as part of this plan's human checkpoint.

## Next Phase Readiness

- M1+M2 ingestion validation is fully assembled: one `make validate-ingest` report covers all 9 gates, and the real-data run exits 0 (ALL GATES PASSED).
- **Open item carried forward:** the real reconciled `data/manual/oespi_monthly.csv` is still pending human double-entry reconciliation. `ING-103` currently soft-passes informationally rather than validating real ÖSPI data end-to-end. Resolve via `uv run python scripts/oespi_reconcile.py` (reconciles `data/manual/oespi_monthly_entry1.csv` + `oespi_monthly_entry2.csv` into `data/manual/oespi_monthly.csv`), then delete the two entry files, then re-run `make validate-ingest` to confirm a real-data ING-103 PASS. Full details in `LIMITATIONS.md` §6.
- **REQ-ING-01 closure is intentionally left to phase verification** (not marked complete by this close-out) — the phase-verification step should weigh the open ÖSPI-reconciliation deferral before deciding whether REQ-ING-01 can be checked off.
- Phase EPRA-03 (m2-auxiliary-data) has all 6 plans executed; ready for `/gsd-verify-work EPRA-03` and, pending REQ-ING-01 resolution, `/gsd-plan-phase 4` (M3 dbt warehouse).

---
*Phase: EPRA-03-m2-auxiliary-data*
*Completed: 2026-07-23*

## Self-Check: PASSED

- FOUND: .planning/phases/EPRA-03-m2-auxiliary-data/03-06-SUMMARY.md
- FOUND: reports/ingestion/validation_2026-07-23.md
- FOUND: LIMITATIONS.md
- FOUND commit: 4f36c2c (feat(03-06): wire ING-094/103/111 into run_gates for one M1+M2 report)
- FOUND commit: 9ded31e (docs(03-06): commit M2 validate-ingest report)
- Verified: all 9 gates (ING-080..085, ING-094, ING-103, ING-111) registered exactly once in run_gates (src/epra/ingest/validate.py:921-929)
- Verified: reports/ingestion/validation_2026-07-23.md shows "Overall: ALL GATES PASSED" with all 9 gate sections PASS
