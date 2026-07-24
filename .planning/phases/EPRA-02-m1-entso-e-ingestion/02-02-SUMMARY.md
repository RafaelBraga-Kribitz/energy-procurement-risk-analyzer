---
phase: EPRA-02-m1-entso-e-ingestion
plan: 02

subsystem: ingest
tags: [pandas, pyarrow, parquet, atomic-write, sha256]

# Dependency graph
requires:
  - phase: EPRA-02-m1-entso-e-ingestion (plan 01)
    provides: src/epra/ingest/exceptions.py (IngestError hierarchy incl. ContractError), tests/conftest.py tmp_settings fixture, pyarrow pin (ADR-004)
provides:
  - src/epra/ingest/_io.py — request_hash(), raw_month_path(), write_month(): the single write boundary for all data/raw/ parquet files
  - Contract enforcement at persistence layer: ts_utc tz-aware UTC required, out-of-month rows rejected, ING-004 provenance columns appended in fixed order
affects: [EPRA-02 plans 03-07 (entsoe fetch/parse/orchestration), test_raw_contracts.py, validate.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single writer module (_io.py) shared by every raw dataset — no per-source write logic"
    - "Atomic write: <path>.tmp then os.replace(tmp, path) (ING-003)"
    - "Testable wall-clock seam (_now_utc()) for freezing ingested_at_utc in idempotency tests"
    - "dataset name allowlist regex (^[a-z][a-z0-9_]*$) as a path-traversal mitigation instead of a hardcoded dataset enum"

key-files:
  created:
    - src/epra/ingest/_io.py
    - tests/unit/test_io.py
    - .planning/phases/EPRA-02-m1-entso-e-ingestion/deferred-items.md
  modified: []

key-decisions:
  - "write_month's `source` provenance column is derived from `dataset`'s prefix before the first underscore (entsoe_prices_at -> entsoe, geosphere_graz_daily -> geosphere) rather than a separate function argument — 03_MODULES.md's write_month signature has no source parameter, and deriving it from dataset avoids a redundant argument that could drift out of sync with the dataset name."
  - "Missing ts_utc column raises ContractError (schema violation); naive/non-UTC ts_utc or out-of-month rows raise ValueError (value violation) — matches 03_MODULES.md's explicit 'Failure' wording for the latter two cases while using the existing exception hierarchy for the schema case."
  - "Column order is deterministic: the frame's own columns (whatever order the caller passed) followed by ingested_at_utc, source, request_hash appended in that fixed order — proven by a dedicated column-order test using a non-alphabetical input frame."

patterns-established:
  - "Pattern: any future raw dataset writer (geosphere, calendar) calls _io.write_month() directly — no new write path needed, only a new `dataset` string + SPEC-01 §7 contract-test row."

requirements-completed: [REQ-ING-01, ING-003, ING-004, ING-005, ING-070]

coverage:
  - id: D1
    description: "request_hash(url) strips the securitytoken query param (case-insensitive) before hashing; stable 64-hex sha256 digest; empty url raises ValueError"
    requirement: "ING-004"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_request_hash_strips_securitytoken_case_insensitive"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_request_hash_is_stable_64_hex_digest"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_request_hash_empty_url_raises"
        status: pass
    human_judgment: false
  - id: D2
    description: "raw_month_path(dataset, month, settings) resolves to data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet per SPEC-01 §7, and rejects unsafe dataset names (path traversal, T-02-03)"
    requirement: "ING-003"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_raw_month_path_matches_spec01_section7_layout"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_raw_month_path_rejects_path_traversal_dataset"
        status: pass
    human_judgment: false
  - id: D3
    description: "write_month() atomically persists a monthly frame (.tmp then os.replace), appends ingested_at_utc/source/request_hash in fixed column order, and rejects naive/non-UTC ts_utc, missing ts_utc, and out-of-month rows"
    requirement: "ING-003, ING-004, ING-005, ING-070"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_atomic_write_with_contract_columns"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_rejects_naive_ts_utc"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_rejects_out_of_month_rows"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_rejects_missing_ts_utc_column"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_replaces_via_tmp_file_and_os_replace"
        status: pass
    human_judgment: false
  - id: D4
    description: "write_month() re-run with identical input frame and frozen clock produces a byte-identical parquet file (ING-003 idempotency); column order is fixed regardless of input column ordering (ING-070)"
    requirement: "ING-003, ING-070"
    verification:
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_idempotent_byte_stable"
        status: pass
      - kind: unit
        ref: "tests/unit/test_io.py#test_write_month_fixed_column_order_for_determinism"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-21
status: complete
---

# Phase EPRA-02 Plan 02: Raw Parquet Writer (`_io`) Summary

**`_io.py` implements the single, contract-enforcing raw-parquet write boundary shared by every ENTSO-E dataset — sha256 request-hashing with token stripping, SPEC-01 §7 path layout, and atomic (`.tmp` + `os.replace`) monthly writes that reject naive/non-UTC or out-of-month `ts_utc` rows.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-21T14:52:00Z (approx.)
- **Completed:** 2026-07-21T15:02:24Z
- **Tasks:** 3 completed
- **Files modified:** 3 (2 created + 1 deferred-items log)

## Accomplishments
- `request_hash(url)` — sha256 hex digest of a URL with the `securityToken` query parameter stripped case-insensitively, so cache keys and the ING-004 `request_hash` column never depend on the secret's value.
- `raw_month_path(dataset, month, settings)` — resolves the exact SPEC-01 §7 layout (`data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet`) and rejects dataset strings that aren't safe filesystem identifiers (mitigates T-02-03 path traversal).
- `write_month(frame, dataset, month, request_hash, settings)` — atomic temp-file-then-`os.replace` write; validates `ts_utc` is present and tz-aware UTC and that every row falls within the target calendar month; appends `ingested_at_utc`/`source`/`request_hash` in a fixed trailing column order.
- Idempotency proven: re-running `write_month` with the same frame and a frozen clock produces byte-identical parquet output (ING-003).

## Task Commits

Each task was committed atomically (per-task TDD RED/GREEN cycle):

1. **Task 1: request_hash and raw_month_path helpers**
   - `d8af367` (test) — failing tests for request_hash + raw_month_path
   - `7eb0cab` (feat) — implementation, tests green
2. **Task 2: write_month atomic parquet persistence**
   - `c8e774d` (test) — failing tests for write_month
   - `8c243d9` (feat) — implementation, tests green
3. **Task 3: Idempotency and dtype stability test**
   - `4543183` (test) — idempotency + column-order determinism tests, green against existing implementation
   - `5b8acd3` (style) — ruff format fix on test_io.py (deviation, see below)

_Note: Tasks 1 and 2 use the per-task TDD RED/GREEN flow (`tdd="true"`); Task 3 is a plain `auto` task adding tests against the already-implemented writer._

**Plan metadata:** (this commit, see below)

## Files Created/Modified
- `src/epra/ingest/_io.py` — `request_hash`, `raw_month_path`, `_now_utc`, `_validate_ts_utc`, `write_month`
- `tests/unit/test_io.py` — 13 unit tests covering all three functions plus atomicity, contract rejection, idempotency, and column-order determinism
- `.planning/phases/EPRA-02-m1-entso-e-ingestion/deferred-items.md` — logs one pre-existing, out-of-scope test failure discovered during verification

## Decisions Made
- `source` provenance column derived from `dataset`'s prefix before the first underscore (matches the `write_month` signature prescribed in `03_MODULES.md`, which has no separate `source` argument).
- Missing `ts_utc` column → `ContractError` (schema violation); naive/non-UTC or out-of-month `ts_utc` values → `ValueError` (value violation) — this split follows the exception hierarchy's stated purpose (`ContractError` = shape/schema mismatch) while matching `03_MODULES.md`'s explicit "Failure" wording for the value cases.
- Column order determinism implemented as: frame's own columns (as given) + `ingested_at_utc`, `source`, `request_hash` appended in that fixed order — verified with a dedicated test using a non-default input column order.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff format violation in test_io.py**
- **Found during:** Task 3 final verification (`make lint` equivalent: `ruff format --check`)
- **Issue:** One test line exceeded ruff's preferred wrapped-string style (still under the 100-char `line-length` limit checked by `ruff check`, but `ruff format --check` — part of `make lint` — flagged it for reformatting)
- **Fix:** Ran `ruff format tests/unit/test_io.py`
- **Files modified:** `tests/unit/test_io.py`
- **Verification:** `ruff format --check src/epra/ingest/_io.py tests/unit/test_io.py` passes; `pytest tests/unit/test_io.py` still 13/13 green
- **Committed in:** `5b8acd3`

**2. [Rule 3 - Blocking, out-of-scope] Logged pre-existing unrelated test failure**
- **Found during:** Task 1 verification (running `uv run pytest -q` to sanity-check the global coverage gate)
- **Issue:** `tests/unit/test_config.py::test_entsoe_token_fails_fast_when_unset` fails in this environment because a real `ENTSOE_API_TOKEN` in `.env` gets reloaded by `load_dotenv()` after the test's `monkeypatch.delenv()`. This file was last touched in the M0 bootstrap commit (`c043933`), well before this plan or plan 02-01 — not caused by any `_io.py`/`test_io.py` change.
- **Fix:** Not fixed (out of scope — `test_config.py`/`config.py` are not in this plan's `files_modified`). Logged to `deferred-items.md` for a future plan to address.
- **Files modified:** `.planning/phases/EPRA-02-m1-entso-e-ingestion/deferred-items.md`
- **Committed in:** `7eb0cab`

---

**Total deviations:** 2 (1 style auto-fix, 1 out-of-scope discovery logged and deferred)
**Impact on plan:** No scope creep; both actions are within Rule 3 (blocking lint fix) and the scope-boundary logging protocol (pre-existing unrelated failure, not touched).

## Issues Encountered
- Running `pytest tests/unit/test_io.py -k "..."` (a filtered subset, as literally specified in Task 1/2/3's `<verify>` blocks) always fails the global `--cov-fail-under=80` gate from `pyproject.toml`'s `addopts`, because coverage is measured across the entire `src/epra` tree regardless of which tests ran. This is a pre-existing condition of the repo's pytest config (confirmed: the full `pytest -q` suite passes coverage at ~91% because `test_stubs_fail_loudly.py` exercises every stub module's `NotImplementedError` raise). Not a real signal about `_io.py`'s test coverage — verified with `--no-cov` for the task-scoped commands and confirmed the full-suite run (which is what CI runs) passes coverage. No fix needed; documented here for the next executor's awareness.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `_io.write_month` is ready to be called by `entsoe.py`'s orchestration (`_fetch` → parse → per-month split → `_io.write_month`), which lands in plans 03-07 of this phase.
- `raw_month_path` gives `tests/test_raw_contracts.py` (ING-070, a later plan) a stable way to locate fixture parquet files once they're committed under `tests/fixtures/entsoe/`.
- No blockers. The pre-existing `test_config.py` token-test failure (see Deviations) should be picked up by whichever plan next touches `config.py`/`test_config.py`, or addressed as a standalone fix before the M1 gate gets ticked off in `AGENTS.md`.

---
*Phase: EPRA-02-m1-entso-e-ingestion*
*Completed: 2026-07-21*

## Self-Check: PASSED

- FOUND: src/epra/ingest/_io.py
- FOUND: tests/unit/test_io.py
- FOUND: .planning/phases/EPRA-02-m1-entso-e-ingestion/deferred-items.md
- FOUND commits: d8af367, 7eb0cab, c8e774d, 8c243d9, 4543183, 5b8acd3
