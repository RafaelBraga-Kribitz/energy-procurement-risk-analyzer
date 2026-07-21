---
phase: EPRA-02-m1-entso-e-ingestion
reviewed: 2026-07-21T00:00:00Z
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
  critical: 2
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase EPRA-02: Code Review Report — M1 ENTSO-E Ingestion

**Reviewed:** 2026-07-21
**Depth:** deep
**Files Reviewed:** 17
**Status:** issues_found

## Summary

The five `epra.ingest` modules implement a coherent, well-documented ingestion
pipeline with strong intent around atomic writes, fail-fast gates, and secret
hygiene. Most of the priority areas hold up under trace: `hourly_mean` never
sums, A03 forward-fill is seeded/period-scoped correctly, `write_month`'s
atomic temp-file-then-`os.replace` pattern is implemented and exercised by a
dedicated spy test, and `request_hash` genuinely strips `securityToken`
case-insensitively before hashing.

However, a cross-file trace of the request-chunking path (`entsoe.iter_chunks`
→ `_fetch.EntsoeQuery.__post_init__`) turns up a concrete, high-confidence bug
that will break the very first real backfill run and periodically break the
45-day incremental refresh: grouping raw calendar months into fixed groups of
3 does not bound the resulting window to ING-030's documented ≤90-day limit,
and most 3-consecutive-month spans exceed it. No test exercises a 3+-month
window, so this is invisible in the current suite (every orchestration test
uses a 1–2 month range). A second, security-relevant gap was found in the
error-detail fallback path in `_fetch.py`: when an HTTP error response has no
body text, the code falls back to `str(exc)`, which for `requests.HTTPError`
(raised via `response.raise_for_status()`) includes the full request URL —
including the real `securityToken` — undermining the A-7/ING-008 "never log
the token" guarantee in a class of failures (empty-body 401/403/etc.) the
current tests don't reach (fixture errors always set non-empty `text`).

## Critical Issues

### CR-01: `iter_chunks` groups 3 raw calendar months without bounding the window to ING-030's 90-day maximum — breaks real backfill and periodically breaks incremental refresh

**File:** `src/epra/ingest/entsoe.py:443-458` (interacts with `src/epra/ingest/_fetch.py:72-87`)

**Issue:**
`iter_chunks` groups the month-starts yielded by `iter_month_starts` into
fixed batches of 3 and yields `(chunk[0], next_month(chunk[-1]))` as the
request window, with no check that the resulting span is ≤90 days:

```python
def iter_chunks(start: date, end: date) -> Iterator[tuple[date, date]]:
    months = list(iter_month_starts(start, end))
    for i in range(0, len(months), 3):
        chunk = months[i : i + 3]
        yield chunk[0], next_month(chunk[-1])
```

Most 3-consecutive-calendar-month spans exceed 90 days (e.g. Apr+May+Jun = 91,
Jul+Aug+Sep = 92, Oct+Nov+Dec = 92 — verified by simulating every 3-month
sliding window across the calendar). `EntsoeQuery.__post_init__`
(`_fetch.py:81-87`) enforces the ≤90-day rule ING-030 itself documents
(`docs/SPEC-01_data_ingestion.md:66`: "request in ≤ 90-day windows"), so any
chunk exceeding it raises `ValueError` before any HTTP call is made:

```python
window = self.period_end - self.period_start
if window > timedelta(days=90):
    raise ValueError(...)
```

Simulating the real production entry point — `settings.window.start_date =
2019-01-01` (`config/settings.yaml`, pinned by
`tests/unit/test_config.py::test_settings_window_and_ingest_params`) through
`backfill()` — the first chunk (Jan–Mar 2019, 90 days) succeeds, but the
**second** chunk is Apr 1 → Jul 1, 2019 = 91 days, which raises immediately.
`make backfill` (the Makefile's only backfill entry point) will crash on the
second `ingest_dataset` chunk for every one of the four datasets.

`ingest_incremental()`'s 45-day lookback is also affected periodically: when
`date.today()` falls early enough in a month that the 45-day lookback spans
three calendar months (e.g. today = 2020-03-01, start = 2020-01-16 → months
Jan/Feb/Mar grouped into one chunk spanning Jan 1–Apr 1, 2020 = 91 days in
that leap year), the same crash occurs in `make ingest`.

No test in `tests/unit/test_entsoe_orchestration.py` or `tests/unit/test_fetch.py`
constructs a window spanning 3+ calendar months (`iter_chunks` itself has zero
direct test coverage — confirmed via search), so this is currently invisible
to CI. Every orchestration test's stub transport also ignores the query
window and returns fixed fixture XML, which further masks the issue even if a
wider window were tried, since the returned rows don't vary with the request.

**Fix:** Bound each chunk by actual elapsed days, not a fixed count of
months, e.g.:

```python
def iter_chunks(start: date, end: date) -> Iterator[tuple[date, date]]:
    months = list(iter_month_starts(start, end))
    chunk: list[date] = []
    for m in months:
        prospective_end = next_month(m)
        if chunk and (prospective_end - chunk[0]).days > 90:
            yield chunk[0], next_month(chunk[-1])
            chunk = [m]
        else:
            chunk.append(m)
    if chunk:
        yield chunk[0], next_month(chunk[-1])
```

Add a direct unit test for `iter_chunks` asserting every yielded
`(start, end)` pair satisfies `(end - start).days <= 90` across a full
2019→2025 span, and an orchestration test that drives `ingest_dataset`/
`backfill` over a 4+ month window (not just 1–2 months) so a stub transport
that varies its response by the requested window would actually catch a
regression here.

---

### CR-02: Error-detail fallback can leak the real `securityToken` via `str(exc)` when the HTTP error response has no body

**File:** `src/epra/ingest/_fetch.py:136-165`

**Issue:** `_error_detail` is the sole place `_invoke_transport_once` (and
`fetch_entsoe`'s outer retry-exhausted handler) draws the message text for
`IngestAuthError`/`IngestTransportError`:

```python
def _error_detail(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    text = getattr(response, "text", None)
    if text:
        return str(text)[:500]
    return str(exc)[:500]
```

The comment above it asserts "the token only ever appears in the outgoing
request's query string, not in ENTSO-E's response body, so truncating the
response text here cannot leak it" — but the fallback branch (`if not text`)
does not truncate response text; it falls back to `str(exc)`. `entsoe-py`'s
`EntsoeRawClient._base_request` (site-packages `entsoe/entsoe.py:106-109`)
calls `response.raise_for_status()`, whose `requests.HTTPError` message is of
the form `f"{status_code} ... for url: {response.url}"` — and `response.url`
is the *real* request URL, built with `params={'securityToken': self.api_key,
...}` (`entsoe/entsoe.py:98-107`). Whenever ENTSO-E (or an intermediary proxy/
WAF) returns an error with an **empty body** — plausible for a hard 401/403
from a gateway that never reaches ENTSO-E's own XML error responses — `text`
is falsy, `_error_detail` falls through to `str(exc)`, and the resulting
`IngestAuthError`/`IngestTransportError` message embeds the real token.

Separately, both raise sites use `raise IngestAuthError(...) from exc` /
`raise IngestTransportError(...) from exc`, preserving the original
`requests.HTTPError` (whose own `str()` also contains the token-bearing URL)
as `__cause__`. Even if `_error_detail` were fixed, any consumer that prints a
full traceback of an uncaught `IngestError` (a bare script invocation, a
notebook, `logger.exception(...)`, pytest's own failure output, or a future
error-reporting integration) will print the chained cause's message too —
which still contains the token. `main()`'s current
`logger.error("ingest failed: %s", exc)` happens not to trigger this (it
formats only the top-level exception, not the chain), but that is incidental,
not enforced.

This directly contradicts A-7/ING-008 ("token must NEVER include the token
value itself... never logged"), and the current test suite does not exercise
this path: every synthetic `_http_error(status, text=...)` in
`tests/unit/test_fetch.py` sets a non-empty `text`, so the `str(exc)` fallback
branch is never hit by any test.

**Fix:** Never fall back to the raw exception string; use a fixed, token-free
description when no response body is available, and sever the exception
chain so the token-bearing original exception can't be reconstructed from a
future traceback dump:

```python
def _error_detail(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    text = getattr(response, "text", None)
    if text:
        return str(text)[:500]
    return f"{type(exc).__name__}: no response body available"
```

```python
raise IngestAuthError("entsoe", f"HTTP {status}: {_error_detail(exc)}") from None
...
raise IngestTransportError("entsoe", _error_detail(exc), status_code=400) from None
```

(apply the same `from None` in `fetch_entsoe`'s retry-exhausted handler).
Add a test with an `_http_error(401, text="")` (empty body) asserting the
raised exception's message — and `str(excinfo.value.__cause__)` if chaining
is kept — never contains the fake token.

## Warnings

### WR-01: `latest_complete_month`'s "complete" check only requires ≥1 row per UTC day, not full-hour coverage

**File:** `src/epra/ingest/entsoe.py:635-658`

**Issue:** `_complete_price_months` (feeding `latest_complete_month`, ING-042)
defines a month as complete when `expected_days <= present_days`, where
`present_days` is derived from `hourly_mean(frame, ...)["ts_utc"].dt.date` —
i.e. it only checks that at least one hourly row exists per calendar day of
the month, not that all (or nearly all) 24 hours are present. A month with,
say, only 1 out of 24 hours of data on every day would be reported
"complete" here, become the default `backfill`/CLI end boundary
(`_resolve_backfill_end`), and be used unguarded by any downstream module
that calls `latest_complete_month()` for a trustworthy window boundary — the
module docstring explicitly says other modules "call this instead of
guessing." The stricter `ING-080` gate (≤24 missing hours per zone-year) would
eventually catch this, but only when `make validate-ingest` is separately run
— `latest_complete_month` itself gives no such guarantee and is described as
"computed, not assumed" without noting this gap.

**Fix:** Either tighten `_complete_price_months` to require full (or
near-full, matching ING-080's ≤24-missing-hours tolerance) hour coverage per
month, or explicitly document in the docstring that "complete" here is a
weaker, day-presence-only heuristic and that callers relying on hour-level
completeness must also run `validate.run_gates()`.

### WR-02: Cache and parquet-writer temp files are not process-unique — concurrent runs can race on the same `.tmp` path

**File:** `src/epra/ingest/_fetch.py:298-301`, `src/epra/ingest/_io.py:176-178`

**Issue:** Both atomic-write sites derive the temp filename purely from the
target filename:

```python
tmp_path = cache_path.parent / (cache_path.name + ".tmp")   # _fetch.py
tmp_path = path.parent / (path.name + ".tmp")                # _io.py
```

If two processes concurrently fetch the same `EntsoeQuery` cache key (e.g. a
manual `--no-cache` run overlapping a scheduled `ingest_incremental`) or write
the same month file, both write to the identical `.tmp` path before the final
`os.replace`, so one process's partially-written temp file can be clobbered
or renamed out from under the other, defeating the intended atomicity
guarantee in exactly the concurrent scenario atomic writes are meant to
protect against. This is untested (`test_write_month_replaces_via_tmp_file_and_os_replace`
only exercises the single-writer path).

**Fix:** Suffix the temp filename with a per-call unique token (PID +
`uuid4().hex[:8]`, or `tempfile.mkstemp` in the same directory) so concurrent
writers never share a temp path, e.g. `f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"`.

### WR-03: `_dataset_root`/`_now_utc` helpers are independently reimplemented in `entsoe.py`/`validate.py` and `_fetch.py`/`_io.py`

**File:** `src/epra/ingest/entsoe.py:628-632`, `src/epra/ingest/validate.py:388-391`; `src/epra/ingest/_fetch.py:193-195`, `src/epra/ingest/_io.py:92-94`

**Issue:** `entsoe._dataset_root` and `validate._dataset_root` are two
near-identical private functions computing the same path
(`data_raw / dataset`), and `_fetch._now_utc`/`_io._now_utc` are two identical
one-line wall-clock seams. Both modules' docstrings note the duplication
("mirrors `_io._data_raw_root`") but don't share the implementation, so a
future change to path resolution (e.g. adding a new root override) has to be
applied in two (or four) places or silently drifts.

**Fix:** Move `_dataset_root`/`_data_raw_root` into `_io.py` as the single
canonical implementation and import it from `validate.py`/`entsoe.py`; same
for the `_now_utc()` seam (or accept the duplication explicitly with a
`# keep in sync with _io._now_utc` comment referencing both sites).

## Info

### IN-01: `ingested_at_utc` provenance column is a plain ISO string, inconsistent with `ts_utc`'s tz-aware timestamp dtype

**File:** `src/epra/ingest/_io.py:169`

**Issue:** `write_month` sets `out["ingested_at_utc"] = _now_utc().isoformat()`
— stored and asserted (`tests/unit/test_io.py`, `tests/test_raw_contracts.py`)
as plain `object`/string dtype, while the dataset's own `ts_utc` column is a
proper tz-aware `datetime64[ns, UTC]`. Any downstream freshness/staleness
calculation over `ingested_at_utc` has to re-parse the string rather than
compare timestamps directly.

**Fix:** Store `ingested_at_utc` as a tz-aware UTC timestamp column (matching
`ts_utc`'s dtype) unless there's an explicit downstream reason (e.g. a
strict-string dbt seed contract) requiring the string form — if so, note that
reason in the docstring.

### IN-02: Fixture provenance documentation is inconsistent between `conftest.py`/README and `test_raw_contracts.py`

**File:** `tests/conftest.py:25-42`, `tests/test_raw_contracts.py:9-16`

**Issue:** The README template written by `_ensure_entsoe_fixtures_dir()`
describes the ENTSO-E fixtures as "generated once from real ENTSO-E pulls so
CI never needs network access," while `test_raw_contracts.py`'s own module
docstring states the fixtures were "generated once via the real Appendix-A
parsers... then copied," and separately concedes `entsoe_prices_delu` (and,
by its own "same precedent" note, effectively all of them, given the
`epra-fixture-*` synthetic `mRID`s visible in the committed XML) are
hand-built rather than real pulls. A future contributor trusting the README's
"real ENTSO-E pulls" claim could over-rely on these fixtures reflecting
real-world XML quirks (field presence/ordering, encoding edge cases) they
don't actually capture.

**Fix:** Reconcile the two docstrings — state plainly that all currently
committed ENTSO-E fixtures are hand-built synthetic samples matching the
documented Appendix-A shape, not captured live pulls, until a real pull is
substituted in.

---

_Reviewed: 2026-07-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
