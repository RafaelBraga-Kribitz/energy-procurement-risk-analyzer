---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 07
current_phase_name: m6-strategy-simulator
status: executing
stopped_at: T6.07 forward risk landed; next T6.08 SSOT
last_updated: "2026-09-03T16:00:00Z"
last_activity: 2026-09-03
last_activity_desc: Phase EPRA-07 execute 07-07 forward risk
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 44
  completed_plans: 41
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-21)

**Core value:** Quantify euro cost of wrong procurement (2021–2025) + forward P95 exposure per strategy
**Current focus:** Phase EPRA-07 — m6-strategy-simulator (executing; T6.08 next)

## Current Position

Phase: EPRA-07 (m6-strategy-simulator) — EXECUTING
Plan: 7 of 10
Status: executing 07-07 done; next 07-08
Last activity: 2026-09-03 — T6.07 forward risk

Progress: [██████░░░░] 62% (5/8 phases)

## Performance Metrics

**Velocity:** Not yet tracked (no plans executed)
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase EPRA-02 P01 | 20min | 3 tasks | 9 files |
| Phase EPRA-02 P02 | 20min | 3 tasks | 3 files |
| Phase EPRA-02 P03 | 25min | 3 tasks | 2 files |
| Phase EPRA-02 P04 | 35min | 3 tasks | 12 files |
| Phase EPRA-02 P05 | 30min | 3 tasks | 4 files |
| Phase EPRA-02 P06 | 45min | 3 tasks | 4 files |
| Phase EPRA-02 P07 | 35min | 2 tasks | 6 files |
| Phase EPRA-03 P01 | 15min | 2 tasks | 2 files |
| Phase EPRA-03 P02 | 35min | 2 tasks | 4 files |
| Phase 03 P03 | 45min | 2 tasks | 8 files |
| Phase EPRA-03 P04 | 55min | 3 tasks | 9 files |
| Phase EPRA-03 P05 | 18min | 3 tasks | 9 files |
| Phase EPRA-03 P06 | 15min | 2 tasks | 6 files |
| Phase EPRA-04 P01 | 20min | 3 tasks | 6 files |
| Phase EPRA-04 P02 | 30min | 3 tasks | 12 files |
| Phase EPRA-04 P03 | 15min | 2 tasks | 2 files |
| Phase EPRA-04 P04 | 20min | 3 tasks | 9 files |
| Phase EPRA-04 P05 | 45min | 3 tasks | 6 files |
| Phase EPRA-04 P06 | 35min | 3 tasks | 7 files |
| Phase EPRA-04 P07 | 30min | 2 tasks | 5 files |
| Phase EPRA-04 P08 | 40min | 3 tasks | 3 files |

## Accumulated Context

### Decisions

- ADR-001: Light governance only — no external governance-bootstrap kit (locked)
- ADR-002: Dev typing stubs for mypy --strict (locked)
- SG-01, SG-14: Proposed gap resolutions — adopt ADRs before M1/M3 implementation
- [Phase ?]: ADR-003: EntsoeRawClient transport-only, own Appendix-A parsers (adopts SG-01)
- [Phase ?]: ADR-004: pyarrow>=18,<26 as canonical pandas parquet engine
- [Phase ?]: ADR-005: latest_complete_month = min(AT, DE-LU) prices completeness (adopts SG-02)
- [Phase ?]: write_month derives the ING-004 source column from dataset's prefix before the first underscore (no separate source argument)
- [Phase ?]: Missing ts_utc column raises ContractError; naive/non-UTC or out-of-month ts_utc raises ValueError, per 03_MODULES.md write_month failure semantics
- [Phase ?]: Import EntsoeRawClient from entsoe.entsoe (not the package __init__) to satisfy mypy --strict no_implicit_reexport
- [Phase ?]: Task 3 token fail-fast test patches _fetch.entsoe_token directly instead of monkeypatch.delenv, avoiding the known python-dotenv .env repopulation flake
- [Phase ?]: No new XML-security dependency: xml.etree.ElementTree with a DOCTYPE/ENTITY guard instead of defusedxml/lxml (T-02-08/T-02-09)
- [Phase ?]: Zone derived from XML domain EIC codes (static _EIC_TO_ZONE map), keeping parse_publication_xml/parse_gl_xml pure per pinned 03_MODULES.md signatures
- [Phase ?]: ingest_dataset splits parquet writes by UTC calendar month (matching write_month's own UTC boundary), not Vienna-local month
- [Phase ?]: request_hash reuses _fetch's private _cache_request_url with a placeholder token value (request_hash strips securityToken regardless of value), avoiding a duplicate token read
- [Phase ?]: latest_complete_month implements ADR-005: min(latest complete AT price month, latest complete DE-LU price month), raising NoDataError when nothing ingested yet
- [Phase ?]: ING-080 DST correctness check counts hourly-aggregated rows by local calendar date (not distinct hour-of-day labels) to match timeutil.local_hours_in_day semantics
- [Phase ?]: Gates return passed=False with an explanatory summary on empty input rather than vacuously passing (A-2: no silent skip)
- [Phase ?]: gate_ing_082 fails a year outside the SPEC-01 SS8 table entirely, not just out-of-range -- new years need an ADR-extended table
- [Phase ?]: entsoe_prices_delu fixture hand-built directly in SPEC-01 §7 shape (no committed DE_LU-domain XML source yet) — accepted as threat T-02-15, low severity
- [Phase ?]: Task 2 (live ENTSO-E backfill + validate-ingest) deferred to operator — no ENTSOE_API_TOKEN/live network in this execution; no data fabricated (A-2)
- [Phase ?]: key_column promoted from implicit-only ts_utc anchor to a keyword-only parameter defaulting to ts_utc — additive, no add-alongside module (03-01)
- [Phase ?]: [03-02] Import Austria from holidays.countries.austria (not bare 'import holidays') to satisfy mypy --strict no_implicit_reexport
- [Phase ?]: [03-02] _default_end steps 18 months via timeutil.next_month() loop, not pd.DateOffset, reusing the codebase's month-arithmetic helper
- [Phase ?]: [03-02] calendar.parquet persists as ONE file via _io._dataset_root, not monthly-partitioned and not through _io.write_month
- [Phase ?]: [03-03] ADR-007: GeoSphere discover_station picks station id 30 'Graz Universität/Heinrichstraße' (COMBINED, longest record since 1894, still active) via live discovery — recorded in config/settings.yaml, not a pending human checkpoint
- [Phase ?]: [03-03] GeoSphere /station/historical/klima-v2-1d/metadata returns a flat {"stations": [...]} object, not a GeoJSON FeatureCollection — output_format=geojson applies only to the data endpoint (03-04), confirmed live and documented in geosphere.py + ADR-007
- [Phase ?]: [03-04] gate_ing_094 coverage denominator is calendar days spanned by the data itself (min..max date), never an hours-based constant (RESEARCH Pitfall 6)
- [Phase ?]: [03-04] _fetch_geosphere is a small GeoSphere-scoped transport with its own cache/politeness logic, not forced through _fetch.fetch_entsoe (typed around EntsoeQuery/EntsoeRawClient, ADR-003)
- [Phase ?]: [03-04] geosphere_graz_daily_2024-01.parquet fixture generated via the real parse_geojson+write_month path against klima_2019-01.geojson, with dates remapped 2019->2024 only to follow the repo's <dataset>_2024-01.parquet naming convention
- [Phase ?]: [03-05] ADR-008 pins the AEA continuously-published strompreisindex page as the sole 2019-latest OSPI transcription source, pending human confirmation at T2.05 (D-01/D-04)
- [Phase ?]: [03-05] load_oespi's peak_available signal lives in frame.attrs (not a second return value or column); gate_ing_103's crisis/MoM checks use oespi_base only so behavior is identical under the ING-104 base-only fallback
- [Phase ?]: [03-06] gate_ing_111 is a thin wrapper reusing the 03-02 calendar assertions verbatim; a missing real ÖSPI CSV degrades run_gates' ING-103 to a non-crashing informational PASS (D-06)
- [Phase ?]: [03-06] ÖSPI double-entry reconciliation (ING-101) deliberately deferred past this close-out -- entry1/entry2 CSVs unreconciled; documented in LIMITATIONS.md sec 6 + deferred-items.md, REQ-ING-01 closure left to phase verification
- [Phase ?]: ADR-009: generate_schema_name omits default_schema prefix so DuckDB schemas are literally staging/marts (single-operator local warehouse, DM-003/SG-13)
- [Phase ?]: sources.yml exposes all 9 raw/manual/processed datasets via a single ../data/-prefixed read_parquet/read_csv glob each (DM-004), zero direct file access from later models
- [Phase ?]: month_spine and accepted_range macros hand-rolled on DuckDB native generate_series -- no dbt_utils/packages.yml added (ADR-001 lean-repo)
- [Phase ?]: [04-02] Rule 1 bug fix: dbt/profiles.yml pins settings.TimeZone=UTC -- DuckDB's default session TimeZone is the host OS local zone, so date_trunc('hour', ts_utc) on TIMESTAMPTZ silently truncated to Vienna-local hour boundaries, not UTC (caught via DST-transition n_subhours=8 anomaly)
- [Phase ?]: [04-02] Rule 3: hand-rolled dbt/macros/test_unique_combination_of_columns.sql (zero dbt_utils dependency, ADR-001) for stg_gen_at_hourly's composite [ts_utc, psr_type] grain key
- [Phase ?]: [04-03] No deviations — dim_calendar builds exactly per SPEC-02 §4 with zero timezone-conversion calls; DST edge hours (23/25) and dim_calendar.ts_utc/dim_strategy.strategy_id uniqueness verified on real data
- [Phase ?]: [04-04] ADR-011: exactly one holiday-aware is_peak_hour (dim_calendar) drives price_peak_eur_mwh everywhere; NULL (not 0) on no-peak days -- verified on real Austrian holiday dates
- [Phase ?]: [04-04] fct_price_daily sources tavg_c via direct join to stg_weather_graz_daily (dim_calendar only carries derived hdd_18/cdd_22, not raw temperature)
- [Phase ?]: [04-04] Rule 1: nested new facts_price.yml generic-test args under dbt 1.12's arguments: property to fix MissingArgumentsPropertyInGenericTestDeprecation; pre-existing staging.yml occurrence logged to deferred-items.md (out of scope)
- [Phase ?]: [04-05] D-04/ADR-010: generator synthesizes every raw/processed row programmatically (seeded numpy RNG), never copies committed fixture parquet -- a capped ~200-row sample cannot satisfy DM-062/DM-065 over a full multi-year window
- [Phase ?]: [04-05] D-06 extension: added a --processed-only CLI mode (writes only data/processed, discovers the real local window from calendar.parquet, never touches data/raw/data/manual) -- used to safely verify Task 3 against this repo's real 2019-2024 ingested data, since --force would have overwritten real raw parquet
- [Phase ?]: [04-05] fct_consumer_load_hourly/fct_procurement_cost_monthly are thin never-disabled loaders over source('raw_processed', ...) (SG-06); DM-063 relationships test (strategy_id -> dim_strategy) green
- [Phase ?]: [04-06] DM-062 row-count test scoped to calendar-complete years (min/max date_local = local Jan-1/Dec-31) so dim_calendar's intentional forward-risk-horizon boundary artifact (a lone year_local=2028, 1-row edge) doesn't trip a false anomaly, mirroring ADR-006's complete-years-within-window convention; no-op for the fully-bounded CI fixture window
- [Phase ?]: [04-06] marts_contract.yml is a flat mart-name-keyed mapping (no version/wrapper key) so test_marts_contract.py can parametrize via sorted(contract) directly; fct_procurement_cost_monthly.year_local/month_local captured as BIGINT (not INTEGER) since that mart loads straight off the processed stand-in parquet, not a dim_calendar join
- [Phase ?]: [04-07] D-02 build-report writer (ModelBuildResult/BuildReport, GateResult/ValidationReport reuse) queries the marts schema read-only for DM-062/DM-050/DM-064 sanity numbers without re-implementing the 04-06 dbt tests' boundary logic -- purely presentation, not re-gating
- [Phase ?]: [04-07] make transform un-stubbed to cd dbt && dbt build; make warehouse composes transform + python -m epra.warehouse.report, mirroring the ingest -> validate-ingest two-step Makefile convention
- [Phase 04-08]: dbt-check is a separate EN-080 job 3 (bootstrap --force then dbt build then D-07 pytest); never folded into test:
- [Phase 04-08]: SC#3 proven in an isolated --data-root so --force cannot clobber committed oespi_monthly.csv
- [Phase 04-08]: TP.02 (mark dbt-check required on main) remains operator GitHub settings — not auto-approved
- [Phase 05 discuss]: D-01 calendar_df is ING-110 spine (not dim_calendar); D-02 ADR-012 SG-04 first-Monday-on-or-after-Aug-1; D-04 ADR-013 2019 peak share; D-06 flat_baseload same function no second YAML; D-08 single LP-003 parquet + sources.yml + all: profile then transform
- [Phase 05-01]: ADR-012 SG-04 first Monday on or after 1 August; vectorized hourly_weights; YAML numerics stay in config
- [Phase 05-02]: LP-004/LP-034 normalize via full-year Σw from build_calendar; build_profile returns ts_utc, load_mwh
- [Phase 05-03]: ADR-013 2019 peak share (~0.486, near-band not YAML-retuned); D-08 single-file consumer parquet
- [Phase 05-04]: LP-040 golden tests/golden/consumer_load_2023.sha256; flat_baseload via profile_name
- [Phase 05-05]: CLI + Makefile profile; all: profile then transform; warehouse stand-in = procurement only; LP-051 confirmed
- [Phase 06 discuss]: D-01 marts-only + pure functions; D-03 ssot_inputs_analytics.parquet; D-06 AN-304 skip-if-incomplete fixture; D-09 BLAS pin; no fixture PNGs committed
- [Phase 06-01]: kit loaders/PNG/SSOT + CLI missing-warehouse exit 1
- [Phase 06-02]: A1 annual_summary/heatmap/duration/negatives; SSOT upsert by key; NULL prices dropped
- [Phase 06-03]: A2 spread_stats on one hourly frame; axhline(0); spread_mean_<year>
- [Phase 06-04]: A4 month-FE HC1 load~HDD; consumer weather-invariant sentence
- [Phase 06-05]: A3 HMM seeds 42-51; AN-304 skip-if-incomplete; december_regime
- [Phase 06-06]: GARCH(1,1) overlay; garch_persistence VERIFIED; no clamp
- [Phase 06-07]: make analyze; AN-701/705 tests; BUILD_LOG M5
- [Phase 07 discuss]: D-01 shared ST-101 aligner; D-02 w_peak from profile parquet; D-03 simulate = retro+forward no dbt; D-05 dual-write parquet; D-06 skip-if-incomplete 2019; D-07 ST-406 cells day one; D-10..11 ADR-014/015; D-12 reuse M5 december_regime (calm wins); D-19 synthetic ST-601 golden
- [Phase 07 research]: ÖSPI from fct_price_monthly; data_last_month from marts not raw; int64 year for BIGINT contract; ssot-check skips GV-302 if NUMERIC_SSOT.md absent (D-04); Decimal ROUND_HALF_UP; emit oespi_peak_ref
- [Phase 07 plan]: 10 execute-plans T6.01–T6.10; ADRs 014–016 at T6.07/T6.08; synthetic ST-601 at T6.10
- [Phase 07-01]: ST-101 aligner + w_peak from profile parquet; 6 unit tests green
- [Phase 07-02]: ST-201..204 anchors; synthetic p_ref_base=70; IncompleteReferenceYearError
- [Phase 07-03]: cost_s1 monthly FULL_SPOT; hand month 50 EUR / 3 MWh
- [Phase 07-07]: ST-406 cells; ADR-014/015; simulate path-major; ST-602(c); no-crisis december_regime

### Pending Todos

- Execute 07-08..07-10 (one PR each) then GSD verify-work
- AN-304 / ST-602(a) on real warehouse (operator)
- TP.02: mark GitHub `dbt-check` and later `ssot-check` required on `main` (operator)
- EN-072: human approval before regenerating consumer golden or replacing synthetic strategy golden with real euros

### Blockers/Concerns

- ~~ENTSO-E API token required for M1 backfill (human-owned)~~ — RESOLVED 2026-07-21: `ENTSOE_API_TOKEN` present in `.env`
- INGEST-CONFLICTS: 2 warnings on SG-01/SG-14 — not blockers; resolve via ADR at implementation
- ~~test_config.py::test_entsoe_token_fails_fast_when_unset fails (.env token repopulated by load_dotenv)~~ — RESOLVED 2026-07-22: test now stubs load_dotenv to isolate from real .env (commit dc14314)
- ~~M1 live-data gate pending operator~~ — DONE 2026-07-22. Live backfill run on real ENTSO-E (token in .env); found + fixed two data-loss bugs (100-doc response cap → pagination; chunk-boundary month overwrite → accumulate-then-write) and one domain bug (gates bucketed by UTC year → ADR-006 scopes them to complete Vienna-local years). `make validate-ingest` now exits 0 — ALL GATES PASSED (ING-080..085) on real 2019→2024-01 data. All three ROADMAP Phase 2 criteria met; M1 complete. See docs/BUILD_LOG.md 2026-07-22 entry.
- ÖSPI double-entry reconciliation pending: data/manual/oespi_monthly_entry1.csv + entry2.csv exist unreconciled; ING-103 soft-passes informationally (D-06). Resolve via uv run python scripts/oespi_reconcile.py, delete entry files, re-run make validate-ingest. See LIMITATIONS.md sec 6.

## Deferred Verification

| Phase | State | Resume |
|-------|-------|--------|
| *(none)* | | |

Phase 2 fully verified 2026-07-22: 178 tests + lint/mypy clean, code review clean, live backfill run on real ENTSO-E, and `make validate-ingest` exits 0 (ALL GATES PASSED). All three ROADMAP Phase 2 criteria met — no open items.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-09-03T12:00:00Z
Stopped at: T6.05 annual summary landed
Resume file: None
Also: .planning/CONTINUITY.md, .planning/graphs/GRAPH_REPORT.md
Next: execute 07-08-PLAN.md (T6.08 SSOT generator + ADR-016)
