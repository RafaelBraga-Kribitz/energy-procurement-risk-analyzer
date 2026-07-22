---
phase: EPRA-03-m2-auxiliary-data
plan: 02
subsystem: ingest
tags: [calendar, holidays, dst, timeutil, pandas, ing-110, ing-111]

# Dependency graph
requires:
  - phase: EPRA-03 plan 01
    provides: write_month key_column dispatcher (not used by this plan, but establishes the _io/_dataset_root reuse pattern this plan follows)
  - phase: EPRA-02 (M1 ENTSO-E)
    provides: epra.common.timeutil (VIENNA, is_peak_hour, to_local, local_hours_in_day, next_month) and epra.ingest.entsoe.latest_complete_month, both reused directly by this plan
provides:
  - epra.ingest.calendar.build_calendar(settings, end=None) — ING-110 hourly UTC calendar spine with Vienna-local attributes, Styrian holidays, and peak-hour flags
  - epra.ingest.calendar.main(argv) — CLI (python -m epra.ingest.calendar [--end YYYY-MM-DD])
  - data/raw/calendar/calendar.parquet — single-file calendar output (gitignored, generated artifact)
  - make calendar target
affects: [dbt dim_calendar (SPEC-02 §4), any future M2/M3 plan reading data/raw/calendar]

# Tech tracking
tech-stack:
  added: [holidays.countries.austria.Austria (holidays>=0.50, already pinned; first production use in this repo)]
  patterns: [reuse _io._dataset_root for REPO_ROOT-relative path resolution instead of reimplementing; mirror entsoe._parse_cli_date style locally rather than cross-import a private helper; module-scoped pytest fixture to build an ~79k-row frame once and reuse across assertion-only tests]

key-files:
  created:
    - tests/unit/test_calendar.py
  modified:
    - src/epra/ingest/calendar.py
    - Makefile
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "Import Austria from holidays.countries.austria (not bare `import holidays`) — mypy --strict's no_implicit_reexport rejects holidays.countries' implicit re-export; mirrors the existing EntsoeRawClient-from-entsoe.entsoe precedent."
  - "Use stdlib datetime.timedelta instead of pd.Timedelta(hours=...) for the end-of-day offset — the latter trips a pandas 2.3.3 'generic unit' DeprecationWarning on the bare-kwarg constructor path, unrelated to this module's logic."
  - "_default_end advances the month via a loop of timeutil.next_month() calls (18 iterations) rather than pd.DateOffset(months=18), staying consistent with the codebase's existing month-arithmetic helper instead of introducing a second month-stepping mechanism."
  - "_parse_cli_date is a local copy mirroring entsoe._parse_cli_date's style (plan said 'reusing the style', not importing the private cross-module symbol)."

patterns-established:
  - "New M2 modules building on data/raw/<dataset>/ persistence reuse _io._dataset_root(dataset, settings) for REPO_ROOT-relative path resolution, matching the WR-03 canonical-implementation convention already followed by entsoe.py and validate.py."

requirements-completed: [ING-110, ING-111]
# REQ-ING-01 is NOT marked complete here — it closes only after all 6 Phase-3
# plans + validation gates land at plan 03-06, per orchestrator instruction.

coverage:
  - id: D1
    description: "build_calendar() returns the ING-110 hourly UTC spine (2019-01-01 -> last UTC hour of end) with exact columns, correct DST 23/25-hour local days, Styrian holiday flags, and timeutil-sourced peak-hour flags"
    requirement: ING-110
    verification:
      - kind: unit
        ref: "tests/unit/test_calendar.py#test_build_calendar_spine_covers_2019_through_end"
        status: pass
      - kind: unit
        ref: "tests/unit/test_calendar.py#test_build_calendar_dst_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "ING-111 correctness: 2024 Styrian holiday count matches holidays.Austria(subdiv='6'); Jan1/May1/Dec25 always holidays; peak-hour definition correct on a known Monday, Sunday, and holiday weekday; SG-10 subdivision code '6' confirmed"
    requirement: ING-111
    verification:
      - kind: unit
        ref: "tests/unit/test_calendar.py#test_build_calendar_ing_111_holiday_count_and_fixed_holidays"
        status: pass
      - kind: unit
        ref: "tests/unit/test_calendar.py#test_build_calendar_ing_111_peak_hours"
        status: pass
      - kind: unit
        ref: "tests/unit/test_calendar.py#test_styria_subdivision_code_is_6"
        status: pass
    human_judgment: false
  - id: D3
    description: "CLI (python -m epra.ingest.calendar [--end YYYY-MM-DD]) persists a SINGLE parquet file at data/raw/calendar/calendar.parquet (not monthly-partitioned, not via _io.write_month); make calendar target wired"
    verification:
      - kind: unit
        ref: "tests/unit/test_calendar.py#test_calendar_main_writes_single_parquet_file"
        status: pass
      - kind: unit
        ref: "tests/unit/test_calendar.py#test_calendar_main_rejects_malformed_end_date"
        status: pass
      - kind: other
        ref: "uv run python -m epra.ingest.calendar --end 2027-12-31 && test -f data/raw/calendar/calendar.parquet"
        status: pass
    human_judgment: false
  - id: D4
    description: "cal.build_calendar / cal.main stub rows removed from test_stubs_fail_loudly.py; full suite (178+ tests) still green with real coverage >= 80%"
    verification:
      - kind: unit
        ref: "tests/unit/test_stubs_fail_loudly.py (17 remaining STUBS parametrizations)"
        status: pass
      - kind: other
        ref: "uv run pytest -m 'not live' -q (full suite)"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-07-23
status: complete
---

# Phase EPRA-03 Plan 02: Calendar hourly spine (ING-110/111) Summary

**Hourly UTC calendar spine (2019 -> forward-window end) with Vienna-local attributes, Styrian public holidays via the `holidays` package (subdiv='6'), and holiday-aware peak-hour flags sourced from `epra.common.timeutil` — persisted as a single `data/raw/calendar/calendar.parquet` file.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 (1 TDD, 1 auto)
- **Files modified:** 4 (1 created, 3 modified) + 1 phase-scoped deferred-items log

## Accomplishments

- `build_calendar(settings, end=None)` builds the ING-110 spine: one row per UTC hour from 2019-01-01 through the last UTC hour of `end`, with `ts_utc, date_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour, year_local, month_local` — exactly matching SPEC-01 §11.
- DST correctness verified via `timeutil.local_hours_in_day` (never hand-derived): 2024-03-31 has 23 distinct local hours, 2024-10-27 has 25.
- Styrian holidays from `holidays.countries.austria.Austria(subdiv="6", years=range(2019, end.year+1))` — 2024 holiday count matches the package exactly; Jan 1, May 1, Dec 25 always flagged.
- Peak-hour flags call `epra.common.timeutil.is_peak_hour` per row (never re-implemented) — verified holiday-aware (a weekday holiday is off-peak) on a known Monday/Sunday/holiday.
- `main(argv)` CLI (`python -m epra.ingest.calendar [--end YYYY-MM-DD]`) with a dynamic default end (`latest_complete_month(settings)` + 18 months, D-08/D-09) and a fixed `--end` override for deterministic runs; writes ONE parquet file via `_io._dataset_root`, not monthly-partitioned, not via `_io.write_month`.
- `make calendar` target wired; `cal.build_calendar`/`cal.main` stub rows removed from `test_stubs_fail_loudly.py`.
- Real CLI run produced the artifact: `data/raw/calendar/calendar.parquet`, 78,888 rows, 9 columns, 2019-01-01 00:00 UTC -> 2027-12-31 23:00 UTC.

## Task Commits

Each task was committed atomically (TDD RED/GREEN split for Task 1):

1. **Task 1 RED: failing test for build_calendar** - `661e99c` (test)
2. **Task 1 GREEN: implement build_calendar** - `83f17b9` (feat)
3. **Task 2: calendar CLI, parquet persistence, Makefile target, stub removal** - `4485c16` (feat)

**Plan metadata:** committed separately after this SUMMARY (docs commit).

_No REFACTOR commit — the GREEN implementation was already clean; no follow-up cleanup needed._

## Files Created/Modified

- `tests/unit/test_calendar.py` - DST, ING-111 holiday/peak, SG-10 subdiv, and CLI tests (new file, 9 tests)
- `src/epra/ingest/calendar.py` - `build_calendar`, `_default_end`, `_parse_cli_date`, `main` implemented (was M2 stub)
- `Makefile` - `calendar` target added (M2 section), `.PHONY` updated
- `tests/unit/test_stubs_fail_loudly.py` - removed the two M2 `cal.build_calendar`/`cal.main` STUBS rows and the now-unused `cal` import

## Decisions Made

- Imported `Austria` from `holidays.countries.austria` (not bare `import holidays`) to satisfy mypy `--strict`'s `no_implicit_reexport` — mirrors the project's existing `EntsoeRawClient`-from-`entsoe.entsoe` precedent (see STATE.md decisions).
- Used stdlib `datetime.timedelta` instead of `pd.Timedelta(hours=...)` for the end-of-day UTC offset, avoiding a pandas 2.3.3 "generic unit" `DeprecationWarning` unrelated to the calendar logic itself.
- `_default_end` steps the month forward via 18 calls to `timeutil.next_month()` rather than `pd.DateOffset(months=18)`, reusing the codebase's existing month-arithmetic helper instead of introducing a parallel mechanism.
- `_parse_cli_date` is a local copy mirroring `entsoe._parse_cli_date`'s validation style rather than importing the private cross-module symbol, per the plan's "reusing the ... style" phrasing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] mypy `--strict` rejected `holidays.countries` implicit re-export of `Austria`**
- **Found during:** Task 1 GREEN verification (`uv run mypy` was part of the plan's overall `<verification>` block)
- **Issue:** `from holidays.countries import Austria` failed mypy's `no_implicit_reexport` (strict mode) with "Module has no attribute 'Austria'", even though `holidays` ships a `py.typed` marker and the import works at runtime.
- **Fix:** Import from the defining submodule directly: `from holidays.countries.austria import Austria`.
- **Files modified:** `src/epra/ingest/calendar.py`
- **Verification:** `uv run mypy src/epra/ingest/calendar.py` → `Success: no issues found in 1 source file`; full-repo `uv run mypy` also clean (30 source files).
- **Committed in:** `83f17b9` (Task 1 GREEN commit)

**2. [Rule 1 - Bug] pandas 2.3.3 DeprecationWarning from `pd.Timedelta(hours=23)`**
- **Found during:** Task 1 GREEN verification — `uv run pytest ... -W error::DeprecationWarning` surfaced a "generic unit for NumPy timedelta is deprecated ... will raise an error in the future" warning from the bare-kwarg `pd.Timedelta(hours=...)` constructor path (confirmed to trigger standalone, independent of any Timestamp/date interaction — an upstream pandas quirk).
- **Fix:** Replaced `pd.Timedelta(hours=23)` (source) and `pd.Timedelta(hours=1)` (test assertion) with stdlib `datetime.timedelta(hours=...)`, which does not touch the deprecated code path.
- **Files modified:** `src/epra/ingest/calendar.py`, `tests/unit/test_calendar.py`
- **Verification:** `uv run pytest tests/unit/test_calendar.py -m "not live" --no-cov -W error::DeprecationWarning` → 5/5 passed, zero warnings-as-errors.
- **Committed in:** `83f17b9` (Task 1 GREEN commit)

**3. [Rule 1 - Bug] acceptance-criteria grep tripped by an explanatory comment**
- **Found during:** Task 1 acceptance-criteria verification — the source-assertion `grep -n "strategies\|StrategyCfg\|load_strategy_config" src/epra/ingest/calendar.py` (must return nothing) matched a docstring comment that mentioned `strategies.yaml` while explaining why it's NOT imported.
- **Fix:** Reworded the comment to convey the same rationale (M2 must not depend on M6 forward-simulation config) without using the literal banned substrings.
- **Files modified:** `src/epra/ingest/calendar.py`
- **Verification:** `grep -n "strategies\|StrategyCfg\|load_strategy_config" src/epra/ingest/calendar.py` now returns nothing (exit 1).
- **Committed in:** `83f17b9` (Task 1 GREEN commit)

---

**Total deviations:** 3 auto-fixed (1 blocking/mypy, 1 bug/deprecation-warning, 1 bug/acceptance-criteria-wording)
**Impact on plan:** All three were required to meet the plan's own `<verification>` block (mypy clean, and the exact acceptance-criteria greps) and to keep the module future-proof against an upstream pandas deprecation. No scope creep — no behavior, schema, or persistence-format changes beyond what the plan specified.

## Issues Encountered

- Running `uv run pytest tests/unit/test_calendar.py [...]` as a file subset (rather than the full suite) trips the project-wide `--cov-fail-under=80` gate even though every test in the subset passes — a known, previously-documented condition (see `02-02-SUMMARY.md` and `03-01-SUMMARY.md`). Resolved by verifying with `--no-cov` for the subset and separately running the FULL suite (`uv run pytest -m "not live" -q`) for the real gate check: 24 unit tests pass for `test_calendar.py` + `test_stubs_fail_loudly.py`; full suite is green with 95.83% coverage (>= 80% gate).
- `uv run ruff format --check src tests scripts` flags `tests/unit/test_io.py` as needing reformatting — pre-existing, last touched by plan 03-01 (commit `58c69ca`), not modified by this plan. Logged to `.planning/phases/EPRA-03-m2-auxiliary-data/deferred-items.md` per the scope-boundary rule (out of scope for 03-02) rather than fixed here.

## User Setup Required

None - no external service configuration required. `holidays>=0.50` was already a pinned dependency (RESEARCH §Package Legitimacy Audit); no new packages installed.

## Next Phase Readiness

- `data/raw/calendar/calendar.parquet` is present and ING-111 gate-clean — ROADMAP Phase 3 success criteria 1 & 2 for this plan are met.
- `build_calendar`/`main` are ready for downstream consumption by dbt's `dim_calendar` (SPEC-02 §4) once M3 begins.
- No blockers for plan 03-03.

---
*Phase: EPRA-03-m2-auxiliary-data*
*Completed: 2026-07-23*

## Self-Check: PASSED

- All created/modified files verified present on disk: `tests/unit/test_calendar.py`, `src/epra/ingest/calendar.py`, `Makefile`, `tests/unit/test_stubs_fail_loudly.py`, `data/raw/calendar/calendar.parquet`, `03-02-SUMMARY.md`.
- All task/summary commits verified in `git log`: `661e99c` (test), `83f17b9` (feat), `4485c16` (feat), `90ffeab` (docs: summary).
- TDD gate sequence verified: `test(03-02)` precedes `feat(03-02)` in git log — RED then GREEN present. No REFACTOR commit (none needed).
