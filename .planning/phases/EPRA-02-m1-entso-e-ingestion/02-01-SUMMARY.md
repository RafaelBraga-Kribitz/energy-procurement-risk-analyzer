---
phase: EPRA-02-m1-entso-e-ingestion
plan: 01
subsystem: infra
tags: [adr, pyarrow, parquet, entsoe-py, pytest, exceptions]

# Dependency graph
requires:
  - phase: EPRA-01 (M0 bootstrap)
    provides: src/epra/common (config, logging, timeutil, db), typed ingest stubs, pyproject.toml toolchain
provides:
  - ADR-003 (EntsoeRawClient transport + own Appendix-A parsers, adopts SG-01)
  - ADR-004 (pyarrow>=18,<26 as canonical pandas parquet engine, adopts pyarrow Wave 0 gap)
  - ADR-005 (latest_complete_month = min(AT, DE-LU) prices completeness, adopts SG-02)
  - pyarrow pinned + installed; pandas parquet engine functional
  - src/epra/ingest/exceptions.py (IngestError hierarchy)
  - tests/conftest.py (tmp_settings, entsoe_fixtures_dir fixtures) + tests/fixtures/entsoe/ placeholder
affects: [EPRA-02-02, EPRA-02-03, EPRA-02-04, EPRA-02-05, EPRA-02-06]

# Tech tracking
tech-stack:
  added: [pyarrow>=18,<26]
  patterns:
    - "Ingest exception hierarchy: IngestError base + IngestAuthError/IngestTransportError/ContractError/GateFailure/NoDataError, each carrying actionable context (source, status_code, gate_id, expected/actual)"
    - "tests/conftest.py tmp_settings fixture redirects Settings.paths (data_raw/data_cache/reports) to tmp_path, mirrors tests/unit/test_logging_and_db.py model_copy pattern"

key-files:
  created:
    - docs/ADR/ADR-003_entsoe-raw-client-sg01.md
    - docs/ADR/ADR-004_pyarrow-parquet-engine.md
    - docs/ADR/ADR-005_latest-complete-month-sg02.md
    - src/epra/ingest/exceptions.py
    - tests/conftest.py
    - tests/fixtures/entsoe/README.md
  modified:
    - pyproject.toml
    - uv.lock
    - docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md

key-decisions:
  - "SG-01 adopted via ADR-003: EntsoeRawClient is transport-only; EntsoePandasClient never used for persistence; own Appendix-A XML parsers preserve ING-009/050/060/063"
  - "pyarrow>=18,<26 adopted via ADR-004 as the canonical pandas parquet engine for _io and ING-070 contract tests"
  - "SG-02 adopted via ADR-005: latest_complete_month() = min(AT prices complete month, DE-LU prices complete month); load/gen completeness excluded from this definition"

patterns-established:
  - "ADR format: Context / Decision / Consequences / Spec deviations, cross-referencing 14_SPEC_GAPS.md rows as 'adopted (ADR-NNN)'"
  - "Ingest exceptions carry structured evidence in constructor args (not just message strings) so callers can branch on gate_id/status_code/dataset"

requirements-completed: [REQ-ING-01, ING-022, ING-042]

coverage:
  - id: D1
    description: "Three Wave 0 ADRs (SG-01 client choice, pyarrow parquet engine, SG-02 latest_complete_month zone rule) recorded and marked accepted, unblocking _fetch/_io/parser plans"
    requirement: "REQ-ING-01"
    verification:
      - kind: unit
        ref: "test -f docs/ADR/ADR-003_entsoe-raw-client-sg01.md && test -f docs/ADR/ADR-004_pyarrow-parquet-engine.md && test -f docs/ADR/ADR-005_latest-complete-month-sg02.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "pyarrow pinned in pyproject.toml and installed; pandas resolves the pyarrow parquet engine"
    requirement: "ING-022"
    verification:
      - kind: unit
        ref: "uv run python -c \"import pyarrow; import pandas as pd; pd.io.parquet.get_engine('pyarrow')\""
        status: pass
    human_judgment: false
  - id: D3
    description: "Ingest exception hierarchy (IngestError, IngestAuthError, IngestTransportError, ContractError, GateFailure, NoDataError) importable and instantiable"
    verification:
      - kind: unit
        ref: "uv run python -c \"from epra.ingest.exceptions import IngestError, IngestAuthError, IngestTransportError, ContractError, GateFailure, NoDataError\""
        status: pass
    human_judgment: false
  - id: D4
    description: "tests/conftest.py provides tmp_path-backed Settings (tmp_settings) and the entsoe_fixtures_dir fixture; tests/fixtures/entsoe/ exists with a placeholder README for future ING-070 fixture files"
    requirement: "ING-042"
    verification:
      - kind: unit
        ref: "ad-hoc pytest run against tests/unit/_sanity_check_conftest_fixtures.py (both fixtures asserted, then file removed — not part of final commit); ruff+mypy clean on tests/conftest.py"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-21
status: complete
---

# Phase EPRA-02 Plan 01: Wave 0 Architecture Decisions Summary

**Three accepted ADRs (EntsoeRawClient transport, pyarrow parquet engine, SG-02 latest-complete-month rule), pyarrow pinned and installed, and an ingest exception hierarchy + tmp_path-backed pytest conftest ready for the _io/_fetch/parser plans.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-21T14:30:00Z (approx)
- **Completed:** 2026-07-21T14:50:16Z
- **Tasks:** 3/3
- **Files modified:** 9 (3 ADRs created, 1 spec-gaps doc updated, pyproject.toml + uv.lock updated, exceptions.py + conftest.py + fixtures README created)

## Accomplishments

- Adopted SG-01 (ADR-003): `EntsoeRawClient` is the sanctioned transport, own Appendix-A parsers own the §7 output contracts, `EntsoePandasClient` is forbidden for persistence — unblocks `_fetch` (02-03) and parsers (02-04).
- Adopted the pyarrow Wave 0 gap (ADR-004): pinned `pyarrow>=18,<26`, reinstalled the venv (`uv pip install -e ".[dev]"`), verified `pandas.io.parquet.get_engine("pyarrow")` resolves.
- Adopted SG-02 (ADR-005): `latest_complete_month()` is defined as `min(AT prices complete month, DE-LU prices complete month)`, explicitly excluding load/gen completeness from the definition.
- Built `src/epra/ingest/exceptions.py`: `IngestError` base with `IngestAuthError`, `IngestTransportError`, `ContractError`, `GateFailure`, `NoDataError` — each constructor takes structured evidence (source, status_code, gate_id, dataset, expected/actual) so messages are always actionable.
- Built `tests/conftest.py`: `tmp_settings` fixture redirects `Settings.paths.data_raw/data_cache/reports` to `tmp_path`; `entsoe_fixtures_dir` fixture plus a real `tests/fixtures/entsoe/README.md` placeholder created at conftest-collection time.
- Cross-referenced SG-01 and SG-02 rows in `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` as `adopted (ADR-003)` / `adopted (ADR-005)`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write ADRs for SG-01, pyarrow, and SG-02** - `bd52b19` (docs)
2. **Task 2: Pin pyarrow and refresh install** - `64f6fb7` (chore)
3. **Task 3: Ingest exceptions and pytest conftest** - `3ebc127` (feat)

**Plan metadata:** (this commit, immediately following)

## Files Created/Modified

- `docs/ADR/ADR-003_entsoe-raw-client-sg01.md` - Adopts SG-01: EntsoeRawClient transport + own Appendix-A parsers
- `docs/ADR/ADR-004_pyarrow-parquet-engine.md` - Adopts pyarrow as the canonical pandas parquet engine
- `docs/ADR/ADR-005_latest-complete-month-sg02.md` - Adopts SG-02: min(AT, DE-LU) prices completeness zone rule
- `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` - SG-01/SG-02 rows marked adopted with ADR cross-references
- `pyproject.toml` - Added `pyarrow>=18,<26` to `[project.dependencies]`
- `uv.lock` - Refreshed lockfile after pyarrow add
- `src/epra/ingest/exceptions.py` - `IngestError` hierarchy (auth, transport, contract, gate, no-data)
- `tests/conftest.py` - `tmp_settings` and `entsoe_fixtures_dir` pytest fixtures
- `tests/fixtures/entsoe/README.md` - Placeholder describing expected ING-070 fixture files

## Decisions Made

- SG-01/SG-02 promoted from `proposed` to `adopted` per this plan's ADRs — binding for all subsequent M1 plans (02-02 through 02-06+).
- pyarrow version range `>=18,<26` chosen to match the project's existing pin style (floor near current stable major, open-but-bounded upper bound); installed version resolved to `25.0.0`.
- Exception classes carry structured attributes (not just formatted strings) so future gate/fetch code can branch on `.gate_id`, `.status_code`, `.dataset` etc. without string parsing.
- `entsoe_fixtures_dir` directory + README creation happens at conftest **import/collection time** (module-level call), not lazily inside the fixture body, so the directory exists on disk for any pytest invocation that touches `tests/`, not only ones that request the fixture.

## Deviations from Plan

**1. [Rule 2 - Missing Critical] Cross-referenced SG-01/SG-02 in 14_SPEC_GAPS.md**
- **Found during:** Task 1
- **Issue:** Plan's `<action>` text explicitly said "Cross-reference SG-01/SG-02 rows in 14_SPEC_GAPS.md as adopted" but this file was not listed in the plan frontmatter's `files_modified`.
- **Fix:** Updated the SG-01 and SG-02 status cells from `proposed` to `adopted (ADR-003)` / `adopted (ADR-005)` in `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md`.
- **Files modified:** `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md`
- **Verification:** Diff reviewed; only the two status cells changed.
- **Committed in:** `bd52b19` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing-critical — explicit action text vs. incomplete frontmatter file list)
**Impact on plan:** Necessary to satisfy the plan's own written action item and keep the spec-gaps register accurate. No scope creep — no other files touched beyond what Task 1's action text specified.

## Issues Encountered

None. `uv pip install -e ".[dev]"` succeeded on the first attempt (network to PyPI was available as expected); no package-legitimacy checkpoint was needed since pyarrow was already vetted `[ASSUMED] OK` in `02-RESEARCH.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 gate is clear: 02-03 (`_fetch.py`, EntsoeRawClient) and 02-04 (Appendix-A parsers) can proceed against ADR-003 without re-litigating client choice.
- `_io.py` (parquet writer, likely 02-02) can rely on the pandas/pyarrow engine being installed and working.
- `latest_complete_month()` implementation (likely 02-05) has its zone rule frozen by ADR-005.
- `tests/conftest.py` fixtures (`tmp_settings`, `entsoe_fixtures_dir`) are ready for `_io`/`_fetch`/parser/gate unit tests in subsequent plans; `tests/fixtures/entsoe/` is an empty-but-documented directory awaiting committed XML/parquet samples (ING-070, T1.03a) — no fixture files exist yet, so `tests/test_raw_contracts.py` (02-0x) will need to add them before contract tests can run.
- No blockers for 02-02 onward.

## Self-Check: PASSED

All created files verified present on disk (3 ADRs, exceptions.py, conftest.py, fixtures README, pyproject.toml). All 3 task commit hashes (`bd52b19`, `64f6fb7`, `3ebc127`) verified present in `git log`.

---
*Phase: EPRA-02-m1-entso-e-ingestion*
*Completed: 2026-07-21*
