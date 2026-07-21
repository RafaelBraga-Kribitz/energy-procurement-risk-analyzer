# ADR-003: EntsoeRawClient as transport; own Appendix-A parsers (adopts SG-01)
Date: 2026-07-21  |  Status: accepted

## Context
ING-022 names `EntsoePandasClient` as the mandated `entsoe-py` client. But
ING-009 requires caching **raw HTTP responses** (XML), and ING-050/060/063
require fields — `resolution`, `curveType`, `currency_Unit`/`price_Measure_Unit`
— that `EntsoePandasClient` discards on the way to building its DataFrame. A
literal reading of ING-022 makes ING-009/050/060/063 unsatisfiable without a
separate transport hack, which is exactly the SG-01 gap recorded in
`docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md`.

Per AGENTS.md A-1 (spec supremacy: when reality makes a requirement
impossible as written, write an ADR, implement the closest behavior that
preserves the output contract, reference the ADR in the docstring) and per
`02-RESEARCH.md` Open Question 1, this ADR is Wave 0 — it must merge before
`_fetch` (02-03) or the Appendix-A parsers (02-04) are implemented.

## Decision
Adopt SG-01. `src/epra/ingest/_fetch.py` uses `entsoe.EntsoeRawClient` as a
URL-builder/transport only — its `query_day_ahead_prices`, `query_load`, and
`query_generation` methods return raw XML strings (`Publication_MarketDocument`
/ `GL_MarketDocument`). This is still "use `entsoe-py`" per ING-022's intent
(the mandated *library*), just not the `EntsoePandasClient` class named in the
literal text.

`src/epra/ingest/entsoe.py` owns the Appendix-A XML parsers
(`parse_publication_xml`, `parse_gl_xml`) that produce the exact §7 output
contracts: `ts_utc`, `price_eur_mwh`/`load_mw`/`value_mw`, `resolution`,
`zone`, PSR `psr_type`/`psr_name`/`kind` for generation. `EntsoePandasClient`
is never imported or called anywhere in this codebase — not in `_fetch`, not
in analytics, per the ING-022 "wrap it, never call from analytics" rule
extended here to "never call at all."

Raw XML bytes are cached under `data/cache/entsoe/<request_hash>.bin` per
ING-009 before parsing. Chunking stays month-by-month (trivially inside the
ING-030 ≤90-day bound). Resolution, curveType (A03 forward-fill, ING-063),
and currency/unit assertions (ING-050) are read directly from the XML by the
Appendix-A parser, never inferred from a client method that already dropped
them — except where ING-060 explicitly allows resolution inference from
timestamp spacing as a fallback.

## Consequences
- `_fetch.py` and `entsoe.py` (02-03, 02-04) depend on this ADR; they import
  `EntsoeRawClient`, never `EntsoePandasClient`.
- ING-009 raw cache and ING-060/063 metadata are preserved exactly as
  written — no output-contract loss versus a literal-but-unsatisfiable
  ING-022 reading.
- Test doubles for `_fetch` (02-03 tests) stub `EntsoeRawClient.query_*` to
  return canned XML strings, not DataFrames — parser tests exercise the same
  Appendix-A code path used against live data.
- Any future code that imports `EntsoePandasClient` for persistence is a
  regression against this ADR and against ING-022's "wrap it" clause.

## Spec deviations
ING-022 (literal `EntsoePandasClient` reading). Output contracts preserved:
§7 raw parquet columns, ING-009 raw-response cache, ING-060 `resolution`
column, ING-063 A03 forward-fill semantics — all satisfied via
`EntsoeRawClient` transport + first-party Appendix-A parser instead of the
named client class. Cross-reference: `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md`
SG-01, now `adopted (ADR-003)`.
