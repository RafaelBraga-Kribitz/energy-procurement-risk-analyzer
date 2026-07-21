---
phase: EPRA-02-m1-entso-e-ingestion
plan: 05
subsystem: ingest
tags: [entsoe, pandas, pyarrow, argparse, cli, makefile]

# Dependency graph
requires:
  - phase: EPRA-02-02
    provides: write_month raw parquet persistence (_io.py)
  - phase: EPRA-02-03
    provides: fetch_entsoe cache/retry/politeness transport (_fetch.py)
  - phase: EPRA-02-04
    provides: parse_publication_xml, parse_gl_xml, hourly_mean, iter_chunks (entsoe.py parsers)
provides:
  - ingest_dataset(settings, dataset_key, start, end, transport) orchestration function
  - backfill(settings, start, end) and ingest_incremental(settings) covering all four §7 datasets
  - latest_complete_month(settings) per ADR-005 (min of AT/DE-LU complete price months)
  - epra.ingest.entsoe CLI (--backfill/--incremental/--start/--end/--no-cache)
  - make backfill / make ingest wired to the real CLI
affects: [EPRA-02-06, EPRA-02-07, M3-dbt-warehouse]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Orchestration functions live in the same module as their parsers (entsoe.py), not a separate file"
    - "request_hash computed by reusing _fetch's private _cache_request_url with a placeholder token value (request_hash() strips securityToken regardless of its value, so no duplicate token read is needed)"
    - "Dataset-key -> (document_type, zone_key) mapping via a frozen _DatasetSpec dataclass + dict, avoiding per-dataset if/elif chains"

key-files:
  created:
    - tests/unit/test_entsoe_orchestration.py
  modified:
    - src/epra/ingest/entsoe.py
    - Makefile
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "ingest_dataset splits parsed frames into calendar-month writes using the UTC calendar month of ts_utc (matching write_month's own UTC-based month validation), not a Vienna-local month, to avoid a second, unnecessary timezone conversion at a boundary that is already UTC-partitioned on disk"
  - "latest_complete_month's ADR-005 'complete calendar day' check also uses UTC calendar days (ts_utc.dt.date) rather than Vienna-local days, for the same reason: the raw file boundary this function reads from is itself a UTC month partition"
  - "Conservative backfill-end fallback (no ingested data yet): first day of the previous calendar month, used only when latest_complete_month() raises NoDataError and no --end override was given"
  - "main()'s --incremental mode rejects --start/--end overrides with a ValueError (exit 1) rather than silently ignoring them, since ING-041 is defined as a fixed 45-day lookback"

patterns-established:
  - "CLI exit contract: 0 success, 1 for ValueError/IngestError (user or data-state errors), SystemExit(2) from argparse itself for malformed flags/dates/missing mode (T-02-10)"

requirements-completed: [REQ-ING-01, ING-001, ING-002, ING-010, ING-040, ING-041, ING-042]

coverage:
  - id: D1
    description: "ingest_dataset fetches+parses+writes one §7 dataset over a date window, iterating <=90-day chunks through the injectable transport seam"
    requirement: "ING-001"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_dataset_writes_one_parquet_per_month"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_dataset_maps_delu_zone"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_dataset_load_dataset_key"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_dataset_generation_dataset_key"
        status: pass
    human_judgment: false
  - id: D2
    description: "ingest_dataset skips (logs, does not raise) a NoDataError window and never leaves a partial file on a ContractError"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_dataset_no_data_window_is_skipped_not_raised"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_dataset_contract_error_leaves_no_partial_file"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_dataset_logs_a03_fill_count"
        status: pass
    human_judgment: false
  - id: D3
    description: "backfill iterates all four dataset keys over [start, end]; ingest_incremental re-ingests a fixed 45-day lookback from today"
    requirement: "ING-040"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_backfill_iterates_all_four_dataset_keys_in_order"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_backfill_writes_real_files_for_all_datasets"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_ingest_incremental_uses_45_day_lookback_from_today"
        status: pass
    human_judgment: false
  - id: D4
    description: "latest_complete_month returns min(AT, DE-LU) complete price month per ADR-005, and raises a clear error when no complete month exists yet"
    requirement: "ING-042"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_latest_complete_month_returns_min_of_at_and_delu"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_latest_complete_month_excludes_incomplete_month"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_latest_complete_month_raises_when_no_data_ingested"
        status: pass
    human_judgment: false
  - id: D5
    description: "CLI main() dispatches --backfill/--incremental with strict date parsing, --no-cache passthrough, and a 0/1 exit contract; make backfill/make ingest invoke it"
    requirement: "ING-002"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_main_backfill_invokes_backfill_with_explicit_window"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_main_incremental_invokes_ingest_incremental"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_orchestration.py#test_main_backfill_rejects_inverted_window"
        status: pass
      - kind: other
        ref: "grep -q epra.ingest.entsoe Makefile"
        status: pass
    human_judgment: false
  - id: D6
    description: "M1 rows removed from the fail-loudly stub test now that entsoe.backfill/ingest_incremental/latest_complete_month/main are implemented"
    verification:
      - kind: unit
        ref: "tests/unit/test_stubs_fail_loudly.py (validate.* M1 rows retained; entsoe.* M1 rows removed)"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-21
status: complete
---

# Phase EPRA-02 Plan 05: ENTSO-E Ingest Orchestration Summary

**End-to-end ENTSO-E backfill/incremental/CLI wiring on top of the prior waves' fetch/parse/write primitives, with latest_complete_month implementing ADR-005's min(AT, DE-LU) rule.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3 completed
- **Files modified:** 4 (`src/epra/ingest/entsoe.py`, `Makefile`, `tests/unit/test_entsoe_orchestration.py` [new], `tests/unit/test_stubs_fail_loudly.py`)

## Accomplishments
- `ingest_dataset` orchestration: chunked fetch -> parse -> per-month `write_month`, dispatching across the four §7 dataset keys (`entsoe_prices_at`, `entsoe_prices_delu`, `entsoe_load_at`, `entsoe_gen_at`) via a `_DatasetSpec` mapping
- `backfill`/`ingest_incremental` wired to iterate all four datasets, both forwarding the injectable `transport`/`use_cache` seam
- `latest_complete_month` implements ADR-005 (adopts SG-02): scans ingested raw parquet, returns `min(latest complete AT month, latest complete DE-LU month)`, raising `NoDataError` when nothing has been ingested yet
- CLI `main()`: `--backfill`/`--incremental` (mutually exclusive), `--start`/`--end` overrides, `--no-cache`; strict ISO-date parsing and inverted-range rejection (T-02-10); logs to `reports/ingestion/ingest_<date>.log` (T-02-11)
- `Makefile`'s `backfill`/`ingest` targets now invoke the real CLI instead of erroring stubs
- Removed the four now-implemented `entsoe.*` rows from `test_stubs_fail_loudly.py` (kept `validate.*` M1 rows per plan 02-06)

## Task Commits

Each task was committed atomically (Task 1 followed the TDD RED/GREEN cycle per its `tdd="true"` flag):

1. **Task 1: Dataset orchestration helpers** (RED) - `af28cd3` (test)
2. **Task 1: Dataset orchestration helpers** (GREEN) - `eadfeb9` (feat)
3. **Task 2: backfill, ingest_incremental, latest_complete_month** - `e6055fd` (feat)
4. **Task 3: CLI, Makefile, stub cleanup** - `5079b72` (feat)

**Plan metadata:** (this commit, following SUMMARY.md write)

## Files Created/Modified
- `src/epra/ingest/entsoe.py` - Adds `ingest_dataset`, `backfill`, `ingest_incremental`, `latest_complete_month`, `main`, and their private helpers (`_DatasetSpec`, `_write_by_month`, `_complete_price_months`, `_month_from_path`, `_dataset_root`, `_parse_cli_date`, `_conservative_backfill_end`, `_resolve_backfill_end`)
- `tests/unit/test_entsoe_orchestration.py` - New: 23 tests across the three tasks, all driven through the fixture-XML `TransportFn` seam (no network)
- `Makefile` - `backfill`/`ingest` targets now call `uv run python -m epra.ingest.entsoe --backfill`/`--incremental`
- `tests/unit/test_stubs_fail_loudly.py` - Removed the four `entsoe.*` M1 rows; `entsoe` import removed (no longer referenced)

## Decisions Made
- Split parsed frames into monthly writes using the **UTC** calendar month of `ts_utc` (matching `write_month`'s own UTC-based validation), not Vienna-local month, avoiding an unnecessary second timezone conversion at a boundary that's already UTC-partitioned on disk. Same reasoning applied to ADR-005's "complete calendar day" check in `latest_complete_month`.
- `request_hash` is computed by calling `_fetch`'s private `_cache_request_url(query, "x")` with a placeholder token value — `_io.request_hash()` strips the `securityToken` query param regardless of its value, so this produces the identical hash `fetch_entsoe` computes internally from the real token, without a second token read.
- Conservative backfill-end fallback (used only when `latest_complete_month()` raises `NoDataError` and no `--end` override is given): first day of the previous calendar month.
- `main()`'s `--incremental` mode rejects `--start`/`--end` overrides with a `ValueError` (exit 1) rather than silently ignoring them, since ING-041 defines a fixed 45-day lookback.

## Deviations from Plan

None - plan executed as written. The only additions beyond the plan's literal text were implementation details necessary to make the described behavior testable/usable: `transport`/`use_cache` keyword parameters threaded through `backfill`/`ingest_incremental` (needed for the fixture-XML test seam per the environment notes) and a handful of small private helper functions.

## Issues Encountered

- `ruff format` reformatted `entsoe.py`/`test_entsoe_orchestration.py` for line wrapping after each Task's edits — applied and re-verified (tests still pass, mypy clean) before each commit.
- `make lint` fails at the `ruff format --check` step on `tests/unit/test_aggregate_hourly.py`, a file last touched in plan `02-04`'s commit `b05024c` and untouched by this plan. Confirmed pre-existing (no diff to that file in this session) and logged to `deferred-items.md` per the executor's scope boundary — not fixed here.
- `tests/unit/test_config.py::test_entsoe_token_fails_fast_when_unset` still fails in this environment for the `02-02`-logged reason (real `.env` token repopulated by `load_dotenv` after `monkeypatch.delenv`); reconfirmed unaffected by this plan's changes.

## User Setup Required

None - no new external service configuration required. `ENTSOE_API_TOKEN` (required for the live backfill in plan 02-07) was already documented and present per STATE.md.

## Next Phase Readiness
- `epra.ingest.entsoe` is fully wired end-to-end: `make backfill`/`make ingest` invoke real CLI paths, gated only by network/token availability (deferred to plan 02-07's live run).
- `latest_complete_month()` is ready for `validate.py` (plan 02-06) and downstream dbt freshness checks / SPEC-05 forward window to call.
- Plan 02-06 (`validate.py` gates) can proceed; its `M1` stub rows in `test_stubs_fail_loudly.py` were intentionally left in place.
- Plan 02-07 (live backfill) can proceed once a real `ENTSOE_API_TOKEN` run is performed outside this no-network environment.

---
*Phase: EPRA-02-m1-entso-e-ingestion*
*Completed: 2026-07-21*

## Self-Check: PASSED

All created/modified files and all four task commits (`af28cd3`, `eadfeb9`, `e6055fd`, `5079b72`) verified present on disk / in `git log`.
