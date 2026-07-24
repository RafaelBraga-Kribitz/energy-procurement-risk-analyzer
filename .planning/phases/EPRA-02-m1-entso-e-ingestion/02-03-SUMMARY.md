---
phase: EPRA-02-m1-entso-e-ingestion
plan: 03
subsystem: ingest
tags: [entsoe-py, tenacity, requests, http-transport, cache, retry, secrets]

# Dependency graph
requires:
  - phase: EPRA-02-m1-entso-e-ingestion (02-01)
    provides: ADR-003 (EntsoeRawClient transport decision), exceptions.py hierarchy
  - phase: EPRA-02-m1-entso-e-ingestion (02-02)
    provides: _io.request_hash() token-stripped cache-key hashing, tmp_settings test fixture
provides:
  - EntsoeQuery frozen dataclass — validated, immutable request window (ING-030)
  - fetch_entsoe() — cached, retried, polite ENTSO-E HTTP transport (ING-006/007/008/009/021/031)
  - Injectable TransportFn seam so downstream parser/orchestration tests never hit the network
affects: [02-04 (Appendix-A XML parsers), 02-05 (window orchestration/backfill), 02-06/02-07 (validation gates, fixtures)]

# Tech tracking
tech-stack:
  added: [tenacity retry/backoff wired into ingest, entsoe.entsoe.EntsoeRawClient as the sole ENTSO-E client]
  patterns:
    - "Transport seam: fetch_entsoe(..., transport: TransportFn | None) defaults to real EntsoeRawClient but accepts a stub for hermetic tests (ADR-003)"
    - "Two-phase retry classification: _invoke_transport_once converts 400/401/403 to terminal exceptions immediately; tenacity's retry_if_exception(_is_retryable) only retries 429/5xx/connection errors"
    - "Cache-key URL built purely for request_hash() input, never sent over the wire"

key-files:
  created:
    - src/epra/ingest/_fetch.py
    - tests/unit/test_fetch.py
  modified: []

key-decisions:
  - "Import EntsoeRawClient from entsoe.entsoe (not the entsoe package __init__) to satisfy mypy --strict's no_implicit_reexport, since entsoe-py ships py.typed but its __init__.py has no __all__"
  - "Token-fail-fast test (Task 3) patches _fetch.entsoe_token directly instead of monkeypatch.delenv(ENTSOE_API_TOKEN), avoiding the known python-dotenv re-population flake already tracked against tests/unit/test_config.py"
  - "Politeness sleep (ING-007) fires once per successful live fetch, after caching and before return — paces the *next* live call regardless of call site, rather than tracking cross-call state"
  - "ING-008 row count is unknown at the transport layer (raw XML, unparsed) — logged as rows=n/a; the actual count is the parser's responsibility in 02-04"

requirements-completed: [REQ-ING-01, ING-006, ING-007, ING-008, ING-009, ING-020, ING-021, ING-030]

coverage:
  - id: D1
    description: "EntsoeQuery frozen dataclass enforces tz-aware UTC bounds, end > start, and a 90-day max window before any HTTP call (ING-030)"
    requirement: "ING-030"
    verification:
      - kind: unit
        ref: "tests/unit/test_fetch.py#test_entsoe_query_* (8 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "fetch_entsoe caches raw XML under data/cache/entsoe/<hash>.bin and reuses it once a window is older than cache_min_age_days; use_cache=False always hits the network (ING-009)"
    requirement: "ING-009"
    verification:
      - kind: unit
        ref: "tests/unit/test_fetch.py#test_fetch_entsoe_live_writes_cache_file, test_fetch_entsoe_uses_cache_when_window_old_enough, test_fetch_entsoe_use_cache_false_always_hits_network, test_fetch_entsoe_ignores_cache_for_recent_window"
        status: pass
    human_judgment: false
  - id: D3
    description: "429/5xx/connection errors retry with tenacity exponential backoff (stop after 6 attempts); 400/401/403 raise immediately without retry (ING-006)"
    requirement: "ING-006"
    verification:
      - kind: unit
        ref: "tests/unit/test_fetch.py#test_fetch_entsoe_retries_429_then_succeeds, test_fetch_entsoe_retries_connection_error_then_succeeds, test_fetch_entsoe_5xx_exhausts_retries_raises_transport_error, test_fetch_entsoe_401_raises_auth_error_without_retry, test_fetch_entsoe_403_raises_auth_error_without_retry, test_fetch_entsoe_400_raises_transport_error_without_retry"
        status: pass
    human_judgment: false
  - id: D4
    description: "Consecutive live calls are paced by a politeness sleep (>=0.5s); cache hits never sleep (ING-007)"
    requirement: "ING-007"
    verification:
      - kind: unit
        ref: "tests/unit/test_fetch.py#test_fetch_entsoe_sleeps_between_live_calls, test_fetch_entsoe_cache_hit_does_not_sleep"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every request logs source/window/status/elapsed_ms and the token never appears in any log record (ING-008, A-7)"
    requirement: "ING-008"
    verification:
      - kind: unit
        ref: "tests/unit/test_fetch.py#test_fetch_entsoe_logs_no_token"
        status: pass
    human_judgment: false
  - id: D6
    description: "fetch_entsoe fails fast with RuntimeError from entsoe_token() before any network call when the token is unset (ING-021)"
    requirement: "ING-021"
    verification:
      - kind: unit
        ref: "tests/unit/test_fetch.py#test_fetch_entsoe_fails_without_token"
        status: pass
    human_judgment: false

# Metrics
duration: ~25min
completed: 2026-07-21
status: complete
---

# Phase 2 Plan 3: ENTSO-E HTTP Transport (_fetch) Summary

**Cached, retried `fetch_entsoe()` wrapping `EntsoeRawClient` (ADR-003) — tenacity backoff on 429/5xx/connection errors, immediate fail on 400/401/403, ING-009 seven-day cache reuse, and ING-007 politeness sleep, all proven against a stub transport with zero live network calls.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 completed
- **Files created:** 2 (`src/epra/ingest/_fetch.py`, `tests/unit/test_fetch.py`)

## Accomplishments
- `EntsoeQuery` frozen dataclass enforces ING-030's window invariants (tz-aware UTC, end > start, ≤90 days) at construction time, before any HTTP call is possible.
- `fetch_entsoe()` is now the single ENTSO-E network boundary: builds a token-stripped cache key via `_io.request_hash()`, checks `data/cache/entsoe/<hash>.bin`, and only calls the network when the cache is missing/ineligible/bypassed.
- Two-phase HTTP error handling: 400/401/403 convert immediately to `IngestTransportError`/`IngestAuthError` (never retried); 429/5xx/connection errors retry via `tenacity` (`wait_exponential(2, 2, 120)`, `stop_after_attempt(6)`), then convert to `IngestTransportError` once exhausted.
- Politeness sleep (`settings.ingest.entsoe_sleep_s`, default 0.5s) fires after every successful live fetch, never on a cache hit.
- ING-008 logging (`source=entsoe window=...status=...elapsed_ms=...`) never includes the token — verified by asserting the fake token string is absent from every captured log record.
- 22 unit tests, all passing, zero network access (stub `TransportFn` injected per ADR-003), zero real secrets used (fake token fixture).

## Task Commits

Each task was committed atomically:

1. **Task 1: EntsoeQuery and window validation** — `d78ae94` (feat)
2. **Task 2: fetch_entsoe with cache, retry, politeness** — `b222d6a` (feat)
3. **Task 3: Token fail-fast integration test** — `70335a9` (test)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified
- `src/epra/ingest/_fetch.py` — `EntsoeQuery`, `fetch_entsoe()`, retry/cache/politeness/logging internals; the only module that imports `entsoe.entsoe.EntsoeRawClient`.
- `tests/unit/test_fetch.py` — 22 unit tests covering query validation, cache hit/miss/bypass/7-day-rule, retry/no-retry HTTP matrix, politeness sleep, secret-safe logging, and token fail-fast.

## Decisions Made
- Imported `EntsoeRawClient` from `entsoe.entsoe` rather than the package's `__init__.py` re-export — `entsoe-py` ships `py.typed` but has no `__all__`, so mypy `--strict`'s `no_implicit_reexport` flagged the plain `from entsoe import EntsoeRawClient` form.
- Task 3's fail-fast test patches `_fetch.entsoe_token` directly instead of following the plan's literal `monkeypatch.delenv(ENTSOE_API_TOKEN)` instruction, because `python-dotenv`'s `load_dotenv()` repopulates a fully-deleted env var from the real `.env` (the exact, already-documented flake in `tests/unit/test_config.py::test_entsoe_token_fails_fast_when_unset`, deferred and out of scope for this plan). Patching the accessor tests the same ING-021 contract at the `fetch_entsoe` entrypoint without inheriting that flake.
- `fetch_entsoe`'s cache-key URL (`_cache_request_url`) is a deterministic, self-contained string built only to feed `request_hash()` — it is never sent over the network, since `EntsoeRawClient` builds and sends its own request internally.
- Row count in the ING-008 log line is `rows=n/a`: `_fetch` only ever sees raw, unparsed XML, so the real row count is logged by the parser (02-04), not here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed mypy `attr-defined`/`unused-ignore` errors from the `entsoe` package import**
- **Found during:** Task 2 (fetch_entsoe implementation)
- **Issue:** `from entsoe import EntsoeRawClient` failed `mypy --strict` (`no_implicit_reexport`) because `entsoe-py` ships `py.typed` but its `__init__.py` has no `__all__`; two speculative `# type: ignore[no-any-return]` comments were then flagged as unused once the import was fixed.
- **Fix:** Import from `entsoe.entsoe` directly (the module where `EntsoeRawClient` is actually defined); removed the now-unnecessary `type: ignore` comments.
- **Files modified:** `src/epra/ingest/_fetch.py`
- **Verification:** `uv run mypy src/epra/ingest/_fetch.py` → `Success: no issues found in 1 source file`
- **Committed in:** `b222d6a` (Task 2 commit)

**2. [Rule 3 - Blocking] Replaced Task 3's literal `monkeypatch.delenv` instruction with a direct `entsoe_token` patch**
- **Found during:** Task 3 (token fail-fast test)
- **Issue:** The plan's action text specified `monkeypatch.delenv("ENTSOE_API_TOKEN", raising=False)`, but this environment's `.env` contains a real token, and `entsoe_token()`'s `load_dotenv()` call repopulates a *deleted* env var from `.env` (dotenv only skips keys that already exist, even as empty strings — it does not skip keys that are absent). This is the identical, already-known root cause of the pre-existing `test_config.py::test_entsoe_token_fails_fast_when_unset` flake logged in STATE.md/deferred-items.md.
- **Fix:** `monkeypatch.setattr(_fetch, "entsoe_token", _raise_unset)` — patches the accessor `fetch_entsoe` calls, so the test verifies "fetch fails fast when the token is unavailable" (ING-021's actual contract at this entrypoint) without depending on `.env`/dotenv timing at all.
- **Files modified:** `tests/unit/test_fetch.py`
- **Verification:** `uv run pytest tests/unit/test_fetch.py -k token -x` passes; confirmed the transport stub is never called (`calls == []`).
- **Committed in:** `70335a9` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking issues fixed inline, no scope creep).
**Impact on plan:** Both fixes were necessary to make the specified verification commands actually pass in this environment; neither changes `fetch_entsoe`'s public contract or behavior.

## Issues Encountered
- `uv run ruff format` reformatted `src/epra/ingest/_fetch.py` (long-line wrapping) after the first full draft — reformatted in place before the first commit; no functional change.
- Plan's Task 1 verify command (`pytest -k EntsoeQuery`) is case-sensitive and this project's test names are snake_case (`test_entsoe_query_*`), so `-k EntsoeQuery` selects zero tests as literally written. Ran `-k entsoe_query` instead (8/8 pass) — noted here rather than renaming tests away from the project's snake_case convention.
- Pre-existing (M0) `tests/unit/test_config.py::test_entsoe_token_fails_fast_when_unset` still fails in this environment for the reason above — unchanged from the blocker already recorded in STATE.md and `deferred-items.md`; out of scope for this plan and not touched.

## User Setup Required
None — no external service configuration required. `ENTSOE_API_TOKEN` was already present in `.env` per the resolved blocker in STATE.md; no test in this plan depends on it (all tests patch `entsoe_token` with a fake value).

## Next Phase Readiness
- `fetch_entsoe(EntsoeQuery(...), settings, transport=...)` is ready for 02-04's Appendix-A XML parsers and 02-05's window orchestration (`backfill`/`ingest_incremental`) to call directly — the `TransportFn` seam means parser/orchestration tests can keep stubbing `EntsoeRawClient.query_*` behavior without ever touching the network.
- No blockers for 02-04. The pre-existing `test_config.py` token-env flake remains deferred (unrelated to `_fetch`'s correctness) and should be picked up whenever `tests/unit/test_config.py` is next touched.

## Self-Check: PASSED

- FOUND: src/epra/ingest/_fetch.py
- FOUND: tests/unit/test_fetch.py
- FOUND: .planning/phases/EPRA-02-m1-entso-e-ingestion/02-03-SUMMARY.md
- FOUND: d78ae94 (Task 1 commit)
- FOUND: b222d6a (Task 2 commit)
- FOUND: 70335a9 (Task 3 commit)

---
*Phase: EPRA-02-m1-entso-e-ingestion*
*Completed: 2026-07-21*
