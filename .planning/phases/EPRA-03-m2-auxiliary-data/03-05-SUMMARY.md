---
phase: EPRA-03-m2-auxiliary-data
plan: 05
subsystem: ingest
tags: [oespi, pandas, validation-gates, adr, spec-01-10]

# Dependency graph
requires:
  - phase: EPRA-03-m2-auxiliary-data (03-04)
    provides: gate_ing_094 pure-gate pattern (GateResult/ValidationReport framework) mirrored here
provides:
  - epra.ingest.oespi.load_oespi(settings, *, csv_path=None) — ING-100/102/104 loader
  - epra.ingest.oespi.main(argv) — CLI (python -m epra.ingest.oespi)
  - epra.ingest.validate.gate_ing_103 — pure ÖSPI series gate
  - tests/fixtures/oespi/synthetic_oespi_monthly.csv — committed clean 2019-2023 series
  - docs/ADR/ADR-008_oespi-series-methodology.md — pinned source, pending T2.05 confirmation
affects: [EPRA-03-06 (real double-entry ÖSPI human checkpoint), M6 strategies (SPEC-05 calibration anchors consume oespi_base/oespi_peak)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "gate_ing_103 mirrors gate_ing_094's multi-check evidence-frame style (one GateResult aggregating N sub-checks)"
    - "load_oespi's csv_path seam mirrors geosphere's transport-injection pattern for test isolation"

key-files:
  created:
    - src/epra/ingest/oespi.py (was a NotImplementedError stub; now load_oespi + main implemented)
    - tests/unit/test_oespi.py
    - tests/fixtures/oespi/synthetic_oespi_monthly.csv
    - docs/ADR/ADR-008_oespi-series-methodology.md
  modified:
    - src/epra/ingest/validate.py (+gate_ing_103)
    - tests/unit/test_ingest_gates.py (+7 ING-103 tests)
    - tests/unit/test_stubs_fail_loudly.py (removed oespi.* M2 rows)
    - Makefile (+oespi target)
    - LIMITATIONS.md (provisional-pick + ING-104 fallback note)

key-decisions:
  - "ADR-008 pins the AEA continuously-published strompreisindex page (Base+Peak since Sept 2018) as the sole 2019->latest transcription source, explicitly flagged pending human confirmation at T2.05 (D-01/D-04) -- a strong candidate, not a locked fact"
  - "load_oespi's peak_available signal lives in frame.attrs, not a separate return value or column -- travels with the DataFrame through gate_ing_103 without changing either function's core signature"
  - "gate_ing_103's crisis-visibility and MoM checks operate on oespi_base only (the column ING-104 guarantees is always present), not oespi_peak, so the gate behaves identically in base-only fallback mode"
  - "_EXPECTED_COLUMNS is duplicated in oespi.py rather than imported from scripts/oespi_reconcile.py, since scripts/ is a standalone operator tool outside the installed epra package (pyproject packages = [\"src/epra\"])"
  - "main() wiring (load_oespi + gate_ing_103 + CLI) deferred from Task 1 to Task 3 per the plan's task split -- avoids a premature cross-task import of validate.gate_ing_103 before it existed"

patterns-established:
  - "Pattern 3 extension: gate_ing_103 is the third pure gate (after gate_ing_08x/094) extending the shared GateResult/ValidationReport framework with a 4-sub-check evidence DataFrame"

requirements-completed: [ING-100, ING-102, ING-103, ING-104]

coverage:
  - id: D1
    description: "load_oespi enforces the ING-100 exact-column schema, raising ContractError on drift (never silent)"
    requirement: "ING-100"
    verification:
      - kind: unit
        ref: "tests/unit/test_oespi.py#test_load_oespi_schema_drift_raises"
        status: pass
    human_judgment: false
  - id: D2
    description: "load_oespi asserts source_url is constant across the whole series (D-01), raising on a mid-series methodology splice"
    requirement: "ING-102"
    verification:
      - kind: unit
        ref: "tests/unit/test_oespi.py#test_load_oespi_source_url_splice_raises"
        status: pass
    human_judgment: false
  - id: D3
    description: "load_oespi never coerces a malformed/non-numeric/blank value to NaN -- always raises ContractError naming the month"
    requirement: "ING-100"
    verification:
      - kind: unit
        ref: "tests/unit/test_oespi.py#test_load_oespi_malformed_value_raises"
        status: pass
      - kind: unit
        ref: "tests/unit/test_oespi.py#test_load_oespi_never_mutates_a_bad_row_to_nan"
        status: pass
      - kind: unit
        ref: "tests/unit/test_oespi.py#test_load_oespi_partial_peak_blank_raises"
        status: pass
    human_judgment: false
  - id: D4
    description: "load_oespi sets peak_available=False and returns base-only without failing when the whole Peak column is blank (ING-104)"
    requirement: "ING-104"
    verification:
      - kind: unit
        ref: "tests/unit/test_oespi.py#test_load_oespi_base_only_fallback"
        status: pass
    human_judgment: false
  - id: D5
    description: "gate_ing_103 catches every ING-103 fail case: month gap, negative value, 2022 peak <3x 2019 mean, >60% MoM jump -- each derived from the committed synthetic CSV"
    requirement: "ING-103"
    verification:
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_103_passes_clean_series"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_103_fails_on_month_gap"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_103_fails_on_negative_value"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_103_fails_when_2022_peak_below_3x_2019_mean"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_103_fails_on_mom_jump_exceeding_60_percent"
        status: pass
      - kind: unit
        ref: "tests/unit/test_ingest_gates.py#test_gate_ing_103_fails_on_empty_input"
        status: pass
    human_judgment: false
  - id: D6
    description: "ADR-008 pins ONE AEA series/source as the sole 2019->latest transcription source, explicitly flagged pending human confirmation at T2.05"
    requirement: "ING-102"
    verification: []
    human_judgment: true
    rationale: "Whether the pinned source page is still the operationally correct choice at actual transcription time is a human confirmation step (T2.05, D-01/D-04) by design -- no automated test can assert that a future human read the right page."
  - id: D7
    description: "oespi CLI (python -m epra.ingest.oespi / make oespi) wires load_oespi + gate_ing_103, prints the gate report, and exits non-zero on load error or gate failure"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "uv run python -m epra.ingest.oespi (against the absent real CSV) -> logs ContractError-adjacent FileNotFoundError, exits 1"
        status: pass
    human_judgment: true
    rationale: "main() is a thin argparse+wiring CLI exercised manually (matches the existing geosphere.py/calendar.py convention of no direct unit test for main()); confirmed by a manual run against the intentionally-absent real CSV, not an automated test."

# Metrics
duration: 18min
completed: 2026-07-23
status: complete
---

# Phase EPRA-03 Plan 05: ÖSPI Loader, Series Gates, and Methodology ADR Summary

**`load_oespi` (ING-100/102/104) and pure `gate_ing_103` (continuity/positivity/2022-crisis-3x/MoM-60%) ship green against a committed synthetic 2019-2023 CSV, with ADR-008 pinning the AEA source pending T2.05 human confirmation.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-23T09:24:10Z
- **Completed:** 2026-07-23T09:41:57Z
- **Tasks:** 3 (2 TDD, 1 auto)
- **Files modified:** 9

## Accomplishments
- `load_oespi(settings, *, csv_path=None)` enforces the ING-100 exact-column schema, the ING-102 single-`source_url` invariant (never splices two methodologies), and the ING-104 base-only fallback (`frame.attrs["peak_available"]`) — never coerces a malformed value to NaN, always raises `ContractError` naming the offending month.
- `gate_ing_103` (pure, `epra.ingest.validate`) aggregates four independent sub-checks — continuity, positivity, 2022-crisis-visibility (max base ≥ 3× 2019 mean base), and month-over-month stability (±60%) — into one `GateResult`, mirroring `gate_ing_094`'s multi-check evidence-frame style. Empty input returns `passed=False` (A-2).
- `tests/fixtures/oespi/synthetic_oespi_monthly.csv`: a committed, clean, gap-free 2019–2023 Base+Peak series (60 months) that `gate_ing_103` PASSES outright; every fail case (month gap, negative value, sub-3x 2022 peak, >60% MoM jump) is derived from mutating a copy of this same fixture in-test, so the fail cases stay anchored to the one committed CSV rather than drifting across ad hoc fixtures.
- ADR-008 pins the AEA continuously-published *strompreisindex* page as the sole 2019→latest transcription source (Base+Peak published since Sept 2018), explicitly flagged as pending human confirmation at T2.05 (D-01/D-04) — a strong research-backed candidate, not a locked fact.
- `oespi.main()` wires `load_oespi` + `gate_ing_103` into a CLI (`python -m epra.ingest.oespi` / `make oespi`), printing the gate's markdown report and returning non-zero on load error or gate failure.
- `LIMITATIONS.md` §2 documents the provisional series pick and the ING-104 base-only fallback path; `test_stubs_fail_loudly.py`'s now-implemented `oespi.load_oespi`/`oespi.main` M2 rows are removed.

## Task Commits

Each task was committed atomically (RED/GREEN pairs for the two TDD tasks):

1. **Task 1: load_oespi loader + synthetic CSV** — `8b746f6` (test, RED) → `a5304db` (feat, GREEN)
2. **Task 2: pure gate_ing_103 series gates** — `c218bf6` (test, RED) → `4aa2332` (feat, GREEN)
3. **Task 3: ADR-008, oespi main/CLI, Makefile, LIMITATIONS, stub removal** — `52db5a3` (docs)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified
- `src/epra/ingest/oespi.py` — `load_oespi` (ING-100/102/104) + `main` (CLI, ING-103 wiring)
- `tests/unit/test_oespi.py` — 7 tests: happy path, schema drift, base-only fallback, partial-peak-blank, source_url splice, malformed value, never-silently-NaN
- `tests/fixtures/oespi/synthetic_oespi_monthly.csv` — committed clean 2019-2023 Base+Peak series (60 rows)
- `src/epra/ingest/validate.py` — `gate_ing_103` (+2 module constants: crisis multiplier, MoM band) + updated module docstring
- `tests/unit/test_ingest_gates.py` — 7 tests: passing case, empty input, month gap, negative value, sub-3x crisis, >60% MoM jump, input-mutation-avoided
- `docs/ADR/ADR-008_oespi-series-methodology.md` — new ADR (next-free number)
- `Makefile` — new `oespi` target + `.PHONY` entry
- `LIMITATIONS.md` — §2 provisional-pick + ING-104 fallback note
- `tests/unit/test_stubs_fail_loudly.py` — removed the two now-implemented `oespi.*` M2 rows and the now-unused `oespi` import

## Decisions Made
- ADR-008 pins the AEA continuously-published *strompreisindex* page as the sole transcription source, explicitly pending T2.05 human confirmation (D-01/D-04) rather than treating research as a locked fact.
- `peak_available` travels as `frame.attrs`, not a second return value or sentinel column — keeps `load_oespi`'s signature stable and lets `gate_ing_103` consume the same frame directly.
- `gate_ing_103`'s crisis-visibility and MoM checks use `oespi_base` only (the column ING-104 guarantees is always present), so the gate's behavior is identical whether or not Peak is available.
- `_EXPECTED_COLUMNS` is duplicated (not imported) from `scripts/oespi_reconcile.py`, since `scripts/` sits outside the installed `epra` package boundary (`pyproject.toml` `packages = ["src/epra"]`) — importing across that boundary would be fragile sys.path manipulation for a one-line tuple.
- `main()`'s full wiring (calling `gate_ing_103`) was deferred from Task 1 to Task 3 exactly as the plan specifies, avoiding a premature import of `validate.gate_ing_103` before Task 2 had written it — Task 1's `oespi.py` kept `main()` as the original `NotImplementedError` stub so its GREEN commit stayed self-contained.

## Deviations from Plan

None — plan executed exactly as written. The synthetic CSV fixture design (one committed clean series, with every ING-103 fail case derived from in-test mutations of that same series) resolves an apparent tension in the plan text between "the committed synthetic_oespi_monthly.csv exercises every ING-103 fail case" (must_haves) and "reuse the clean core... add targeted failing fixtures/rows" (Task 2 action) — interpreted as intended, matching the existing `gate_ing_094`/`_geosphere_year` helper-mutation test pattern already established in this codebase.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `load_oespi`/`gate_ing_103` ship green against the synthetic CSV; ready for 03-06, which delivers the real human-transcribed, double-entry-reconciled `data/manual/oespi_monthly.csv` (D-05/D-06 human checkpoint) and wires `gate_ing_103` results into a real validation report.
- No blockers. The real ÖSPI CSV's absence is expected and correct at this point in the phase — not a regression, not deferred debt beyond its designed checkpoint.
- `run_gates()` (the M1 aggregate `make validate-ingest` entry point) intentionally does NOT call `gate_ing_103` yet — that wiring belongs to 03-06 once the real CSV can satisfy it without breaking `make validate-ingest` for users who haven't transcribed yet.

---
*Phase: EPRA-03-m2-auxiliary-data*
*Completed: 2026-07-23*

## Self-Check: PASSED

All key files found on disk; all 5 task commit hashes (8b746f6, a5304db, c218bf6, 4aa2332, 52db5a3) found in `git log`.
