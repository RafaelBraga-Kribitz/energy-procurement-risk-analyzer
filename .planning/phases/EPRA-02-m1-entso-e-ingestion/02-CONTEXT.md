# Phase 2: M1 ENTSO-E Ingestion - Context

**Gathered:** 2026-07-21
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — decisions captured from locked SPEC-01 / ADRs / research; no open grey areas (spec-supremacy project, all RESEARCH open questions RESOLVED)

<domain>
## Phase Boundary

Real ENTSO-E market data lands in validated monthly raw parquet for 2019 → latest complete month:
- **Datasets:** AT + DE-LU day-ahead prices, AT actual load, AT actual generation (per production type).
- **Transport:** `entsoe-py` fetch with token from env, raw-XML caching, tenacity retry, sequential politeness sleep.
- **Parse:** pure XML → contracted DataFrame parsers (Appendix A/B), UTC at boundary, native resolution preserved.
- **Persist:** atomic monthly parquet under `data/raw/{dataset}/{YYYY}/` via `_io`.
- **Validate:** `validate.py` gates ING-080..085 + `make validate-ingest` markdown report on real data.
- **Operate:** `make backfill | ingest | validate-ingest` wired to package CLIs.

Out of this phase (M1): GeoSphere temperature, ÖSPI CSV, calendar/holidays (all M2 / Phase 3); dbt warehouse + canonical staging aggregation (M3 / Phase 4). One milestone, one PR (A-5).

</domain>

<decisions>
## Implementation Decisions

### Client & Transport (ADR-003 adopts SG-01)
- Use `EntsoeRawClient` (entsoe-py family) returning raw XML strings — NOT `EntsoePandasClient` — to preserve ING-009 raw cache and ING-060/063 resolution/currency metadata that PandasClient discards.
- ADR-003 is created in Wave 0 (plan 02-01) BEFORE `_fetch`/parser work; ING-022's literal PandasClient text is binding until that ADR merges (A-1).
- Cache raw XML bytes under `data/cache/entsoe/` keyed by a token-stripped request hash (ING-009); never log full request URLs or the token (A-7).
- Sequential requests only with politeness sleep (ING-007); `tenacity` exponential backoff on 429/5xx/connection errors (ING-006); chunk ≤90 days.

### Parquet I/O (ADR-004)
- Add `pyarrow>=18,<26` to runtime dependencies (SPEC-07 §3 pin-list omission corrected by ADR); pandas `.to_parquet` is canonical for `_io` and ING-070 contract tests. DuckDB is the documented fallback only.
- Atomic monthly writes: write `.parquet.tmp` then `os.replace` (ING-003); one file per dataset-month.

### Time & Aggregation
- Store UTC in raw parquet; convert at the parse boundary via `common.timeutil.to_utc` (ING-005, T-1, T-4). Never persist local/naive timestamps.
- PT15M → hourly uses arithmetic **mean** of the 4 quarters, never sum (ING-061/062, T-2). Dedicated ING-062 fixture guards this.
- A03 curveType forward-fill within period (ING-063).

### Window & Zones (ADR-005 adopts SG-02)
- `latest_complete_month` = min(AT prices complete month, DE-LU prices complete month) so the window never runs ahead of the lagging zone.
- Backfill range: 2019 → latest complete month; incremental appends new complete months idempotently.

### Validation Gates
- `validate.py` = pure gate functions (no I/O) + a thin report writer to `reports/ingestion/validation_*.md`.
- Gates apply the same hourly-mean rule as staging BEFORE coverage checks so ING-080 is not fed 15-min rows (avoids ~4× false-missing-hour bug).
- ING-080 DST check uses `timeutil.local_hours_in_day` (23/25 on last Sun Mar/Oct).
- Never widen gate bands to pass (A-2); real gaps stay NULL and fail loudly.

### Claude's Discretion
- Internal decomposition of `_io` / `_fetch` / `entsoe` / `validate` per blueprint `03_MODULES.md`, helper naming, and fixture byte content — implementer's choice within the contracts and REQ-ID docstrings (W-2).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `epra.common.config` — `load_settings()` (frozen pydantic), `entsoe_token()`, path settings (`data_raw`, `data_cache`). Already implemented in M0.
- `epra.common.logging` — `setup()` structured logging.
- `epra.common.timeutil` — `to_utc`, `to_local`, `local_hours_in_day` (DST-tested in `test_timeutil.py`). Only sanctioned TZ layer (T-1).
- Typed stubs in `src/epra/ingest/entsoe.py` and `validate.py` raising `NotImplementedError` — public API surface to implement.

### Established Patterns
- Functional core / imperative shell: pure parsers + pure gate functions; I/O confined to `_fetch`, `_io`, thin `main()`.
- Public functions cite REQ IDs in docstrings (`Implements: ING-063`) per W-2.
- Live network isolated behind `@pytest.mark.live`; CI runs `-m "not live"` (EN-070).

### Integration Points
- Makefile targets `backfill` / `ingest` / `validate-ingest` are wired but currently fail loudly → point them at `entsoe.main` / `validate.main`.
- `tests/test_stubs_fail_loudly.py` — remove M1 rows as each stub is implemented.
- New internal modules land under `src/epra/ingest/` (`_io.py`, `_fetch.py`); tests + fixtures under `tests/` and `tests/fixtures/entsoe/`.

</code_context>

<specifics>
## Specific Ideas

- Binding authority: `docs/SPEC-01_data_ingestion.md` (ING-001..085, Appendix A/B), `docs/EXECUTION_BLUEPRINT/02_WBS.md` (T1.01–T1.09) and `03_MODULES.md` (module contracts), `AGENTS.md` traps T-1..T-4. Deviations require an ADR that preserves output contracts (A-1).
- Live backfill needs `ENTSOE_API_TOKEN` (present in `.env` as of 2026-07-21); the agent env has no token, so live real-data gate (02-07) runs as a local/human checkpoint — code + fixture gates ship without live data (EN-070, A5).

</specifics>

<deferred>
## Deferred Ideas

- GeoSphere temperature, ÖSPI manual CSV (double-entry), calendar/holidays ingestion → M2 / Phase 3 (A-5: not in this PR).
- Canonical staging hourly aggregation in dbt → M3 / Phase 4; M1 does a minimal inline hourly-mean only for its own gates.
- Holiday-aware peak definition (SG-14) → M2.

</deferred>
