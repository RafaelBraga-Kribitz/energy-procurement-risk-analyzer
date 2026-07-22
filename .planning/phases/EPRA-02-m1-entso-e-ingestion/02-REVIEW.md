---
phase: EPRA-02-m1-entso-e-ingestion
reviewed: 2026-07-22T00:00:00Z
depth: deep
files_reviewed: 17
files_reviewed_list:
  - src/epra/ingest/_fetch.py
  - src/epra/ingest/_io.py
  - src/epra/ingest/entsoe.py
  - src/epra/ingest/exceptions.py
  - src/epra/ingest/validate.py
  - tests/conftest.py
  - tests/test_raw_contracts.py
  - tests/unit/test_aggregate_hourly.py
  - tests/unit/test_config.py
  - tests/unit/test_entsoe_orchestration.py
  - tests/unit/test_entsoe_parse.py
  - tests/unit/test_fetch.py
  - tests/unit/test_ingest_gates.py
  - tests/unit/test_io.py
  - tests/unit/test_stubs_fail_loudly.py
  - Makefile
  - pyproject.toml
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase EPRA-02: Code Review Report — M1 ENTSO-E Ingestion (Iteration 2)

**Reviewed:** 2026-07-22
**Depth:** deep
**Files Reviewed:** 17
**Status:** clean

## Summary

Re-review of all 17 in-scope files after the fixer's five commits
(`06e440c` CR-01, `4bb53f3` CR-02, `5031698` WR-01, `2f97761` WR-02, `a2dadc7`
WR-03). All five prior findings were traced end-to-end against the current
code and are genuinely resolved, with no new correctness or security defects
introduced by the fixes:

- **CR-01 (`iter_chunks` 90-day bound):** verified by direct trace against
  `timeutil.iter_month_starts`/`next_month` — the month list is contiguous
  with no gaps (`month_start(start)` to `month_start(end)` inclusive, one
  entry per calendar month), and the new chunking loop only closes a chunk
  when adding the next month would push `(prospective_end - chunk[0]).days`
  over 90, so every yielded `(start, end)` pair (a) tiles the input range
  with no gaps/overlaps and (b) never exceeds the 90-day bound
  `EntsoeQuery.__post_init__` enforces. Manually simulated the Apr–Jun 2019
  case (91 raw calendar days) and confirmed it now splits into a 61-day and a
  30-day chunk, both valid `EntsoeQuery` windows. Backed by four new
  dedicated tests in `tests/unit/test_entsoe_orchestration.py`
  (`test_iter_chunks_never_exceeds_90_days_across_2019_2025`,
  `test_iter_chunks_covers_full_window_with_no_gaps_or_overlaps`,
  `test_iter_chunks_apr_may_jun_91_day_span_is_split_not_rejected`,
  `test_iter_chunks_second_backfill_chunk_from_real_start_date_is_valid`).
- **CR-02 (token-leak scrub):** `_error_detail` no longer falls back to
  `str(exc)`; the empty-body branch returns a fixed, token-free
  `f"{type(exc).__name__}: no response body available"` string. Traced every
  raise site that constructs an `IngestAuthError`/`IngestTransportError`
  (`_invoke_transport_once`'s two branches and `fetch_entsoe`'s
  retry-exhausted handler) — all three route through `_error_detail` and all
  three now use `raise ... from None`, severing `__cause__` so a future
  traceback dump can't reprint the original token-bearing
  `requests.HTTPError.__str__()`. Also confirmed no other call site in
  `epra.ingest` logs a raw caught exception's `str()`/traceback — the only
  `logger.error("...: %s", exc)` sites (`entsoe.py:798`, `validate.py:475`)
  format `IngestError` subclasses whose own messages are already built from
  `_error_detail`/controlled text, not the original transport exception.
  Backed by `test_fetch_entsoe_401_empty_body_never_leaks_token_via_str_exc_fallback`
  and `test_fetch_entsoe_5xx_empty_body_exhausted_retries_never_leaks_token`,
  both of which assert `FAKE_TOKEN not in str(excinfo.value)` and
  `excinfo.value.__cause__ is None`.
- **WR-01 (doc-only):** `latest_complete_month`/`_complete_price_months`
  docstrings now explicitly state the day-presence-only heuristic is
  "WEAKER than ING-080's hour-coverage gate" and direct callers needing
  hour-level completeness to also run `validate.run_gates()`. Resolved.
- **WR-02 (unique temp filenames):** both `_fetch.fetch_entsoe` and
  `_io.write_month` now suffix temp paths with
  `f"{name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"`, backed by new spy-based
  regression tests in both `test_fetch.py` and `test_io.py` asserting two
  back-to-back calls produce distinct `.tmp` source paths. Resolved.
- **WR-03 (helper consolidation):** `_dataset_root` and `_now_utc` now live
  once in `_io.py` and are imported by `entsoe.py`/`validate.py`/`_fetch.py`;
  confirmed via import statements in all three consumer modules and no
  remaining duplicate local definitions. Resolved.

No new Critical or Warning issues were found in this pass. The two Info-level
items from the previous review were not addressed by the fixer (they were
explicitly out of scope for this fix cycle) and remain open; they are noted
below for visibility but do not block this phase.

## Info

### IN-01: `ingested_at_utc` provenance column is a plain ISO string, inconsistent with `ts_utc`'s tz-aware timestamp dtype

**File:** `src/epra/ingest/_io.py:186`
**Issue:** `write_month` still sets `out["ingested_at_utc"] = _now_utc().isoformat()`, stored/asserted as plain `object`/string dtype, while `ts_utc` is a proper tz-aware `datetime64[ns, UTC]`. Any downstream freshness/staleness calculation over `ingested_at_utc` must re-parse the string rather than compare timestamps directly. Carried forward unfixed from the previous review; still low-risk and non-blocking.
**Fix:** Store `ingested_at_utc` as a tz-aware UTC timestamp column matching `ts_utc`'s dtype, unless there's an explicit downstream reason (e.g. a strict-string dbt seed contract) — if so, document that reason.

### IN-02: Fixture provenance documentation is inconsistent between `conftest.py`'s README template and `test_raw_contracts.py`'s docstring

**File:** `tests/conftest.py:25-42`, `tests/test_raw_contracts.py:9-16`
**Issue:** The README template written by `_ensure_entsoe_fixtures_dir()` still describes the ENTSO-E fixtures as "generated once from real ENTSO-E pulls," while `test_raw_contracts.py`'s module docstring states they were "generated once via the real Appendix-A parsers... then copied" and concedes at least `entsoe_prices_delu` (and, by its own "same precedent" note, effectively all of them, given the synthetic `epra-fixture-*` `mRID`s in the committed XML) are hand-built rather than real pulls. Carried forward unfixed from the previous review.
**Fix:** Reconcile the two docstrings — state plainly that all currently committed ENTSO-E fixtures are hand-built synthetic samples matching the documented Appendix-A shape, not captured live pulls, until a real pull is substituted in.

---

_Reviewed: 2026-07-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
