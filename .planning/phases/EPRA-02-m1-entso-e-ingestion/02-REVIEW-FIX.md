---
phase: EPRA-02-m1-entso-e-ingestion
fixed_at: 2026-07-22T03:37:11Z
review_path: .planning/phases/EPRA-02-m1-entso-e-ingestion/02-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase EPRA-02: Code Review Fix Report — M1 ENTSO-E Ingestion

**Fixed at:** 2026-07-22T03:37:11Z
**Source review:** .planning/phases/EPRA-02-m1-entso-e-ingestion/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (2 Critical, 3 Warning; Info findings IN-01/IN-02 out of scope per `fix_scope=critical_warning`)
- Fixed: 5
- Skipped: 0

**Verification:** `make lint` (ruff check, ruff format --check, mypy) and `make test`
(pytest, offline, `-m "not live"`) both GREEN after every fix. Final coverage
95.97% (gate: 80%).

## Fixed Issues

### CR-01: `iter_chunks` groups 3 raw calendar months without bounding the window to ING-030's 90-day maximum

**Files modified:** `src/epra/ingest/entsoe.py`, `tests/unit/test_entsoe_orchestration.py`
**Commit:** `06e440c`
**Applied fix:** Rewrote `iter_chunks` to group month-starts by actual elapsed
days (greedily extending a chunk only while `(prospective_end - chunk_start).days <= 90`)
instead of a fixed count of 3 calendar months. This exactly matches the
reviewer's suggested algorithm. Verified the new chunking still covers the
full requested window contiguously (no gaps/overlaps — each new chunk starts
exactly where the previous one ended).

Added 4 direct unit tests to `test_entsoe_orchestration.py` (previously
`iter_chunks` had zero direct coverage):
- `test_iter_chunks_never_exceeds_90_days_across_2019_2025` — sweeps the
  full real backfill range and asserts every yielded window is `<= 90` days.
- `test_iter_chunks_covers_full_window_with_no_gaps_or_overlaps` — asserts
  chunk boundaries are contiguous across the same sweep.
- `test_iter_chunks_apr_may_jun_91_day_span_is_split_not_rejected` — the
  explicit 91-day boundary case from the finding (Apr+May+Jun 2019).
- `test_iter_chunks_second_backfill_chunk_from_real_start_date_is_valid` —
  regresses the exact "second chunk of `make backfill` from 2019-01-01
  crashes" scenario described in the review.

### CR-02: Error-detail fallback can leak the real `securityToken` via `str(exc)` when the HTTP error response has no body

**Files modified:** `src/epra/ingest/_fetch.py`, `tests/unit/test_fetch.py`
**Commit:** `4bb53f3`
**Applied fix:** `_error_detail`'s empty-body fallback branch no longer
returns `str(exc)[:500]` (which, for a `requests.HTTPError` raised via
`raise_for_status()`, embeds the real request URL and thus the real token).
It now returns a fixed, token-free `f"{type(exc).__name__}: no response body
available"` description. Additionally, all three raise sites that build
`IngestAuthError`/`IngestTransportError` from a caught transport exception
(`_invoke_transport_once`'s 401/403 and 400 branches, and `fetch_entsoe`'s
retry-exhausted handler) now use `raise ... from None` instead of `from exc`,
severing the exception chain so a future traceback dump (`logger.exception`,
a bare script, pytest failure output) can't reprint the token-bearing
original exception via `__cause__`.

Added 2 regression tests to `test_fetch.py`:
- `test_fetch_entsoe_401_empty_body_never_leaks_token_via_str_exc_fallback` —
  exercises the fast 401 path with an empty response body, asserts the fake
  token is absent from the raised message and `excinfo.value.__cause__ is None`.
- `test_fetch_entsoe_5xx_empty_body_exhausted_retries_never_leaks_token` —
  same regression via the retry-exhausted fallback path (503, not 400/401/403).

### WR-01: `latest_complete_month`'s "complete" check only requires >=1 row per UTC day, not full-hour coverage

**File modified:** `src/epra/ingest/entsoe.py`
**Commit:** `5031698`
**Applied fix:** Chose the documentation-only branch of the reviewer's two
suggested fixes rather than tightening the semantics. `docs/ADR/ADR-005_latest-complete-month-sg02.md`
(accepted status) explicitly defines "complete" for this function as
day-presence-only ("every calendar day in that local month has at least one
price row"), so silently changing `_complete_price_months` to require
full-hour coverage would contradict an already-accepted ADR (A-1 spec
supremacy) rather than fix a bug. Instead, clarified both
`_complete_price_months` and `latest_complete_month`'s docstrings to state
explicitly that this is a weaker, day-presence-only heuristic than ING-080's
hour-coverage gate, and that callers needing hour-level completeness must
also run `validate.run_gates()`.

### WR-02: Cache and parquet-writer temp files are not process-unique — concurrent runs can race on the same `.tmp` path

**Files modified:** `src/epra/ingest/_fetch.py`, `src/epra/ingest/_io.py`, `tests/unit/test_fetch.py`, `tests/unit/test_io.py`
**Commit:** `2f97761`
**Applied fix:** Both atomic-write sites (`_io.write_month`'s parquet temp
file and `_fetch.fetch_entsoe`'s cache temp file) now suffix the temp
filename with `{os.getpid()}.{uuid4().hex[:8]}` before `.tmp`, exactly as
suggested, so two processes writing the same target file concurrently never
share a temp path. Existing tests that assert `src.endswith(".tmp")` and
`dst == str(path)` remain valid since the new names still end in `.tmp`.

Added 2 regression tests demonstrating per-call uniqueness:
- `test_write_month_tmp_path_is_per_call_unique` (`test_io.py`) — two
  `write_month` calls for the same month produce distinct `.tmp` source
  paths.
- `test_fetch_entsoe_cache_tmp_path_is_per_call_unique` (`test_fetch.py`) —
  same regression for the cache-file write path.

### WR-03: `_dataset_root`/`_now_utc` helpers are independently reimplemented across modules

**Files modified:** `src/epra/ingest/_fetch.py`, `src/epra/ingest/_io.py`, `src/epra/ingest/entsoe.py`, `src/epra/ingest/validate.py`
**Commit:** `a2dadc7`
**Applied fix:** Moved both duplicated helpers into `_io.py` as the single
canonical implementation:
- Added `_io._dataset_root(dataset, settings)` (= `_data_raw_root(settings) / dataset`).
  `entsoe.py` and `validate.py` now import it instead of reimplementing the
  same `REPO_ROOT`-relative path resolution; their local copies were
  deleted, and the now-unused `REPO_ROOT` import was removed from
  `entsoe.py` (still used elsewhere in `validate.py`, so kept there).
- `_fetch.py` now imports `_io._now_utc` instead of reimplementing an
  identical one-line `datetime.now(UTC)` seam; its local copy and the
  now-unused `UTC` import were removed.

Confirmed no circular imports (`_io.py` has no dependency on `entsoe.py` or
`validate.py`) and no test-isolation regression: the only existing
monkeypatch of this seam (`monkeypatch.setattr(_io, "_now_utc", ...)` in
`test_io.py`) patches the name in `_io`'s own namespace and is unaffected by
`_fetch.py` importing the same function object into its namespace (same
established pattern this codebase already uses for `_fetch.entsoe_token`).

## Skipped Issues

None — all 5 in-scope findings (CR-01, CR-02, WR-01, WR-02, WR-03) were fixed
and committed. Info findings IN-01 and IN-02 were out of scope for this pass
(`fix_scope=critical_warning`).

---

_Fixed: 2026-07-22T03:37:11Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
