# Graph Report - energy-procurement-risk-analyzer  (2026-09-30)

## Corpus Check
- 239 files · ~466,972 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 43 file(s) not represented in the graph (top: (none) 24, .xml 8, .parquet 5)

## Summary
- 2520 nodes · 4598 edges · 186 communities (156 shown, 30 thin omitted)
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 1094 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cdd94c43`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).
- Regenerated 2026-09-30 with `graphify update .` (graphifyy CLI) on a clean checkout of `cdd94c43`;
  dbt `.sql` files are NOT represented (optional `tree_sitter_sql` dependency was not installed).
- `graph.json` / `graph.html` are no longer committed (generated locally by the GSD graphify hooks).

## Community Hubs (Navigation)
- Communities (142 total, 18 thin omitted)
- entsoe.py
- _read
- Phase 2: M1 ENTSO-E Ingestion - Research
- test_io.py
- Summary
- Synthesized Constraints (SPECs)
- Shared Patterns
- timeutil.py
- test_fetch.py
- run_gates
- test_fetch_entsoe_cache_tmp_path_is_per_call_unique
- Specification gaps tracker (14_SPEC_GAPS)
- _year_hourly
- test_raw_contracts.py
- test_ingest_gates.py
- 05 — IMPLEMENTATION GUIDES (the "how", per milestone)
- write_month
- 00_MASTER_PLAN.md
- fetch_entsoe
- bootstrap_fixture_warehouse.py
- Phase EPRA-02 Plan 07: M1 Close-Out (Contract Tests, Fixtures, BUILD_LOG) Summary
- Implementation Decisions
- SPEC-01 — Data Ingestion
- SPEC-05 — Procurement Strategy Simulator
- Phase EPRA-02 Plan 01: Wave 0 Architecture Decisions Summary
- request_hash
- iter_month_starts
- 03 — MODULE, CLASS, AND FUNCTION CONTRACTS
- latest_complete_month
- Phase Details
- M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2
- SPEC-07 — Engineering, Tooling, CI/CD
- PROJECT CHARTER — Energy Procurement Risk Analyzer (EPRA)
- ConsumerProfileCfg
- config.py
- SPEC-03 — Consumer Load Profile ("StyriaMetal GmbH")
- Goal Achievement
- Project State
- hourly_mean
- 01 — PHASES: Roadmap, entry/exit criteria, rollback
- M6 — Strategies (SPEC-05) — the heart; sequence is mandatory
- SPEC-02 — Data Model (DuckDB + dbt)
- Codebase Concerns
- Graph Report - energy-procurement-risk-analyzer  (2026-07-22)
- write-session-snap.js
- Doc Ingest Synthesis Summary
- Energy Procurement Risk Analyzer (EPRA)
- build_profile
- test_scripts.py
- 00 — MASTER PLAN: The Execution Operating System
- Naming Patterns
- Testing Patterns
- ModelBuildResult
- Requirements: Energy Procurement Risk Analyzer (EPRA)
- format.py
- 3. Build order and gates (from Charter §7 — expanded into agent tasks)
- 07 — QUALITY STANDARDS (measurable thresholds)
- SPEC-04 — Market Analytics (modules A1–A4)
- SPEC-06 — Reporting, Dashboard, README
- Phase 4: M3 dbt Warehouse - Research
- External Integrations
- Phase 1: M0 Bootstrap Verification Report
- CR-01: `iter_chunks` groups 3 raw calendar months without bounding the window to ING-030's 90-day maximum
- load_strategy_config
- ingest
- M3 — dbt warehouse (SPEC-02)
- M5 — Analytics (SPEC-04) — order A1→A2→A4→A3
- M7 — Reporting, dashboard, refresh, release (SPEC-06, SPEC-07 §8)
- 06 — CHECKLISTS
- SPEC-08 — Governance & Quality (deliberately lightweight)
- connect
- LIMITATIONS
- Technology Stack
- setup
- discover_station
- Phase 2 — Validation Strategy
- Ingestion validation report — 2026-07-22
- AGENTS.md — Build Playbook for AI Agents
- M2 — Auxiliary data (SPEC-01 §§9–11) — merge FIRST (R-1)
- 04 — DEPENDENCY GRAPHS, CRITICAL PATH, PARALLELISM
- Claude Code ↔ Cursor Continuity
- test_geosphere.py
- Onboarding Summary
- 02-UAT.md
- Energy Procurement Risk Analyzer (EPRA)
- oespi_reconcile.py
- gate_ing_111
- geosphere.py
- build_calendar
- ContractError
- _last_sunday
- ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored
- ADR-002: Dev-only typing-stub packages for mypy --strict
- ADR-003: EntsoeRawClient as transport; own Appendix-A parsers (adopts SG-01)
- ADR-004: pyarrow as the pandas parquet engine for ingestion I/O
- test_bootstrap_fixture_warehouse.py
- parse_publication_xml
- Phase 3: M2 Auxiliary Data - Research
- M4 — Consumer profile (SPEC-03)
- Phase 1: M0 Bootstrap Summary
- _ensure_entsoe_fixtures_dir
- check_no_token_in_code.py
- parse_geojson
- Phase 4: M3 dbt Warehouse - Context
- forward_risk.py
- Key Abstractions
- 10 — VALIDATION GATES: the no-progression ladder
- 11 — ACCEPTANCE CRITERIA (objective, runnable)
- 13 — TRACEABILITY MATRIX
- Conflict Detection Report
- Phase 1 (M0 Bootstrap) — Plan 01: Repo, tooling, CI, pipeline skeleton
- test_entsoe_token_fails_fast_when_unset
- Phase 3: M2 Auxiliary Data - Context
- 02 — WORK BREAKDOWN STRUCTURE
- Synthesized Decisions (ADRs)
- MonkeyPatch
- test_calendar.py
- Settings
- _fetch.py
- Phase EPRA-04 Plan 02: Staging Models (8 views) Summary
- Phase EPRA-04 Plan 04: Price/Generation Marts (fct_price_hourly/daily/monthly, fct_generation_monthly) Summary
- 02-01-PLAN.md
- 02-02-PLAN.md
- 02-03-PLAN.md
- 02-04-PLAN.md
- 02-05-PLAN.md
- 02-06-PLAN.md
- 02-07-PLAN.md
- ENTSO-E test fixtures
- dashboards/README.md
- dbt/README.md
- is_peak_hour
- requirements.md
- Phase EPRA-04 Plan 05: Fixture/Stand-in Generator + Future Marts (D-04, SG-06) Summary
- Phase EPRA-04 Plan 06: DM-050/062/064/065/066 Test Suite + D-07 Schema Contract Summary
- test_entsoe_orchestration.py
- epra
- _validate_date_key
- Phase EPRA-04 Plan 01: dbt Foundation — Schema Macro, Sources, Helper Macros Summary
- Phase EPRA-04 Plan 03: dim_calendar + dims.yml (DM-060) Summary
- Phase EPRA-04 Plan 07: D-02 Build-Report Writer + Makefile Operator Interface Summary
- Phase EPRA-04 Plan 08: CI dbt-check Job + M3 Close-Out Summary
- Ingestion validation report — 2026-07-23
- test_stubs_fail_loudly.py
- Phase EPRA-03 Plan 01: write_month key_column dispatcher Summary
- Phase EPRA-03 Plan 02: Calendar hourly spine (ING-110/111) Summary
- Shared Patterns
- test_marts_contract.py
- Phase 3: M2 Auxiliary Data - Discussion Log
- Phase 3 — Validation Strategy
- Phase 4: M3 dbt Warehouse - Discussion Log
- Phase 4 — Validation Strategy
- 5.1 M1 — ENTSO-E
- Project Audit — 2026-09-30 (findings only, nothing fixed)
- Pattern Assignments
- Common Pitfalls
- ADR-009: `generate_schema_name` override — literal `staging`/`marts` schemas
- ADR-010: CI fixture bootstrap synthesizes data at run time; environment-aligned data/processed stand-ins feed the local build too
- DiscoveryError
- dbt build report — 2026-07-24
- test_ingest_dataset_pages_past_100_document_cap
- Architecture Patterns
- Code Examples
- _fake_token
- test_discover_station_live_reaches_geosphere
- 04-01-PLAN.md
- 04-02-PLAN.md
- 04-03-PLAN.md
- 04-05-PLAN.md
- 04-06-PLAN.md
- 04-08-PLAN.md
- _marts_schema_populated
- Standard Stack
- Deferred Items — EPRA-04 M3 dbt Warehouse
- test_missing_data_root_argument_value_is_a_usage_error
- test_calendar_main_writes_single_parquet_file
- COVERAGE.md
- EPRA-03-m2-auxiliary-data/deferred-items.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 161 edges
2. `Communities (142 total, 18 thin omitted)` - 124 edges
3. `write_month()` - 69 edges
4. `ContractError` - 68 edges
5. `fetch_entsoe()` - 51 edges
6. `EntsoeQuery` - 47 edges
7. `run_gates()` - 45 edges
8. `ingest()` - 44 edges
9. `load_settings()` - 43 edges
10. `latest_complete_month()` - 43 edges

## Surprising Connections (you probably didn't know these)
- `Community 66 - "conftest.py"` --references--> `Settings`  [INFERRED]
  .planning/graphs/GRAPH_REPORT.md → src/epra/common/config.py
- `Configuration injection` --references--> `Settings`  [INFERRED]
  .planning/phases/EPRA-02-m1-entso-e-ingestion/02-PATTERNS.md → src/epra/common/config.py
- `Applicable ASVS Categories` --references--> `Settings`  [INFERRED]
  .planning/phases/EPRA-03-m2-auxiliary-data/03-RESEARCH.md → src/epra/common/config.py
- `T4.01 — Weight engine (algorithm steps 1–4) `[CP]`` --references--> `ConsumerProfileCfg`  [INFERRED]
  docs/EXECUTION_BLUEPRINT/02_WBS.md → src/epra/common/config.py
- `Don't Hand-Roll` --references--> `load_settings()`  [INFERRED]
  .planning/phases/EPRA-02-m1-entso-e-ingestion/02-RESEARCH.md → src/epra/common/config.py

## Import Cycles
- None detected.

## Communities (186 total, 30 thin omitted)

### Community 0 - "Communities (142 total, 18 thin omitted)"
Cohesion: 0.02
Nodes (121): Communities (142 total, 18 thin omitted), Community 0 - "Communities (137 total, 18 thin omitted)", Community 100 - "M4 — Consumer profile (SPEC-03)", Community 101 - "Phase 1: M0 Bootstrap Summary", Community 102 - "Info", Community 103 - "check_file", Community 104 - "ingest_dataset", Community 105 - "style.py" (+113 more)

### Community 1 - "entsoe.py"
Cohesion: 0.14
Nodes (16): Decisions Made, _acknowledgement_reason(), _apply_a03_fill(), _child(), _children(), _extract_points(), _local_name(), _parse_document() (+8 more)

### Community 2 - "_read"
Cohesion: 0.21
Nodes (10): _read(), test_backfill_writes_real_files_for_all_datasets(), test_ingest_dataset_contract_error_leaves_no_partial_file(), test_ingest_dataset_generation_dataset_key(), test_ingest_dataset_load_dataset_key(), test_ingest_dataset_logs_a03_fill_count(), test_ingest_dataset_maps_delu_zone(), test_ingest_dataset_no_data_window_is_skipped_not_raised() (+2 more)

### Community 3 - "Phase 2: M1 ENTSO-E Ingestion - Research"
Cohesion: 0.05
Nodes (43): Alternatives Considered, Anti-Patterns to Avoid, Applicable ASVS Categories, Architectural Responsibility Map, Architecture Patterns, Assumptions Log, Atomic monthly parquet write (ING-003), Cache key without token (ING-009) (+35 more)

### Community 4 - "test_io.py"
Cohesion: 0.07
Nodes (20): Task Commits, _geosphere_daily_frame(), _prices_frame(), test_raw_month_path_matches_spec01_section7_layout(), test_raw_month_path_rejects_path_traversal_dataset(), test_write_month_atomic_write_with_contract_columns(), test_write_month_date_key_applies_no_timezone_assertion(), test_write_month_date_key_happy_path() (+12 more)

### Community 5 - "Summary"
Cohesion: 0.12
Nodes (16): epra.ingest._fetch (new, internal — created by T1.02), Surprising Connections (you probably didn't know these), Accomplishments, `src/epra/ingest/exceptions.py` (utility), CR-02: Error-detail fallback can leak the real `securityToken` via `str(exc)` when the HTTP error response has no body, Summary, IngestAuthError, IngestError (+8 more)

### Community 6 - "Synthesized Constraints (SPECs)"
Cohesion: 0.07
Nodes (27): SPEC-01: ENTSO-E client and fetch, SPEC-01: General ingestion rules, SPEC-01: Raw output contracts, SPEC-01: Resolution handling, SPEC-01: Validation gates, SPEC-01: Window management, SPEC-02: dbt tests, SPEC-02: Dimension contracts (+19 more)

### Community 7 - "Shared Patterns"
Cohesion: 0.15
Nodes (12): CLI `main` contract, Configuration injection, Contract tests, File Classification, Logging, Metadata, No Analog Found, Phase 2: M1 ENTSO-E Ingestion — Pattern Map (+4 more)

### Community 8 - "timeutil.py"
Cohesion: 0.23
Nodes (6): Reusable Assets, Anti-Patterns to Avoid, to_local(), to_utc(), test_naive_datetimes_are_rejected(), test_utc_local_round_trip()

### Community 9 - "test_fetch.py"
Cohesion: 0.08
Nodes (30): _http_error(), _old_window(), _query(), test_entsoe_query_accepts_exactly_90_day_window(), test_entsoe_query_accepts_valid_window(), test_entsoe_query_is_frozen(), test_entsoe_query_rejects_end_before_start(), test_entsoe_query_rejects_equal_start_and_end() (+22 more)

### Community 10 - "run_gates"
Cohesion: 0.06
Nodes (46): Consequences, T1.09 — Validation gates ING-080..085 + report writer `[CP]`, epra.ingest.validate (T1.09, T2.03, T2.04), 4. P2 — Code hygiene / debt, Community 10 - "run_gates", Accomplishments, Auto-fixed Issues, Decisions Made (+38 more)

### Community 11 - "test_fetch_entsoe_cache_tmp_path_is_per_call_unique"
Cohesion: 0.20
Nodes (4): WR-02: Cache and parquet-writer temp files are not process-unique — concurrent runs can race on the same `.tmp` path, _fake_token(), _sleep_calls(), test_fetch_entsoe_cache_tmp_path_is_per_call_unique()

### Community 12 - "Specification gaps tracker (14_SPEC_GAPS)"
Cohesion: 0.09
Nodes (21): Authority note, SG-01 (proposed), SG-02 (proposed), SG-03 (proposed), SG-04 (proposed), SG-05 (proposed), SG-06 (proposed), SG-07 (proposed) (+13 more)

### Community 13 - "_year_hourly"
Cohesion: 0.09
Nodes (25): Functional core / imperative shell, _complete_local_years(), gate_ing_080(), gate_ing_081(), gate_ing_082(), gate_ing_083(), gate_ing_084(), gate_ing_085() (+17 more)

### Community 14 - "test_raw_contracts.py"
Cohesion: 0.13
Nodes (11): _fixture_path(), test_entsoe_gen_at_dtypes_match_spec01_section7(), test_entsoe_load_at_dtypes_match_spec01_section7(), test_entsoe_prices_at_dtypes_match_spec01_section7(), test_entsoe_prices_delu_dtypes_match_spec01_section7(), test_fixture_committed_and_bounded(), test_fixture_exact_column_layout(), test_fixture_provenance_columns_present_and_typed() (+3 more)

### Community 15 - "test_ingest_gates.py"
Cohesion: 0.08
Nodes (31): Deviations from Plan, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-03 Plan 04: GeoSphere Daily Temperature Ingest Summary, Self-Check: PASSED, Task Commits, User Setup Required (+23 more)

### Community 16 - "05 — IMPLEMENTATION GUIDES (the "how", per milestone)"
Cohesion: 0.17
Nodes (12): 05 — IMPLEMENTATION GUIDES (the "how", per milestone), 5.2 M2 — Auxiliary data, 5.3 M3 — dbt warehouse, 5.4 M4 — Consumer profile, 5.5 M5 — Analytics, 5.6 M6 — Strategies, 5.7 M7 — Reporting & release, Anchor identity checks (cheap unit tests that catch T-5 dead) (+4 more)

### Community 17 - "write_month"
Cohesion: 0.13
Nodes (15): Files Created/Modified, Next Phase Readiness, Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries, Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries (+7 more)

### Community 19 - "fetch_entsoe"
Cohesion: 0.12
Nodes (18): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Performance, Phase 2 Plan 3: ENTSO-E HTTP Transport (_fetch) Summary, Self-Check: PASSED (+10 more)

### Community 20 - "bootstrap_fixture_warehouse.py"
Cohesion: 0.11
Nodes (19): _atomic_write_csv(), _atomic_write_parquet(), _build_calendar(), _build_consumer_load_hourly(), _build_gen(), _build_geosphere(), _build_load(), _build_oespi_rows() (+11 more)

### Community 21 - "Phase EPRA-02 Plan 07: M1 Close-Out (Contract Tests, Fixtures, BUILD_LOG) Summary"
Cohesion: 0.15
Nodes (12): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance (+4 more)

### Community 22 - "Implementation Decisions"
Cohesion: 0.14
Nodes (13): Claude's Discretion, Client & Transport (ADR-003 adopts SG-01), Deferred Ideas, Established Patterns, Existing Code Insights, Implementation Decisions, Parquet I/O (ADR-004), Phase 2: M1 ENTSO-E Ingestion - Context (+5 more)

### Community 23 - "SPEC-01 — Data Ingestion"
Cohesion: 0.14
Nodes (14): 10. ÖSPI (manual, double-entry validated), 11. Calendar, 1. General ingestion rules (apply to every source), 2. ENTSO-E: registration and authentication, 3. ENTSO-E: what to fetch, 4. ENTSO-E: window management & incremental refresh, 5. Units and currencies, 6. Resolution handling (CRITICAL — R-2, R-3) (+6 more)

### Community 24 - "SPEC-05 — Procurement Strategy Simulator"
Cohesion: 0.14
Nodes (14): 1. Scope of the decision being modeled, 2. Architecture, 3. Strategy definitions (families S1–S4; grid in dim_strategy, SPEC-02 §4), 4. Calibration anchors, 5. Retrospective engine (Q1), 6. Forward risk engine (Q3) — seasonal block bootstrap, 7. Fair-comparison and honesty rules, 8. `config/strategies.yaml` (authoritative copy) (+6 more)

### Community 25 - "Phase EPRA-02 Plan 01: Wave 0 Architecture Decisions Summary"
Cohesion: 0.16
Nodes (12): Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-02 Plan 01: Wave 0 Architecture Decisions Summary, Self-Check: PASSED (+4 more)

### Community 26 - "request_hash"
Cohesion: 0.17
Nodes (11): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Issues Encountered, Performance, Phase EPRA-02 Plan 02: Raw Parquet Writer (`_io`) Summary, Self-Check: PASSED (+3 more)

### Community 27 - "iter_month_starts"
Cohesion: 0.09
Nodes (20): epra.ingest.entsoe (T1.04–T1.08), Community 63 - "Fixed Issues", Accomplishments, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase 2 Plan 04: ENTSO-E XML Parsers and Hourly Aggregation Summary (+12 more)

### Community 28 - "03 — MODULE, CLASS, AND FUNCTION CONTRACTS"
Cohesion: 0.20
Nodes (10): 03 — MODULE, CLASS, AND FUNCTION CONTRACTS, epra.analytics.* (T5.01–T5.07), epra.common (implemented — extension notes only), epra.consumer.profile (T4.01–T4.04), epra.ingest.calendar (T2.01), epra.ingest._io (new, internal — created by T1.01), epra.ingest.oespi (T2.04), epra.report.* (charts: T7.02; format/style: done) (+2 more)

### Community 29 - "latest_complete_month"
Cohesion: 0.07
Nodes (37): ADR-005: latest_complete_month() = min(AT prices, DE-LU prices) (adopts SG-02), Consequences, Context, Decision, Spec deviations, 2026-07-21 — M1 ENTSO-E Ingestion (automated deliverables complete; live-data gate pending operator), T1.08 — Window management + CLI + Makefile `[CP]`, Suggested Questions (+29 more)

### Community 30 - "Phase Details"
Cohesion: 0.14
Nodes (13): Overview, Phase 1: M0 Bootstrap, Phase 2: M1 ENTSO-E Ingestion, Phase 3: M2 Auxiliary Data, Phase 4: M3 dbt Warehouse, Phase 5: M4 Consumer Profile, Phase 6: M5 Analytics, Phase 7: M6 Strategy Simulator (+5 more)

### Community 31 - "M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2"
Cohesion: 0.18
Nodes (11): M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2, T1.01 — Raw parquet writer + ING-004 metadata columns `[PAR]` `[CP]`, T1.02 — Fetch layer: cached raw client + retry + politeness `[PAR]` `[CP]`, T1.03a — Handcrafted parser fixtures (pre-token) `[PAR]`, T1.03b — Real-excerpt fixture refresh `[TOKEN]`, T1.04 — Price ingestion AT + DE-LU `[CP]`, T1.05 — Load ingestion AT `[PAR]`, T1.06 — Generation ingestion AT (long format) `[PAR]` (+3 more)

### Community 32 - "SPEC-07 — Engineering, Tooling, CI/CD"
Cohesion: 0.17
Nodes (11): 1. Toolchain, 2. Repository layout (create exactly this; empty dirs get `.gitkeep`), 3. Dependencies (pin these in `pyproject.toml`; upgrades require ADR), 4. Configuration & secrets, 5. Makefile (canonical interface; targets and their meaning), 7. Testing policy, 8. GitHub Actions, 9. Git conventions (+3 more)

### Community 33 - "PROJECT CHARTER — Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.12
Nodes (17): 10. Glossary, 11. Charter change log, 1.1 The four analytical questions (Q1–Q4), 1.2 The audience, 1. The business problem (read this first), 2. The reference consumer ("StyriaMetal GmbH"), 3. Data sources (all real; no synthetic market data — ever), 4.1 In scope (+9 more)

### Community 34 - "ConsumerProfileCfg"
Cohesion: 0.17
Nodes (9): ConsumerProfileCfg, _profile_dict(), test_consumer_profile_matches_spec03(), test_day_shape_validator_rejects_missing_shape(), test_day_shape_validator_rejects_wrong_length(), test_seasonal_validator_requires_all_12_months(), test_settings_window_and_ingest_params(), test_settings_zones_match_spec01_appendix_a() (+1 more)

### Community 35 - "config.py"
Cohesion: 0.22
Nodes (10): `src/epra/common/config.py` (config — extend only if needed), ChristmasShutdownCfg, ForwardCfg, _Frozen, GeosphereCfg, IngestCfg, MaintenanceCfg, PathsCfg (+2 more)

### Community 36 - "SPEC-03 — Consumer Load Profile ("StyriaMetal GmbH")"
Cohesion: 0.15
Nodes (12): 1. Principles, 2. Construction algorithm (implement exactly in this order), 3.1 Day shapes (24 values each, index = hour_local 0–23), 3.2 Seasonal factors by month (mild winter uplift — process heat + lighting), 3.3 Special windows (recur every year), 3. Parameters (the values; also encoded in §6 YAML — YAML wins if they ever diverge), 4. Derived facts the rest of the project relies on, 5. Sensitivity variant (cheap, mandatory) (+4 more)

### Community 37 - "Goal Achievement"
Cohesion: 0.20
Nodes (9): Anti-Patterns Found, Behavioral Spot-Checks, Code Review Cycle, Gaps Summary, Goal Achievement, Human Verification Required, Observable Truths (ROADMAP Success Criteria), Phase 2 (EPRA-02): M1 ENTSO-E Ingestion Verification Report (+1 more)

### Community 38 - "Project State"
Cohesion: 0.17
Nodes (11): Accumulated Context, Blockers/Concerns, Current Position, Decisions, Deferred Items, Deferred Verification, Pending Todos, Performance Metrics (+3 more)

### Community 39 - "hourly_mean"
Cohesion: 0.19
Nodes (11): Community 39 - "hourly_mean", Auto-fixed Issues, Deviations from Plan, Sequencing note (not a Rule 1-4 deviation, documented for transparency), hourly_mean(), _pt15m_hour(), test_hourly_mean_averages_quarters_not_sum(), test_hourly_mean_floors_ts_utc_to_the_hour() (+3 more)

### Community 40 - "01 — PHASES: Roadmap, entry/exit criteria, rollback"
Cohesion: 0.18
Nodes (11): 01 — PHASES: Roadmap, entry/exit criteria, rollback, Phase 0 — Repository foundation (M0) — **DONE 2026-07-19**, Phase 1 — Auxiliary data (M2) — merge FIRST, Phase 2 — Core ingestion (M1), Phase 3 — Warehouse (M3), Phase 4 — Consumer profile (M4), Phase 5 — Analytics (M5), Phase 6 — Strategies (M6) (+3 more)

### Community 41 - "M6 — Strategies (SPEC-05) — the heart; sequence is mandatory"
Cohesion: 0.18
Nodes (11): M6 — Strategies (SPEC-05) — the heart; sequence is mandatory, T6.01 — Strategy data access + volume alignment `[CP]`, T6.02 — Calibration anchors `[CP]`, T6.03 — Retrospective S1 `[CP]`, T6.04 — Retrospective S2/S3/S4 + no-lookahead test `[CP]`, T6.05 — Annual summary, headline, charts `[CP]`, T6.06 — Sensitivities `[PAR]`, T6.07 — Forward bootstrap (vectorized) `[CP]` (+3 more)

### Community 42 - "SPEC-02 — Data Model (DuckDB + dbt)"
Cohesion: 0.18
Nodes (10): 1. Stack and layout, 2. Timezone doctrine (repeat of the single most dangerous bug class), 3. Staging models (exact contracts), 4. Dimensions, 5. Marts (exact contracts — the M3 exit gate diff-checks these), 6. dbt tests (minimum set; all must pass in `dbt build`), 7. Exports for BI (produced by `make export`, consumed by Power BI — SPEC-06), `dim_calendar` (grain: hour) (+2 more)

### Community 43 - "Codebase Concerns"
Cohesion: 0.20
Nodes (9): Codebase Concerns, Dependencies at Risk, Known Bugs, Missing Critical Features, Performance Bottlenecks, Scaling Limits, Security Considerations, Tech Debt (+1 more)

### Community 44 - "Graph Report - energy-procurement-risk-analyzer  (2026-07-22)"
Cohesion: 0.25
Nodes (7): Community Hubs (Navigation), Corpus Check, Graph Freshness, Graph Report - energy-procurement-risk-analyzer  (2026-07-22), Import Cycles, Knowledge Gaps, Summary

### Community 45 - "write-session-snap.js"
Cohesion: 0.08
Nodes (31): buildSessionBriefing(), findContinueHere(), findPlanningRoot(), fs, headLines(), path, resolveRepoRoot(), currentBranch() (+23 more)

### Community 46 - "Doc Ingest Synthesis Summary"
Cohesion: 0.18
Nodes (10): Conflicts, Constraints, Context topics, Cross-ref cycle detection, Decisions (locked), Doc counts by type, Doc Ingest Synthesis Summary, Intel files (+2 more)

### Community 47 - "Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.18
Nodes (10): Active, Constraints, Context, Core Value, Energy Procurement Risk Analyzer (EPRA), Key Decisions, Out of Scope, Requirements (+2 more)

### Community 48 - "build_profile"
Cohesion: 0.18
Nodes (5): Data Flow, Directory Purposes, build_profile(), monthly_volumes(), render_executive_charts()

### Community 49 - "test_scripts.py"
Cohesion: 0.35
Nodes (6): _run(), test_oespi_reconcile_accepts_matching_entries(), test_oespi_reconcile_rejects_mismatch(), test_oespi_reconcile_requires_both_entries(), test_token_guard_allows_env_placeholder(), test_token_guard_flags_literal()

### Community 50 - "00 — MASTER PLAN: The Execution Operating System"
Cohesion: 0.20
Nodes (10): 00 — MASTER PLAN: The Execution Operating System, 0.1 What this blueprint is — and is not, 0.2 Document map (reading order for a new contributor), 0.3 Mission restated (one sentence, from Charter §1), 0.4 Execution model, 0.5 Task metadata conventions, 0.6 Global Definition of Ready (DoR), 0.7 Global Definition of Done (DoD) (+2 more)

### Community 51 - "Naming Patterns"
Cohesion: 0.15
Nodes (9): Code Style, Coding Conventions, Comments, Function Design, Import Organization, Module Design, Naming Patterns, hybrid_color() (+1 more)

### Community 52 - "Testing Patterns"
Cohesion: 0.18
Nodes (10): Common Patterns, Coverage, Fixtures and Factories, Mocking, Test File Organization, Test Framework, Test Structure, Test Types (+2 more)

### Community 53 - "ModelBuildResult"
Cohesion: 0.07
Nodes (19): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries, Files Created/Modified, build_report(), BuildReport, ModelBuildResult, _monthly_mart_coverage() (+11 more)

### Community 54 - "Requirements: Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.20
Nodes (9): Analytical Questions (Charter Q1–Q4), Extensions, Governance & Quality, Out of Scope, Pipeline Capabilities, Requirements: Energy Procurement Risk Analyzer (EPRA), Traceability, v1 Requirements (+1 more)

### Community 55 - "format.py"
Cohesion: 0.20
Nodes (4): format_eur(), format_eur_millions(), format_eur_mwh(), format_pct()

### Community 56 - "3. Build order and gates (from Charter §7 — expanded into agent tasks)"
Cohesion: 0.22
Nodes (9): 3. Build order and gates (from Charter §7 — expanded into agent tasks), M0 — Bootstrap, M1 — ENTSO-E ingestion, M2 — Auxiliary data, M3 — dbt warehouse, M4 — Consumer profile, M5 — Analytics, M6 — Strategies (+1 more)

### Community 57 - "07 — QUALITY STANDARDS (measurable thresholds)"
Cohesion: 0.25
Nodes (8): 07 — QUALITY STANDARDS (measurable thresholds), 7.1 Code, 7.2 Runtime & memory budgets, 7.3 Determinism & reproducibility (hard, all from SPECs), 7.4 Scientific correctness, 7.5 Data quality, 7.6 Visualization (RP-70x, restated as pass/fail), 7.7 Documentation completeness

### Community 58 - "SPEC-04 — Market Analytics (modules A1–A4)"
Cohesion: 0.22
Nodes (8): §5 Degree-day definitions, §6 Deliverables checklist for M5 (all must exist), §7 Gates (M5 exit), A1 — Descriptive market structure (`analytics/descriptive.py`), A2 — AT–DE-LU spread (`analytics/spread.py`), A3 — Volatility regimes (`analytics/regimes.py`), A4 — Weather & load sensitivity (`analytics/weather.py`, deliberately small), SPEC-04 — Market Analytics (modules A1–A4)

### Community 59 - "SPEC-06 — Reporting, Dashboard, README"
Cohesion: 0.22
Nodes (8): 1. Artifact inventory, 2. Executive charts (exactly these four, in `reports/executive_charts/`), 3. Chart data flow, 4. Power BI dashboard (manual step, precisely specified), 5. `reports/EXEC_SUMMARY.md` (≤ 2 pages, structure mandatory), 6. README.md structure (order mandatory), 7. Chart standards (apply to every PNG in the repo), SPEC-06 — Reporting, Dashboard, README

### Community 60 - "Phase 4: M3 dbt Warehouse - Research"
Cohesion: 0.05
Nodes (38): Anti-Patterns to Avoid, Applicable ASVS Categories, Architecture Patterns, Assumptions Log, Claude's Discretion, Code Examples, Deferred Ideas (OUT OF SCOPE), Don't Hand-Roll (+30 more)

### Community 61 - "External Integrations"
Cohesion: 0.25
Nodes (7): APIs & External Services, Authentication & Identity, CI/CD & Deployment, Environment Configuration, External Integrations, Monitoring & Observability, Webhooks & Callbacks

### Community 62 - "Phase 1: M0 Bootstrap Verification Report"
Cohesion: 0.22
Nodes (8): Gaps Summary, Goal Achievement, Human Verification Required, Observable Truths, Phase 1: M0 Bootstrap Verification Report, Required Artifacts, Requirements Coverage, Verification Metadata

### Community 63 - "CR-01: `iter_chunks` groups 3 raw calendar months without bounding the window to ING-030's 90-day maximum"
Cohesion: 0.15
Nodes (9): CR-01: `iter_chunks` groups 3 raw calendar months without bounding the window to ING-030's 90-day maximum, Fixed Issues, Phase EPRA-02: Code Review Fix Report — M1 ENTSO-E Ingestion, Skipped Issues, WR-03: `_dataset_root`/`_now_utc` helpers are independently reimplemented across modules, test_iter_chunks_apr_may_jun_91_day_span_is_split_not_rejected(), test_iter_chunks_covers_full_window_with_no_gaps_or_overlaps(), test_iter_chunks_never_exceeds_90_days_across_2019_2025() (+1 more)

### Community 64 - "load_strategy_config"
Cohesion: 0.12
Nodes (12): 2026-07-19 — Execution Blueprint (planning deliverable, owner-requested), 2026-07-19 — M0 Bootstrap (complete) + breadth foundation, 2026-07-22 — M1 live backfill run: two data-loss bugs found and fixed, 2026-07-24 — M3 dbt Warehouse (SPEC-02) — both builds green, schema contract byte-matched, BUILD_LOG (append-only, per AGENTS.md W-5), Fragile Areas, Pitfall 3: Calendar horizon coupling to M6 config, load_consumer_profile() (+4 more)

### Community 65 - "ingest"
Cohesion: 0.12
Nodes (14): 08 — DESIGN PATTERNS: exactly where each belongs, Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries, Files Created/Modified, _default_data_transport(), _fetch_geosphere(), ingest() (+6 more)

### Community 67 - "M3 — dbt warehouse (SPEC-02)"
Cohesion: 0.25
Nodes (8): M3 — dbt warehouse (SPEC-02), T3.01 — Sources + schema-name macro + external parquet plumbing `[CP]`, T3.02 — Staging models (8) `[CP]`, T3.03 — dim_calendar + dim_strategy `[PAR]`, T3.04 — Marts `[CP]`, T3.05 — dbt test suite DM-060..066 + schema contract `[CP]`, T3.06 — CI fixture bootstrap + job 3 `[CP]`, T3.07 — M3 PR assembly `[CP]` — as T1.11 (gate: dbt build green real+fixtures; schemas byte-match). BUILD_LOG.

### Community 68 - "M5 — Analytics (SPEC-04) — order A1→A2→A4→A3"
Cohesion: 0.25
Nodes (8): M5 — Analytics (SPEC-04) — order A1→A2→A4→A3, T5.01 — Analytics shared kit `[CP]`, T5.02 — A1 descriptive `[PAR]`, T5.03 — A2 spread `[PAR]` — AN-201..203 artifacts + SSOT `spread_mean_<year>`; interpretation paragraph. **Effort:** M · **Depends:** T5.01 · **AC:** zero-line present in chart; stats table matches a hand-checked month., T5.04 — A4 weather `[PAR]` — AN-401..402: scatter+OLS (HC1, month FE) to md+PNG; weather-invariance sentence included. **Effort:** M · **Depends:** T5.01 · **AC:** OLS coefficient sign positive (load rises with HDD) asserted with tolerance; prose test green., T5.05 — A3 regimes (HMM) `[CP]`, T5.06 — A3 GARCH complement `[PAR]`, T5.07 — `make analyze` + AN-70x gates + M5 PR `[CP]`

### Community 69 - "M7 — Reporting, dashboard, refresh, release (SPEC-06, SPEC-07 §8)"
Cohesion: 0.25
Nodes (8): M7 — Reporting, dashboard, refresh, release (SPEC-06, SPEC-07 §8), T7.01 — Export script + contract tests `[CP]`, T7.02 — Executive charts `[CP]`, T7.03 — EXEC_SUMMARY `[HUMAN-co]` `[CP]`, T7.04 — Final README + LIMITATIONS `[CP]`, T7.05 — refresh.yml `[CP]`, T7.06 — Power BI handoff + human build `[HUMAN]`, T7.07 — Release: DL-1..10 walk + M7 PR `[CP]`

### Community 70 - "06 — CHECKLISTS"
Cohesion: 0.25
Nodes (8): 06 — CHECKLISTS, 6.1 Global implementation checklist (every PR), 6.2 Global code-review checklist (reviewer or self-review before merge), 6.3 Global QA checklist (run, don't read), 6.4 Scientific validation checklist (M4/M5/M6 only), 6.5 Documentation checklist (every milestone), 6.6 Repository hygiene checklist (every milestone), 6.7 Per-milestone implementation specifics

### Community 71 - "SPEC-08 — Governance & Quality (deliberately lightweight)"
Cohesion: 0.25
Nodes (8): 1. Epistemic tags, 2. ADRs (Architecture Decision Records), 3. SSOT mechanism, 4. CI gates summary (defined in SPEC-07 §8; listed here as the quality contract), 5. Data quality gates index (where they live), 6. LIMITATIONS.md (must contain at least these sections, honestly written), 7. What deliberately does NOT exist here, SPEC-08 — Governance & Quality (deliberately lightweight)

### Community 72 - "connect"
Cohesion: 0.22
Nodes (3): Data Storage, connect(), warehouse_path()

### Community 73 - "LIMITATIONS"
Cohesion: 0.22
Nodes (8): 1. The consumer load profile is constructed, not measured, 2. ÖSPI as forward/contract price proxy, 3. The fixed-price premium is an assumption, 4. The bootstrap cannot simulate an unprecedented regime, 5. Grid fees, taxes, and levies are excluded, 6. Data-quality caveats for 2025, 7. No forecast-skill claim, LIMITATIONS

### Community 74 - "Technology Stack"
Cohesion: 0.25
Nodes (7): Configuration, Frameworks, Key Dependencies, Languages, Platform Requirements, Runtime, Technology Stack

### Community 75 - "setup"
Cohesion: 0.11
Nodes (15): 6. Logging & errors, Architecture, Cross-Cutting Concerns, Entry Points, Layers, Pattern Overview, Logging, Codebase Structure (+7 more)

### Community 76 - "discover_station"
Cohesion: 0.08
Nodes (27): ADR-007: GeoSphere station selection (ING-091), Consequences, Context, Decision, Spec deviations, Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries (+19 more)

### Community 77 - "Phase 2 — Validation Strategy"
Cohesion: 0.14
Nodes (11): ADR-006: Validation gates assert over complete Vienna-local years within the ingested window, Context, Decision, Spec deviations, Manual-Only Verifications, Per-Task Verification Map, Phase 2 — Validation Strategy, Sampling Rate (+3 more)

### Community 78 - "Ingestion validation report — 2026-07-22"
Cohesion: 0.25
Nodes (7): ING-080 — PASS, ING-081 — PASS, ING-082 — PASS, ING-083 — PASS, ING-084 — PASS, ING-085 — PASS, Ingestion validation report — 2026-07-22

### Community 79 - "AGENTS.md — Build Playbook for AI Agents"
Cohesion: 0.29
Nodes (6): 1. Non-negotiable rules, 2. When to STOP and ask the human, 4. Working style requirements, 5. Verification protocol (run before claiming any milestone done), 6. Known traps (learn from these in advance), AGENTS.md — Build Playbook for AI Agents

### Community 80 - "M2 — Auxiliary data (SPEC-01 §§9–11) — merge FIRST (R-1)"
Cohesion: 0.29
Nodes (7): M2 — Auxiliary data (SPEC-01 §§9–11) — merge FIRST (R-1), T2.01 — Calendar module `[PAR]` `[CP]`, T2.02 — GeoSphere discovery + station ADR `[PAR]`, T2.03 — GeoSphere ingestion + gates `[PAR]`, T2.04 — ÖSPI loader + gates + methodology ADR, T2.05 — ÖSPI double transcription `[HUMAN]` `[CP]`, T2.06 — M2 PR assembly `[CP]`

### Community 81 - "04 — DEPENDENCY GRAPHS, CRITICAL PATH, PARALLELISM"
Cohesion: 0.29
Nodes (7): 04 — DEPENDENCY GRAPHS, CRITICAL PATH, PARALLELISM, 4.1 Module dependency graph (import-level; arrows = "may import"), 4.2 Milestone dependency graph, 4.3 Execution dependency graph (task level, abridged to decision-relevant edges), 4.4 Critical path, 4.5 Parallel lanes (safe to run concurrently, different agents), 4.6 Blocked / risky / API-dependent work

### Community 82 - "Claude Code ↔ Cursor Continuity"
Cohesion: 0.29
Nodes (6): Claude Code ↔ Cursor Continuity, Graphify, Hook behavior (local), Skill sync (after `/gsd-update`), Source of truth, Switch / resume protocol

### Community 83 - "test_geosphere.py"
Cohesion: 0.12
Nodes (23): _fixture_geojson(), _fixture_metadata(), _settings(), _sleep_calls(), test_discover_station_filters_out_non_graz_and_shorter_records(), test_discover_station_prefers_graz_universitaet(), test_discover_station_raises_when_no_graz_station(), test_discover_station_rejects_malformed_top_level_shape() (+15 more)

### Community 84 - "Onboarding Summary"
Cohesion: 0.29
Nodes (6): Authority hierarchy, Current position, Next command, Onboarding Summary, Open warnings (non-blocking), What was done

### Community 85 - "02-UAT.md"
Cohesion: 0.29
Nodes (6): 1. Live backfill produces four dataset trees under data/raw/, 2. make validate-ingest reports ING-080..085 PASS on real data, Current Test, Gaps, Summary, Tests

### Community 86 - "Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.15
Nodes (13): Architecture, Author, Data, Energy Procurement Risk Analyzer (EPRA), Explore this project, License, Limitations, Method (+5 more)

### Community 87 - "oespi_reconcile.py"
Cohesion: 0.36
Nodes (3): main(), _read(), reconcile()

### Community 88 - "gate_ing_111"
Cohesion: 0.10
Nodes (20): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness (+12 more)

### Community 89 - "geosphere.py"
Cohesion: 0.10
Nodes (7): load_settings(), main(), _dataset_root(), main(), _write_report(), test_db_connect_creates_warehouse(), test_logging_setup_is_idempotent()

### Community 90 - "build_calendar"
Cohesion: 0.10
Nodes (17): Files Created/Modified, Integration Points, 1. Real ÖSPI double-entry transcription and reconciliation, Anti-Patterns Found, Behavioral Spot-Checks, Gaps Summary, Goal Achievement, Human Verification Required (+9 more)

### Community 91 - "ContractError"
Cohesion: 0.08
Nodes (31): ADR-008: ÖSPI series methodology — one pinned source, pending human confirmation (ING-102), Consequences, Context, Decision, Spec deviations, Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries (+23 more)

### Community 93 - "ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored"
Cohesion: 0.33
Nodes (5): ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored, Consequences, Context, Decision, Spec deviations

### Community 94 - "ADR-002: Dev-only typing-stub packages for mypy --strict"
Cohesion: 0.33
Nodes (5): ADR-002: Dev-only typing-stub packages for mypy --strict, Consequences, Context, Decision, Spec deviations

### Community 95 - "ADR-003: EntsoeRawClient as transport; own Appendix-A parsers (adopts SG-01)"
Cohesion: 0.33
Nodes (5): ADR-003: EntsoeRawClient as transport; own Appendix-A parsers (adopts SG-01), Consequences, Context, Decision, Spec deviations

### Community 96 - "ADR-004: pyarrow as the pandas parquet engine for ingestion I/O"
Cohesion: 0.33
Nodes (5): ADR-004: pyarrow as the pandas parquet engine for ingestion I/O, Consequences, Context, Decision, Spec deviations

### Community 97 - "test_bootstrap_fixture_warehouse.py"
Cohesion: 0.17
Nodes (10): _dummy_raw_price_file(), _read_dataset(), _run(), test_default_window_covers_2022_2024_with_dst_days_and_crisis_month(), test_determinism_same_seed_identical_data_across_two_runs(), test_force_guard_proceeds_with_force(), test_force_guard_refuses_populated_manual_oespi_without_force(), test_force_guard_refuses_populated_raw_without_force() (+2 more)

### Community 98 - "parse_publication_xml"
Cohesion: 0.25
Nodes (18): parse_publication_xml(), _read(), test_infer_resolution_matches_load_fixture(), test_infer_resolution_matches_pt15m_fixture(), test_infer_resolution_matches_pt60m_fixture(), test_parse_gl_xml_acknowledgement_raises_no_data_error(), test_parse_gl_xml_generation_long_format(), test_parse_gl_xml_load_columns() (+10 more)

### Community 99 - "Phase 3: M2 Auxiliary Data - Research"
Cohesion: 0.10
Nodes (20): Architectural Responsibility Map, Assumptions Log, Claude's Discretion, Core, Deferred Ideas (OUT OF SCOPE), Environment Availability, Locked Decisions, Metadata (+12 more)

### Community 100 - "M4 — Consumer profile (SPEC-03)"
Cohesion: 0.33
Nodes (6): M4 — Consumer profile (SPEC-03), T4.01 — Weight engine (algorithm steps 1–4) `[CP]`, T4.02 — Normalization incl. partial years `[CP]`, T4.03 — Outputs: hourly parquet, monthly volumes, peak share `[CP]`, T4.04 — flat_baseload variant + golden/property/meta tests `[CP]`, T4.05 — `make profile` wiring + M4 PR `[CP]` — CLI entry, Makefile target un-stubbed, stub-test rows for M4 deleted, BUILD_LOG, PR per template.

### Community 101 - "Phase 1: M0 Bootstrap Summary"
Cohesion: 0.33
Nodes (5): Accomplishments, Files Created/Modified, Next Phase Readiness, Phase 1: M0 Bootstrap Summary, Task Commits

### Community 102 - "_ensure_entsoe_fixtures_dir"
Cohesion: 0.25
Nodes (5): IN-01: `ingested_at_utc` provenance column is a plain ISO string, inconsistent with `ts_utc`'s tz-aware timestamp dtype, IN-02: Fixture provenance documentation is inconsistent between `conftest.py`'s README template and `test_raw_contracts.py`'s docstring, Info, Phase EPRA-02: Code Review Report — M1 ENTSO-E Ingestion (Iteration 2), _ensure_entsoe_fixtures_dir()

### Community 104 - "parse_geojson"
Cohesion: 0.10
Nodes (16): Common Pitfalls, Phase Requirements → Test Map, Pitfall 1: `_io.write_month()` rejects GeoSphere's date-keyed frame out of the box, Pitfall 2: Splicing the two ÖSPI methodologies, Pitfall 4: `holidays.Austria(subdiv='6', years=...)` needs a dynamic year range, not a fixed list, Pitfall 5: GeoSphere response parsing — GeoJSON nesting, not a flat table, Pitfall 6: ING-080-style false-missing-hours does NOT apply to daily GeoSphere data the same way, but coverage arithmetic still needs the right denominator, Sampling Rate (+8 more)

### Community 105 - "Phase 4: M3 dbt Warehouse - Context"
Cohesion: 0.10
Nodes (19): Canonical References, CI fixture bootstrap (Area B — SG-06, T3.06), Claude's Discretion, Contract & ADR governance (Area D — SG-05, T3.05), Deferred Ideas, Downstream consumers (context, not modified here), Established Patterns, Existing Code Insights (+11 more)

### Community 107 - "Key Abstractions"
Cohesion: 0.18
Nodes (4): Key Abstractions, run(), main(), run()

### Community 108 - "10 — VALIDATION GATES: the no-progression ladder"
Cohesion: 0.40
Nodes (5): 10 — VALIDATION GATES: the no-progression ladder, Gate lanes, Gate lifecycle, Per-milestone gate matrix, Stop conditions (halt the milestone, do not route around)

### Community 109 - "11 — ACCEPTANCE CRITERIA (objective, runnable)"
Cohesion: 0.40
Nodes (5): 11.1 Rules for acceptance criteria (all tasks), 11.2 Milestone acceptance (beyond the gate matrix in [10_VALIDATION_GATES.md](10_VALIDATION_GATES.md)), 11.3 DL-1..10 release verification (M7, execute literally), 11.4 Definition of Ready / Done, 11 — ACCEPTANCE CRITERIA (objective, runnable)

### Community 110 - "13 — TRACEABILITY MATRIX"
Cohesion: 0.40
Nodes (4): 13.1 Task → spec → deliverable (condensed; task cards carry the full lists), 13.2 Reverse coverage check (REQ → task), 13.3 Artifact → producer index, 13 — TRACEABILITY MATRIX

### Community 112 - "Conflict Detection Report"
Cohesion: 0.40
Nodes (4): BLOCKERS (0), Conflict Detection Report, INFO (6), WARNINGS (11)

### Community 113 - "Phase 1 (M0 Bootstrap) — Plan 01: Repo, tooling, CI, pipeline skeleton"
Cohesion: 0.40
Nodes (4): Objective, Phase 1 (M0 Bootstrap) — Plan 01: Repo, tooling, CI, pipeline skeleton, Requirements, Scope delivered (see commit c043933)

### Community 114 - "test_entsoe_token_fails_fast_when_unset"
Cohesion: 0.32
Nodes (6): Issues Encountered, Deferred Items — EPRA-02 M1 ENTSO-E Ingestion, From 02-02 (raw parquet writer `_io`), From 02-05 (ingest orchestration, CLI, Makefile), From 02-06 (validation gate framework, `validate-ingest`), test_entsoe_token_fails_fast_when_unset()

### Community 115 - "Phase 3: M2 Auxiliary Data - Context"
Cohesion: 0.11
Nodes (17): Binding spec (authority), Calendar forward horizon (SPEC-01 §11 · SG-15), Canonical References, Claude's Discretion, Deferred Ideas, Established Patterns, Existing Code Insights, Implementation Decisions (+9 more)

### Community 117 - "02 — WORK BREAKDOWN STRUCTURE"
Cohesion: 0.50
Nodes (4): 02 — WORK BREAKDOWN STRUCTURE, TP.01 — Activate ENTSO-E token `[HUMAN]` `[CP]`, TP.02 — GitHub remote, branch protection, CI secret `[HUMAN]`, TP — Preparatory / operations tasks

### Community 118 - "Synthesized Decisions (ADRs)"
Cohesion: 0.50
Nodes (3): ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored, ADR-002: Dev-only typing-stub packages for mypy --strict, Synthesized Decisions (ADRs)

### Community 119 - "MonkeyPatch"
Cohesion: 0.15
Nodes (11): test_backfill_iterates_all_four_dataset_keys_in_order(), spy_ingest_dataset(), test_ingest_incremental_uses_45_day_lookback_from_today(), test_main_backfill_defaults_start_and_uses_latest_complete_month(), test_main_backfill_falls_back_to_conservative_end_when_no_data(), test_main_backfill_invokes_backfill_with_explicit_window(), fake_backfill(), test_main_backfill_no_cache_flag_forwarded() (+3 more)

### Community 120 - "test_calendar.py"
Cohesion: 0.16
Nodes (4): calendar_frame(), test_build_calendar_ing_111_holiday_count_and_fixed_holidays(), test_build_calendar_ing_111_peak_hours(), test_build_calendar_spine_covers_2019_through_end()

### Community 121 - "Settings"
Cohesion: 0.07
Nodes (23): 7.8 Coding standards (beyond lint — normative), Error Handling, Error Handling, God Nodes (most connected - your core abstractions), Pattern Assignments, `src/epra/ingest/entsoe.py` (service, batch + file-I/O), `src/epra/ingest/_fetch.py` (service, request-response), `src/epra/ingest/_io.py` (utility, file-I/O) (+15 more)

### Community 122 - "_fetch.py"
Cohesion: 0.16
Nodes (3): _cache_path(), _cache_root(), _default_transport()

### Community 123 - "Phase EPRA-04 Plan 02: Staging Models (8 views) Summary"
Cohesion: 0.15
Nodes (12): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance (+4 more)

### Community 124 - "Phase EPRA-04 Plan 04: Price/Generation Marts (fct_price_hourly/daily/monthly, fct_generation_monthly) Summary"
Cohesion: 0.15
Nodes (12): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance (+4 more)

### Community 135 - "is_peak_hour"
Cohesion: 0.17
Nodes (12): ADR-011: One holiday-aware `is_peak_hour` drives every peak-price computation, Consequences, Context, Decision, Spec deviations, 14 — SPECIFICATION GAPS & AMBIGUITY RESOLUTIONS, SPEC-01: Calendar generation, Artifacts this phase produces (this plan) (+4 more)

### Community 138 - "Phase EPRA-04 Plan 05: Fixture/Stand-in Generator + Future Marts (D-04, SG-06) Summary"
Cohesion: 0.15
Nodes (12): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance (+4 more)

### Community 139 - "Phase EPRA-04 Plan 06: DM-050/062/064/065/066 Test Suite + D-07 Schema Contract Summary"
Cohesion: 0.15
Nodes (12): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance (+4 more)

### Community 140 - "test_entsoe_orchestration.py"
Cohesion: 0.24
Nodes (5): _full_month_price_frame(), _partial_month_price_frame(), test_latest_complete_month_excludes_incomplete_month(), test_latest_complete_month_raises_when_no_data_ingested(), test_latest_complete_month_returns_min_of_at_and_delu()

### Community 142 - "_validate_date_key"
Cohesion: 0.27
Nodes (6): Accomplishments, Decisions Made, Files Created/Modified, _month_bounds(), _validate_date_key(), _validate_ts_utc_key()

### Community 143 - "Phase EPRA-04 Plan 01: dbt Foundation — Schema Macro, Sources, Helper Macros Summary"
Cohesion: 0.17
Nodes (11): Accomplishments, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-04 Plan 01: dbt Foundation — Schema Macro, Sources, Helper Macros Summary (+3 more)

### Community 144 - "Phase EPRA-04 Plan 03: dim_calendar + dims.yml (DM-060) Summary"
Cohesion: 0.17
Nodes (11): Accomplishments, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-04 Plan 03: dim_calendar + dims.yml (DM-060) Summary (+3 more)

### Community 145 - "Phase EPRA-04 Plan 07: D-02 Build-Report Writer + Makefile Operator Interface Summary"
Cohesion: 0.18
Nodes (10): Auto-fixed Issues, Decisions Made, Deviations from Plan, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-04 Plan 07: D-02 Build-Report Writer + Makefile Operator Interface Summary, Self-Check: PASSED (+2 more)

### Community 146 - "Phase EPRA-04 Plan 08: CI dbt-check Job + M3 Close-Out Summary"
Cohesion: 0.18
Nodes (10): Accomplishments, Decisions Made, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-04 Plan 08: CI dbt-check Job + M3 Close-Out Summary, Self-Check: PASSED (+2 more)

### Community 147 - "Ingestion validation report — 2026-07-23"
Cohesion: 0.18
Nodes (10): ING-080 — PASS, ING-081 — PASS, ING-082 — PASS, ING-083 — PASS, ING-084 — PASS, ING-085 — PASS, ING-094 — PASS, ING-103 — PASS (+2 more)

### Community 149 - "Phase EPRA-03 Plan 01: write_month key_column dispatcher Summary"
Cohesion: 0.20
Nodes (9): Deviations from Plan, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-03 Plan 01: write_month key_column dispatcher Summary, Self-Check: PASSED, TDD Gate Compliance, User Setup Required (+1 more)

### Community 150 - "Phase EPRA-03 Plan 02: Calendar hourly spine (ING-110/111) Summary"
Cohesion: 0.20
Nodes (9): Auto-fixed Issues, Deviations from Plan, Issues Encountered, Next Phase Readiness, Performance, Phase EPRA-03 Plan 02: Calendar hourly spine (ING-110/111) Summary, Self-Check: PASSED, Task Commits (+1 more)

### Community 151 - "Shared Patterns"
Cohesion: 0.20
Nodes (9): CLI script shape (`argparse` + `main(argv) -> int` + `sys.exit`/`raise SystemExit`), Contract-table-as-YAML + parametrized pytest diff, DuckDB access via shared helper, `Implements: XXX-nnn` spec-ID citation, Metadata, No Analog Found, Phase 4: M3 dbt Warehouse - Pattern Map, Shared Patterns (+1 more)

### Community 152 - "test_marts_contract.py"
Cohesion: 0.24
Nodes (3): _actual_columns(), _expected_columns(), test_mart_schema_matches_contract()

### Community 153 - "Phase 3: M2 Auxiliary Data - Discussion Log"
Cohesion: 0.25
Nodes (7): Calendar horizon (SG-15 / ING-110), Claude's Discretion, Deferred Ideas, Phase 3: M2 Auxiliary Data - Discussion Log, Real-data boundary & phase close, ÖSPI series & fallback (ING-102 / ING-104), ÖSPI transcription (ING-101 double-entry)

### Community 154 - "Phase 3 — Validation Strategy"
Cohesion: 0.25
Nodes (7): Manual-Only Verifications, Per-Task Verification Map, Phase 3 — Validation Strategy, Sampling Rate, Test Infrastructure, Validation Sign-Off, Wave 0 Requirements

### Community 155 - "Phase 4: M3 dbt Warehouse - Discussion Log"
Cohesion: 0.25
Nodes (7): CI fixture bootstrap, Claude's Discretion, Contract & ADR governance, Deferred Ideas, Future-mart stand-ins, Phase 4: M3 dbt Warehouse - Discussion Log, Real-data close boundary

### Community 156 - "Phase 4 — Validation Strategy"
Cohesion: 0.25
Nodes (7): Manual-Only Verifications, Per-Task Verification Map, Phase 4 — Validation Strategy, Sampling Rate, Test Infrastructure, Validation Sign-Off, Wave 0 Requirements

### Community 158 - "5.1 M1 — ENTSO-E"
Cohesion: 0.29
Nodes (7): 5.1 M1 — ENTSO-E, A03 forward-fill (ING-063), Chunking loop shape, Client strategy (SG-01, adopt via ADR in T1.02's commit range), ING-082 failure investigation protocol (do IN ORDER, stop when found), Live backfill runbook (T1.10), Timezone recipe (T-1/T-4, do exactly this)

### Community 159 - "Project Audit — 2026-09-30 (findings only, nothing fixed)"
Cohesion: 0.29
Nodes (6): 1. P0 — Blocks the deliverable, 3. P1 — Stale / wrong claims in docs and planning, 5. Additional findings from the docs-consistency pass, P1, P2, Project Audit — 2026-09-30 (findings only, nothing fixed)

### Community 160 - "Pattern Assignments"
Cohesion: 0.29
Nodes (7): dbt models/macros/tests/YAML (D-01–D-08, T3.01–T3.06), `.github/workflows/ci.yml` `dbt-check` job (config, event-driven), `Makefile` `transform:` target (config, batch), Pattern Assignments, `scripts/bootstrap_fixture_warehouse.py` (utility, batch/file-I/O), `tests/unit/test_bootstrap_fixture_warehouse.py` (test, batch), `tests/unit/test_marts_contract.py` (test, request-response / schema-diff)

### Community 161 - "Common Pitfalls"
Cohesion: 0.29
Nodes (7): Common Pitfalls, Pitfall 1: Relative-path mismatch between `dbt/` cwd and `data/`, Pitfall 2: Native `generate_schema_name` override breaks CI/dev isolation if ever multi-environment, Pitfall 3: `dbt/contracts/marts_contract.yml` silently ignored by dbt, Pitfall 4: 15-minute vs 60-minute resolution mixed-month aggregation off-by-one, Pitfall 5: TIMESTAMPTZ vs plain TIMESTAMP dtype mismatch across sources, Pitfall 6: `union_by_name` needed if any monthly parquet ever has reordered columns

### Community 162 - "ADR-009: `generate_schema_name` override — literal `staging`/`marts` schemas"
Cohesion: 0.33
Nodes (5): ADR-009: `generate_schema_name` override — literal `staging`/`marts` schemas, Consequences, Context, Decision, Spec deviations

### Community 163 - "ADR-010: CI fixture bootstrap synthesizes data at run time; environment-aligned data/processed stand-ins feed the local build too"
Cohesion: 0.33
Nodes (5): ADR-010: CI fixture bootstrap synthesizes data at run time; environment-aligned data/processed stand-ins feed the local build too, Consequences, Context, Decision, Spec deviations

### Community 164 - "DiscoveryError"
Cohesion: 0.33
Nodes (4): epra.ingest.geosphere (T2.02–T2.03), DiscoveryError, _require_station_id(), fake_ingest()

### Community 165 - "dbt build report — 2026-07-24"
Cohesion: 0.33
Nodes (5): 2022-08 reconciliation delta (DM-064) — PASS, dbt build report — 2026-07-24, fct_price_hourly row counts (DM-062) — PASS, future marts — PASS, monthly-mart month coverage (DM-050) — PASS

### Community 167 - "test_ingest_dataset_pages_past_100_document_cap"
Cohesion: 0.33
Nodes (3): _synth_prices_xml(), test_ingest_dataset_pages_past_100_document_cap(), capped_transport()

### Community 168 - "Architecture Patterns"
Cohesion: 0.40
Nodes (5): Architecture Patterns, Pattern 1: Extend the shared writer for date-keyed (non-hourly) raw datasets, Pattern 2: GeoSphere discovery-then-ingest, ADR-gated, Recommended Project Structure, System Architecture Diagram

### Community 169 - "Code Examples"
Cohesion: 0.40
Nodes (5): Code Examples, Existing pattern to mirror: `_io.write_month`'s atomicity (already built, M1), Existing pattern to mirror: `latest_complete_month()` — the M1 function `calendar.py` must wire as its dynamic `--end` default (D-09), GeoSphere endpoint shape (CITED, not exhaustively verified against a live response this session), Verified: `holidays` package Austria/Styria subdivision (installed-package introspection, this session)

### Community 172 - "04-01-PLAN.md"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries

### Community 173 - "04-02-PLAN.md"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries

### Community 174 - "04-03-PLAN.md"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries

### Community 175 - "04-05-PLAN.md"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries

### Community 176 - "04-06-PLAN.md"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries

### Community 177 - "04-08-PLAN.md"
Cohesion: 0.50
Nodes (3): Artifacts this phase produces (this plan), STRIDE Threat Register, Trust Boundaries

### Community 178 - "_marts_schema_populated"
Cohesion: 0.50
Nodes (3): Auto-fixed Issues, Deviations from Plan, _marts_schema_populated()

### Community 179 - "Standard Stack"
Cohesion: 0.50
Nodes (4): Alternatives Considered, Core, Standard Stack, Supporting

### Community 180 - "Deferred Items — EPRA-04 M3 dbt Warehouse"
Cohesion: 0.50
Nodes (3): 04-04, 04-07, Deferred Items — EPRA-04 M3 dbt Warehouse

## Knowledge Gaps
- **941 isolated node(s):** `fs`, `path`, `fs`, `path`, `{ spawn, execSync }` (+936 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1414 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `Communities (142 total, 18 thin omitted)`, `entsoe.py`, `_read`, `test_io.py`, `Summary`, `Shared Patterns`, `test_fetch.py`, `run_gates`, `test_fetch_entsoe_cache_tmp_path_is_per_call_unique`, `test_entsoe_orchestration.py`, `_year_hourly`, `test_ingest_gates.py`, `write_month`, `fetch_entsoe`, `bootstrap_fixture_warehouse.py`, `Phase EPRA-02 Plan 01: Wave 0 Architecture Decisions Summary`, `latest_complete_month`, `SPEC-07 — Engineering, Tooling, CI/CD`, `config.py`, `DiscoveryError`, `test_ingest_dataset_pages_past_100_document_cap`, `build_profile`, `Naming Patterns`, `ModelBuildResult`, `test_calendar_main_writes_single_parquet_file`, `load_strategy_config`, `ingest`, `connect`, `setup`, `discover_station`, `test_geosphere.py`, `geosphere.py`, `build_calendar`, `ContractError`, `forward_risk.py`, `Key Abstractions`, `MonkeyPatch`, `_fetch.py`?**
  _High betweenness centrality (0.254) - this node is a cross-community bridge._
- **Why does `Communities (142 total, 18 thin omitted)` connect `Communities (142 total, 18 thin omitted)` to `run_gates`, `iter_month_starts`, `Graph Report - energy-procurement-risk-analyzer  (2026-07-22)`, `hourly_mean`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `is_peak_hour()` connect `is_peak_hour` to `timeutil.py`, `run_gates`, `Phase EPRA-04 Plan 05: Fixture/Stand-in Generator + Future Marts (D-04, SG-06) Summary`, `Specification gaps tracker (14_SPEC_GAPS)`, `Phase EPRA-04 Plan 03: dim_calendar + dims.yml (DM-060) Summary`, `write_month`, `bootstrap_fixture_warehouse.py`, `SPEC-02 — Data Model (DuckDB + dbt)`, `Codebase Concerns`, `04-03-PLAN.md`, `Phase 4: M3 dbt Warehouse - Research`, `load_strategy_config`, `LIMITATIONS`, `M2 — Auxiliary data (SPEC-01 §§9–11) — merge FIRST (R-1)`, `geosphere.py`, `build_calendar`, `ContractError`, `Phase 3: M2 Auxiliary Data - Research`, `Phase 4: M3 dbt Warehouse - Context`, `Phase 3: M2 Auxiliary Data - Context`, `Phase EPRA-04 Plan 04: Price/Generation Marts (fct_price_hourly/daily/monthly, fct_generation_monthly) Summary`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 141 inferred relationships involving `Settings` (e.g. with `7.8 Coding standards (beyond lint — normative)` and `08 — DESIGN PATTERNS: exactly where each belongs`) actually correct?**
  _`Settings` has 141 INFERRED edges - model-reasoned connections that need verification._
- **Are the 47 inferred relationships involving `write_month()` (e.g. with `Decision` and `2026-07-21 — M1 ENTSO-E Ingestion (automated deliverables complete; live-data gate pending operator)`) actually correct?**
  _`write_month()` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `ContractError` (e.g. with `Context` and `Consequences`) actually correct?**
  _`ContractError` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `fetch_entsoe()` (e.g. with `God Nodes (most connected - your core abstractions)` and `Accomplishments`) actually correct?**
  _`fetch_entsoe()` has 19 INFERRED edges - model-reasoned connections that need verification._