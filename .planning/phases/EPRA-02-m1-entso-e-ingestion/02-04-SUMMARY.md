---
phase: EPRA-02-m1-entso-e-ingestion
plan: 04
subsystem: ingest
tags: [entsoe, xml-parsing, elementtree, pandas, tdd, timezone]

requires:
  - phase: EPRA-02-m1-entso-e-ingestion (02-01/02-03)
    provides: exceptions.py (ContractError/NoDataError), _io.write_month, _fetch.fetch_entsoe (raw XML transport), timeutil.to_utc
provides:
  - parse_publication_xml(xml) -> day-ahead prices DataFrame (ts_utc, price_eur_mwh, resolution, zone)
  - parse_gl_xml(xml, kind) -> load/generation long-format DataFrame per ING-032
  - infer_resolution(ts) -> PT60M/PT15M spacing fallback
  - hourly_mean(df, value_col) -> ING-061/062 mean-not-sum aggregation
  - iter_chunks(start, end) -> quarterly (start, end) request windows
  - PSR_NAMES Appendix B code->name table
  - 8 committed synthetic ENTSO-E XML fixtures under tests/fixtures/entsoe/
affects: [EPRA-02-05 (orchestration: backfill/ingest_incremental/latest_complete_month/main), EPRA-02-06 (validate.py gates), EPRA-03 (dbt staging hourly aggregation)]

tech-stack:
  added: []
  patterns:
    - "Namespace-agnostic XML parsing via ElementTree {*}tag wildcard find/findall (Python 3.8+), avoids depending on exact ENTSO-E schema URN version"
    - "DOCTYPE/ENTITY string-prefix guard (_reject_doctype) as a zero-dependency XXE/entity-bomb mitigation instead of adding lxml/defusedxml"
    - "Functional core: all parser/aggregation functions are pure (xml str / DataFrame in, DataFrame out), no I/O — matches 03_MODULES.md functional-core pattern"

key-files:
  created:
    - tests/fixtures/entsoe/prices_pt60m_at.xml
    - tests/fixtures/entsoe/prices_pt15m_at.xml
    - tests/fixtures/entsoe/prices_a03_forward_fill.xml
    - tests/fixtures/entsoe/load_at.xml
    - tests/fixtures/entsoe/gen_at.xml
    - tests/fixtures/entsoe/acknowledgement.xml
    - tests/fixtures/entsoe/dst_spring.xml
    - tests/fixtures/entsoe/dst_fall.xml
    - tests/unit/test_entsoe_parse.py
    - tests/unit/test_aggregate_hourly.py
  modified:
    - src/epra/ingest/entsoe.py
    - tests/fixtures/entsoe/README.md

key-decisions:
  - "Used stdlib xml.etree.ElementTree with a manual DOCTYPE/ENTITY string guard instead of adding defusedxml/lxml as a new dependency (T-02-08/T-02-09 mitigation without a package-install checkpoint)"
  - "Zone derived from XML domain EIC codes via a small static _EIC_TO_ZONE map (AT/DE_LU) rather than injected Settings, keeping parse_publication_xml/parse_gl_xml pure per the pinned 03_MODULES.md signatures"
  - "hourly_mean implemented together with the Task 2 parser code (same module edit) rather than in a separate Task 3 commit — both are small pure functions in the same file; Task 3's dedicated ING-062 test file was still written and committed separately per the plan's fixture requirement"

patterns-established:
  - "A03 forward-fill: walk period positions 1..N, carry last-seen value forward, count fills; raise ContractError if position 1 itself is missing (no seed to fill from)"
  - "period num_positions computed from (timeInterval.end - timeInterval.start) / resolution, not from the max XML position present — required for A03 documents where trailing/omitted positions never appear in the XML at all"

requirements-completed: [REQ-ING-01, ING-031, ING-032, ING-050, ING-051, ING-060, ING-061, ING-062, ING-063]

coverage:
  - id: D1
    description: "parse_publication_xml parses Publication_MarketDocument prices with EUR/MWH assertion, resolution, zone, UTC ts_utc"
    requirement: "ING-050"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_publication_xml_pt60m_columns_and_zone"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_publication_xml_wrong_currency_raises_contract_error"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_publication_xml_wrong_unit_raises_contract_error"
        status: pass
    human_judgment: false
  - id: D2
    description: "A03 curveType forward-fill within a period, with fill count in frame.attrs"
    requirement: "ING-063"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_publication_xml_a03_forward_fill_within_period"
        status: pass
    human_judgment: false
  - id: D3
    description: "Acknowledgement_MarketDocument raises NoDataError (prices and load/generation)"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_publication_xml_acknowledgement_raises_no_data_error"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_gl_xml_acknowledgement_raises_no_data_error"
        status: pass
    human_judgment: false
  - id: D4
    description: "parse_gl_xml load and long-format generation with PSR code/name and aggregated/consumption kind"
    requirement: "ING-032"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_gl_xml_load_columns"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_gl_xml_generation_long_format"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_gl_xml_unknown_psr_code_keeps_row"
        status: pass
    human_judgment: false
  - id: D5
    description: "DST spring/fall days persist as 23/25 distinct UTC hours (parse-boundary UTC conversion correctness)"
    requirement: "ING-031"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_publication_xml_dst_spring_23_hours"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_parse_publication_xml_dst_fall_25_hours"
        status: pass
    human_judgment: false
  - id: D6
    description: "infer_resolution matches declared resolution on PT60M/PT15M fixtures"
    requirement: "ING-060"
    verification:
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_infer_resolution_matches_pt60m_fixture"
        status: pass
      - kind: unit
        ref: "tests/unit/test_entsoe_parse.py#test_infer_resolution_matches_pt15m_fixture"
        status: pass
    human_judgment: false
  - id: D7
    description: "hourly_mean aggregates PT15M quarters by arithmetic mean, never sum, for both price and load column names"
    requirement: "ING-062"
    verification:
      - kind: unit
        ref: "tests/unit/test_aggregate_hourly.py#test_hourly_mean_averages_quarters_not_sum"
        status: pass
      - kind: unit
        ref: "tests/unit/test_aggregate_hourly.py#test_hourly_mean_works_for_load_mw_column_name"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-21
status: complete
---

# Phase 2 Plan 04: ENTSO-E XML Parsers and Hourly Aggregation Summary

**Pure, fixture-tested ENTSO-E Appendix-A XML parsers (prices, load, generation) plus the ING-062 mean-not-sum hourly aggregation helper, built with `xml.etree.ElementTree` and zero new dependencies**

## Performance

- **Duration:** 35 min
- **Started:** 2026-07-21T19:11:00Z
- **Completed:** 2026-07-21T19:46:37Z
- **Tasks:** 3
- **Files modified:** 12 (8 fixtures + README + entsoe.py + 2 test files)

## Accomplishments

- `parse_publication_xml` parses `Publication_MarketDocument` day-ahead prices with hard EUR/MWH assertions (ING-050), declared `resolution` persisted per row (ING-060), A03 forward-fill within a period with a fill counter in `frame.attrs["a03_fills"]` (ING-063), and UTC conversion at the parse boundary via `epra.common.timeutil.to_utc` (ING-031/ING-005)
- `parse_gl_xml` parses `GL_MarketDocument` for both AT actual load (flat) and AT generation per type (ING-032 long format: `psr_type`, `psr_name` from a new `PSR_NAMES` Appendix B table, `kind` = `"aggregated"`/`"consumption"` derived from `businessType`), keeping unknown PSR codes as `UNKNOWN(<code>)` rows rather than dropping them
- Both parsers raise `NoDataError` for `Acknowledgement_MarketDocument` responses and `ContractError` for unexpected root elements or malformed input
- `infer_resolution` provides the ING-060 median-spacing fallback; `iter_chunks` groups `timeutil.iter_month_starts` into quarterly request windows for the 02-05 orchestration plan
- `hourly_mean` implements the ING-061/062 canonical hourly aggregation — explicit `.mean()`, never `.sum()` — reusable across `price_eur_mwh`/`load_mw`/`value_mw`
- 8 committed synthetic XML fixtures matching Appendix A exactly (PT60M/PT15M prices, A03 forward-fill, load, multi-PSR generation, Acknowledgement, DST spring/fall) plus a provenance README
- 22 new unit tests, all passing; full repo suite still at 95% coverage with only the pre-existing, already-documented `test_entsoe_token_fails_fast_when_unset` flake failing (unrelated, out of scope)

## Task Commits

Each task was committed atomically (TDD RED/GREEN for Tasks 2 and 3):

1. **Task 1: Commit XML fixtures and README** - `b4b2fe6` (test)
2. **Task 2: Parser tests and implementation**
   - RED: `3a3107d` (test) - failing tests, `parse_publication_xml`/`parse_gl_xml`/`infer_resolution`/`PSR_NAMES` didn't exist yet
   - GREEN: `94437f1` (feat) - parsers implemented, all 17 tests pass; includes `hourly_mean`/`iter_chunks` in the same module edit
3. **Task 3: ING-062 hourly mean tests and helper** - `b05024c` (test) - dedicated ING-062 fixture set (function already implemented in Task 2's commit; see Deviations)

**Plan metadata:** (this commit, following SUMMARY)

## Files Created/Modified

- `src/epra/ingest/entsoe.py` - parse_publication_xml, parse_gl_xml, infer_resolution, hourly_mean, iter_chunks, PSR_NAMES, XML/A03/zone helpers; orchestration stubs (backfill/ingest_incremental/latest_complete_month/main) unchanged, still NotImplementedError for plan 02-05
- `tests/unit/test_entsoe_parse.py` - 17 tests: price/load/generation parsing, A03 fill, wrong currency/unit, Acknowledgement, DST 23h/25h, infer_resolution, PSR_NAMES
- `tests/unit/test_aggregate_hourly.py` - 5 tests: mean-not-sum guard, full 24h PT15M day, load_mw reuse, hour-floor, PT60M pass-through
- `tests/fixtures/entsoe/*.xml` (8 files) - synthetic, hand-crafted Appendix-A-shaped fixtures
- `tests/fixtures/entsoe/README.md` - provenance and REQ-coverage table per file

## Decisions Made

- **No new XML-security dependency:** used stdlib `xml.etree.ElementTree` with a manual `_reject_doctype` guard (rejects any input containing `<!DOCTYPE` or `<!ENTITY`) instead of adding `defusedxml`/`lxml`. ElementTree's expat backend does not resolve external entities by default, so the residual risk was internal entity expansion ("billion laughs"), which the guard closes without a new package-install checkpoint.
- **Zone from XML, not Settings:** `parse_publication_xml`/`parse_gl_xml` stay pure per their pinned `03_MODULES.md` signatures (`xml -> DataFrame`, no `Settings` argument). Zone is derived from the domain EIC code in the XML itself via a small static `_EIC_TO_ZONE` map; unrecognized EIC codes pass through unchanged (visible for debugging) rather than raising.
- **num_positions from period time span, not max XML position:** required for correct A03 handling — omitted trailing positions never appear in the XML at all, so position count must come from `(end - start) / resolution`, not from the highest `position` value present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect PSR_NAMES count assertion in the test**
- **Found during:** Task 2 GREEN run
- **Issue:** Test asserted `len(PSR_NAMES) == 20`, but SPEC-01 Appendix B lists exactly 18 codes (B01-B06, B09-B20; B07/B08 are not defined)
- **Fix:** Corrected the test assertion to `== 18` with an explanatory comment
- **Files modified:** `tests/unit/test_entsoe_parse.py`
- **Verification:** All 17 parser tests pass
- **Committed in:** `94437f1` (Task 2 GREEN commit)

**2. [Rule 3 - Blocking] Switched pd.Timedelta to stdlib timedelta in test fixtures**
- **Found during:** Task 3 test run
- **Issue:** `pd.Timedelta(minutes=N)` triggers a pandas 2.3.3/numpy 2.5.1 "generic unit" `DeprecationWarning` in this environment on every construction (a pre-existing library-version interaction, reproduced independently of my code), polluting test output (108 warnings)
- **Fix:** Used `datetime.timedelta(minutes=N)` instead when adding offsets to `pd.Timestamp` in `tests/unit/test_aggregate_hourly.py` — identical behavior, no warning
- **Files modified:** `tests/unit/test_aggregate_hourly.py`
- **Verification:** `uv run pytest tests/unit/test_aggregate_hourly.py -x --no-cov` — 5 passed, 0 warnings
- **Committed in:** `b05024c` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking/environment)
**Impact on plan:** Both fixes are test-only corrections; no production behavior changed beyond what the plan specified. No scope creep.

### Sequencing note (not a Rule 1-4 deviation, documented for transparency)

`hourly_mean` was written in the same file edit as Task 2's parser implementation (single `entsoe.py` rewrite) rather than deferred to Task 3's own GREEN commit. This means Task 3's dedicated ING-062 test file (`test_aggregate_hourly.py`) passed immediately on first run — there was no true RED phase for Task 3 specifically, since the implementation already existed from Task 2's commit. The function itself has full behavioral coverage (5 dedicated tests including the exact `[10,20,30,40] -> 25.0` guard the plan requires), and Task 3 was still committed as its own atomic commit adding those tests. See `## TDD Gate Compliance` below.

## TDD Gate Compliance

- Task 2 (`tdd="true"`): RED (`3a3107d`) before GREEN (`94437f1`) — verified via `git log`, RED commit predates GREEN commit, RED run confirmed via `ImportError` before implementation existed.
- Task 3 (`tdd="true"`): a `test` commit (`b05024c`) exists, but no distinct RED failure was observed for `hourly_mean` specifically because it was implemented alongside Task 2 in `94437f1`. This is a plan-execution sequencing choice (both are small pure functions touching the same file), not a correctness gap — `hourly_mean` has 5 dedicated passing tests including the exact ING-062 fixture the plan specifies (`[10,20,30,40]` -> mean `25.0`, asserted `!= 100.0`).

## Issues Encountered

None beyond the two auto-fixed items above.

## User Setup Required

None - no external service configuration required. All tests run against committed fixtures, no network or `ENTSOE_API_TOKEN` needed.

## Next Phase Readiness

- Parser API (`parse_publication_xml`, `parse_gl_xml`, `infer_resolution`, `hourly_mean`, `iter_chunks`, `PSR_NAMES`) is complete, pinned, and fixture-tested — plan 02-05 (orchestration: `backfill`, `ingest_incremental`, `latest_complete_month`, CLI `main`) can import these unchanged and wire them to `_fetch.fetch_entsoe` + `_io.write_month`.
- `iter_chunks` is ready for 02-05's window management but not yet exercised by any test in this plan (no `<behavior>` bullet required it) — 02-05 should add direct coverage when it becomes the caller.
- No blockers. Full suite: 95.15% coverage, only the pre-existing unrelated `test_entsoe_token_fails_fast_when_unset` flake fails (already logged in STATE.md/deferred-items.md, out of scope since 02-02).

## Self-Check: PASSED

All 11 created/modified files verified present on disk (8 XML fixtures,
2 test files, `src/epra/ingest/entsoe.py`); all 4 commit hashes
(`b4b2fe6`, `3a3107d`, `94437f1`, `b05024c`) verified present in `git log`.

---
*Phase: EPRA-02-m1-entso-e-ingestion*
*Completed: 2026-07-21*
