# Graph Report - energy-procurement-risk-analyzer  (2026-07-22)

## Corpus Check
- 154 files · ~320,425 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1637 nodes · 2308 edges · 142 communities (124 shown, 18 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 54 edges (avg confidence: 0.66)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `487d467a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Communities (137 total, 18 thin omitted)
- entsoe.py
- test_entsoe_orchestration.py
- Phase 2: M1 ENTSO-E Ingestion - Research
- test_io.py
- _fetch.py
- Synthesized Constraints (SPECs)
- Pattern Assignments
- timeutil.py
- Settings
- run_gates
- test_fetch.py
- Specification gaps tracker (14_SPEC_GAPS)
- validate.py
- test_raw_contracts.py
- test_ingest_gates.py
- 05 — IMPLEMENTATION GUIDES (the "how", per milestone)
- _io.py
- 00_MASTER_PLAN.md
- Phase 2 Plan 3: ENTSO-E HTTP Transport (_fetch) Summary
- Phase EPRA-02 Plan 06: ENTSO-E Validation Gate Framework Summary
- Phase EPRA-02 Plan 07: M1 Close-Out (Contract Tests, Fixtures, BUILD_LOG) Summary
- Implementation Decisions
- SPEC-01 — Data Ingestion
- SPEC-05 — Procurement Strategy Simulator
- Phase EPRA-02 Plan 01: Wave 0 Architecture Decisions Summary
- Phase EPRA-02 Plan 02: Raw Parquet Writer (`_io`) Summary
- Phase 2 Plan 04: ENTSO-E XML Parsers and Hourly Aggregation Summary
- 03 — MODULE, CLASS, AND FUNCTION CONTRACTS
- Phase EPRA-02 Plan 05: ENTSO-E Ingest Orchestration Summary
- Phase Details
- M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2
- SPEC-07 — Engineering, Tooling, CI/CD
- PROJECT CHARTER — Energy Procurement Risk Analyzer (EPRA)
- load_settings
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
- ConsumerProfileCfg
- test_scripts.py
- 00 — MASTER PLAN: The Execution Operating System
- Coding Conventions
- Testing Patterns
- maybe-graphify-update.js
- Requirements: Energy Procurement Risk Analyzer (EPRA)
- format.py
- 3. Build order and gates (from Charter §7 — expanded into agent tasks)
- 07 — QUALITY STANDARDS (measurable thresholds)
- SPEC-04 — Market Analytics (modules A1–A4)
- SPEC-06 — Reporting, Dashboard, README
- Architecture
- External Integrations
- Phase 1: M0 Bootstrap Verification Report
- Fixed Issues
- load_consumer_profile
- geosphere.py
- conftest.py
- M3 — dbt warehouse (SPEC-02)
- M5 — Analytics (SPEC-04) — order A1→A2→A4→A3
- M7 — Reporting, dashboard, refresh, release (SPEC-06, SPEC-07 §8)
- 06 — CHECKLISTS
- SPEC-08 — Governance & Quality (deliberately lightweight)
- db.py
- LIMITATIONS
- Technology Stack
- Codebase Structure
- build-session-briefing.js
- Phase 2 — Validation Strategy
- Ingestion validation report — 2026-07-22
- AGENTS.md — Build Playbook for AI Agents
- M2 — Auxiliary data (SPEC-01 §§9–11) — merge FIRST (R-1)
- 04 — DEPENDENCY GRAPHS, CRITICAL PATH, PARALLELISM
- Claude Code ↔ Cursor Continuity
- run-graphify-rebuild.js
- Onboarding Summary
- 02-UAT.md
- Energy Procurement Risk Analyzer (EPRA)
- reconcile
- StrategyCfg
- test_logging_and_db.py
- calendar.py
- oespi.py
- _write_report
- ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored
- ADR-002: Dev-only typing-stub packages for mypy --strict
- ADR-003: EntsoeRawClient as transport; own Appendix-A parsers (adopts SG-01)
- ADR-004: pyarrow as the pandas parquet engine for ingestion I/O
- ADR-005: latest_complete_month() = min(AT prices, DE-LU prices) (adopts SG-02)
- ADR-006: Validation gates assert over complete Vienna-local years within the ingested window
- BUILD_LOG (append-only, per AGENTS.md W-5)
- M4 — Consumer profile (SPEC-03)
- Phase 1: M0 Bootstrap Summary
- Info
- check_file
- ingest_dataset
- style.py
- forward_risk.py
- retrospective.py
- 10 — VALIDATION GATES: the no-progression ladder
- 11 — ACCEPTANCE CRITERIA (objective, runnable)
- 13 — TRACEABILITY MATRIX
- Conflict Detection Report
- Phase 1 (M0 Bootstrap) — Plan 01: Repo, tooling, CI, pipeline skeleton
- Deferred Items — EPRA-02 M1 ENTSO-E Ingestion
- logging.py
- test_smoke.py
- 02 — WORK BREAKDOWN STRUCTURE
- Synthesized Decisions (ADRs)
- 4. Scope
- descriptive.py
- regimes.py
- spread.py
- weather.py
- charts.py
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
- 14_SPEC_GAPS.md
- requirements.md
- check_ssot_consistency.py
- export_marts.py
- generate_golden_metrics.py
- generate_ssot.py
- epra

## God Nodes (most connected - your core abstractions)
1. `Communities (137 total, 18 thin omitted)` - 118 edges
2. `Settings` - 108 edges
3. `fetch_entsoe()` - 34 edges
4. `Synthesized Constraints (SPECs)` - 28 edges
5. `parse_publication_xml()` - 25 edges
6. `ContractError` - 21 edges
7. `_old_window()` - 21 edges
8. `Specification gaps tracker (14_SPEC_GAPS)` - 20 edges
9. `parse_gl_xml()` - 19 edges
10. `Phase 2: M1 ENTSO-E Ingestion - Research` - 19 edges

## Surprising Connections (you probably didn't know these)
- `test_fetch_entsoe_401_empty_body_never_leaks_token_via_str_exc_fallback()` --indirect_call--> `IngestAuthError`  [INFERRED]
  tests/unit/test_fetch.py → src/epra/ingest/exceptions.py
- `test_fetch_entsoe_401_raises_auth_error_without_retry()` --indirect_call--> `IngestAuthError`  [INFERRED]
  tests/unit/test_fetch.py → src/epra/ingest/exceptions.py
- `test_fetch_entsoe_403_raises_auth_error_without_retry()` --indirect_call--> `IngestAuthError`  [INFERRED]
  tests/unit/test_fetch.py → src/epra/ingest/exceptions.py
- `test_ingest_dataset_contract_error_leaves_no_partial_file()` --indirect_call--> `ContractError`  [INFERRED]
  tests/unit/test_entsoe_orchestration.py → src/epra/ingest/exceptions.py
- `test_write_month_rejects_missing_ts_utc_column()` --indirect_call--> `ContractError`  [INFERRED]
  tests/unit/test_io.py → src/epra/ingest/exceptions.py

## Import Cycles
- None detected.

## Communities (142 total, 18 thin omitted)

### Community 0 - "Communities (137 total, 18 thin omitted)"
Cohesion: 0.02
Nodes (118): Communities (137 total, 18 thin omitted), Community 0 - "entsoe.py", Community 101 - "Fixed Issues", Community 10 - "05 — IMPLEMENTATION GUIDES (the "how", per milestone)", Community 118 - "test_raw_contracts.py", Community 11 - "00_MASTER_PLAN.md", Community 120 - "_io.py", Community 121 - "Phase EPRA-02 Plan 06: ENTSO-E Validation Gate Framework Summary" (+110 more)

### Community 1 - "entsoe.py"
Cohesion: 0.06
Nodes (81): DocumentType, Element, Exception, _acknowledgement_reason(), _apply_a03_fill(), backfill(), _child(), _children() (+73 more)

### Community 2 - "test_entsoe_orchestration.py"
Cohesion: 0.08
Nodes (45): Absolute path of the monthly raw parquet file for ``dataset``.      Layout is, raw_month_path(), _fake_token(), _full_month_price_frame(), _no_sleep(), _partial_month_price_frame(), DataFrame, LogCaptureFixture (+37 more)

### Community 3 - "Phase 2: M1 ENTSO-E Ingestion - Research"
Cohesion: 0.04
Nodes (46): Alternatives Considered, Anti-Patterns to Avoid, Applicable ASVS Categories, Architectural Responsibility Map, Architecture Patterns, Assumptions Log, Atomic monthly parquet write (ING-003), Cache key without token (ING-009) (+38 more)

### Community 4 - "test_io.py"
Cohesion: 0.06
Nodes (29): Market analytics A1-A4 (SPEC-04): reads DuckDB marts, writes reports/analytics/., Consumer load profile (SPEC-03): deterministic, CALIBRATED, config-driven., Ingestion layer (SPEC-01): external sources → data/raw/ parquet.  One module per, Reporting layer (SPEC-06): formatting, chart style, executive charts., Procurement strategy simulator (SPEC-05) — the heart of the project.  Build orde, _prices_frame(), DataFrame, date (+21 more)

### Community 5 - "_fetch.py"
Cohesion: 0.11
Nodes (27): BaseException, entsoe_token(), Return the ENTSO-E API token from the environment, failing fast (ING-021)., IngestAuthError, Authentication/authorization failed for an external source.      Raised for miss, _cache_path(), _cache_root(), _default_transport() (+19 more)

### Community 6 - "Synthesized Constraints (SPECs)"
Cohesion: 0.07
Nodes (28): SPEC-01: Calendar generation, SPEC-01: ENTSO-E client and fetch, SPEC-01: General ingestion rules, SPEC-01: Raw output contracts, SPEC-01: Resolution handling, SPEC-01: Validation gates, SPEC-01: Window management, SPEC-02: dbt tests (+20 more)

### Community 7 - "Pattern Assignments"
Cohesion: 0.07
Nodes (27): CLI `main` contract, Configuration injection, Contract tests, File Classification, Functional core / imperative shell, Logging, `Makefile` (config, batch), Metadata (+19 more)

### Community 8 - "timeutil.py"
Cohesion: 0.13
Nodes (25): is_peak_hour(), iter_month_starts(), local_hours_in_day(), month_start(), next_month(), date, datetime, Time handling — the single most dangerous bug class in this project (T-1).  Doct (+17 more)

### Community 9 - "Settings"
Cohesion: 0.18
Nodes (26): Settings, IngestTransportError, Non-recoverable HTTP/network failure fetching from an external source.      Rais, fetch_entsoe(), Fetch raw ENTSO-E XML for `query`, using the on-disk cache (ING-009).      Rea, _old_window(), LogCaptureFixture, CR-02 regression: when the HTTP error response has an empty body,     `_error_d (+18 more)

### Community 10 - "run_gates"
Cohesion: 0.13
Nodes (19): GateFailure, A post-ingest validation gate (ING-080..085) failed.      Raised by `validate.ru, GateResult, main(), Raise ``GateFailure`` naming every failed gate id (EN-061). No-op if all passed., Run all M1 ENTSO-E gates (ING-080..085); write report; raise on failure (EN-061), One SPEC-01 §8 gate's outcome.      Attributes:         gate_id: SPEC REQ ID,, CLI: ``python -m epra.ingest.validate`` -- run all M1 gates, write the report. (+11 more)

### Community 11 - "test_fetch.py"
Cohesion: 0.15
Nodes (21): HTTPError, _fake_token(), _http_error(), Any, MonkeyPatch, _query(), Unit tests for `epra.ingest._fetch` — cache, retry, politeness, and secret-safe, Every test uses a deterministic fake token — never a real one (A-7). (+13 more)

### Community 12 - "Specification gaps tracker (14_SPEC_GAPS)"
Cohesion: 0.09
Nodes (21): Authority note, SG-01 (proposed), SG-02 (proposed), SG-03 (proposed), SG-04 (proposed), SG-05 (proposed), SG-06 (proposed), SG-07 (proposed) (+13 more)

### Community 13 - "validate.py"
Cohesion: 0.14
Nodes (21): _complete_local_years(), gate_ing_082(), gate_ing_084(), gate_ing_085(), _load_hourly(), _local_year(), DataFrame, Series (+13 more)

### Community 14 - "test_raw_contracts.py"
Cohesion: 0.13
Nodes (21): _fixture_path(), Path, ING-070 raw contract drift guards.  Opens each committed §7 fixture parquet unde, entsoe_prices_at: price_eur_mwh double, resolution/zone varchar (ING-070)., entsoe_prices_delu: same shape as entsoe_prices_at, zone='DE_LU' (ING-070)., entsoe_load_at: load_mw double, resolution/zone varchar (ING-070)., entsoe_gen_at: long format, psr_type/psr_name/kind varchar, value_mw double (ING, Every §7 dataset has a committed fixture parquet, <=200 rows (ING-070). (+13 more)

### Community 15 - "test_ingest_gates.py"
Cohesion: 0.17
Nodes (19): gate_ing_080(), gate_ing_081(), gate_ing_083(), ING-080: hour coverage per zone-year (≤24 missing) + DST 23/25 correctness check, ING-081: hourly AT price plausibility, −500 ≤ price ≤ 5000 EUR/MWh.      Out-o, ING-083: negative hourly AT prices must appear in each spec-required year     t, DataFrame, Synthetic pass/fail tests for ING-080..085 validation gates (02-06 task 1).  Eac (+11 more)

### Community 16 - "05 — IMPLEMENTATION GUIDES (the "how", per milestone)"
Cohesion: 0.11
Nodes (19): 05 — IMPLEMENTATION GUIDES (the "how", per milestone), 5.1 M1 — ENTSO-E, 5.2 M2 — Auxiliary data, 5.3 M3 — dbt warehouse, 5.4 M4 — Consumer profile, 5.5 M5 — Analytics, 5.6 M6 — Strategies, 5.7 M7 — Reporting & release (+11 more)

### Community 17 - "_io.py"
Cohesion: 0.16
Nodes (18): _data_raw_root(), _dataset_root(), _now_utc(), DataFrame, date, datetime, Path, Single raw parquet writer — the persistence boundary for all ENTSO-E datasets ( (+10 more)

### Community 18 - "00_MASTER_PLAN.md"
Cohesion: 0.28
Nodes (3): 08 — DESIGN PATTERNS: exactly where each belongs, 09 — ANTI-PATTERNS: automatic PR rejection list, 12 — RISK REGISTER (execution-level; extends Charter §8 R-1..R-8)

### Community 19 - "Phase 2 Plan 3: ENTSO-E HTTP Transport (_fetch) Summary"
Cohesion: 0.12
Nodes (15): Accomplishments, Auto-fixed Issues, Decisions Made, Dependency graph, Deviations from Plan, Files Created/Modified, Issues Encountered, Metrics (+7 more)

### Community 20 - "Phase EPRA-02 Plan 06: ENTSO-E Validation Gate Framework Summary"
Cohesion: 0.12
Nodes (15): Accomplishments, Auto-fixed Issues, Decisions Made, Dependency graph, Deviations from Plan, Files Created/Modified, Issues Encountered, Metrics (+7 more)

### Community 21 - "Phase EPRA-02 Plan 07: M1 Close-Out (Contract Tests, Fixtures, BUILD_LOG) Summary"
Cohesion: 0.12
Nodes (15): Accomplishments, Auto-fixed Issues, Decisions Made, Dependency graph, Deviations from Plan, Files Created/Modified, Issues Encountered, Metrics (+7 more)

### Community 22 - "Implementation Decisions"
Cohesion: 0.12
Nodes (15): Claude's Discretion, Client & Transport (ADR-003 adopts SG-01), Deferred Ideas, Established Patterns, Existing Code Insights, Implementation Decisions, Integration Points, Parquet I/O (ADR-004) (+7 more)

### Community 23 - "SPEC-01 — Data Ingestion"
Cohesion: 0.13
Nodes (14): 10. ÖSPI (manual, double-entry validated), 11. Calendar, 1. General ingestion rules (apply to every source), 2. ENTSO-E: registration and authentication, 3. ENTSO-E: what to fetch, 4. ENTSO-E: window management & incremental refresh, 5. Units and currencies, 6. Resolution handling (CRITICAL — R-2, R-3) (+6 more)

### Community 24 - "SPEC-05 — Procurement Strategy Simulator"
Cohesion: 0.13
Nodes (14): 1. Scope of the decision being modeled, 2. Architecture, 3. Strategy definitions (families S1–S4; grid in dim_strategy, SPEC-02 §4), 4. Calibration anchors, 5. Retrospective engine (Q1), 6. Forward risk engine (Q3) — seasonal block bootstrap, 7. Fair-comparison and honesty rules, 8. `config/strategies.yaml` (authoritative copy) (+6 more)

### Community 25 - "Phase EPRA-02 Plan 01: Wave 0 Architecture Decisions Summary"
Cohesion: 0.13
Nodes (14): Accomplishments, Decisions Made, Dependency graph, Deviations from Plan, Files Created/Modified, Issues Encountered, Metrics, Next Phase Readiness (+6 more)

### Community 26 - "Phase EPRA-02 Plan 02: Raw Parquet Writer (`_io`) Summary"
Cohesion: 0.13
Nodes (14): Accomplishments, Auto-fixed Issues, Decisions Made, Dependency graph, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness (+6 more)

### Community 27 - "Phase 2 Plan 04: ENTSO-E XML Parsers and Hourly Aggregation Summary"
Cohesion: 0.13
Nodes (14): Accomplishments, Auto-fixed Issues, Decisions Made, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance (+6 more)

### Community 28 - "03 — MODULE, CLASS, AND FUNCTION CONTRACTS"
Cohesion: 0.14
Nodes (14): 03 — MODULE, CLASS, AND FUNCTION CONTRACTS, epra.analytics.* (T5.01–T5.07), epra.common (implemented — extension notes only), epra.consumer.profile (T4.01–T4.04), epra.ingest.calendar (T2.01), epra.ingest.entsoe (T1.04–T1.08), epra.ingest._fetch (new, internal — created by T1.02), epra.ingest.geosphere (T2.02–T2.03) (+6 more)

### Community 29 - "Phase EPRA-02 Plan 05: ENTSO-E Ingest Orchestration Summary"
Cohesion: 0.14
Nodes (13): Accomplishments, Decisions Made, Dependency graph, Deviations from Plan, Files Created/Modified, Issues Encountered, Next Phase Readiness, Performance (+5 more)

### Community 30 - "Phase Details"
Cohesion: 0.14
Nodes (13): Overview, Phase 1: M0 Bootstrap, Phase 2: M1 ENTSO-E Ingestion, Phase 3: M2 Auxiliary Data, Phase 4: M3 dbt Warehouse, Phase 5: M4 Consumer Profile, Phase 6: M5 Analytics, Phase 7: M6 Strategy Simulator (+5 more)

### Community 31 - "M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2"
Cohesion: 0.15
Nodes (13): M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2, T1.01 — Raw parquet writer + ING-004 metadata columns `[PAR]` `[CP]`, T1.02 — Fetch layer: cached raw client + retry + politeness `[PAR]` `[CP]`, T1.03a — Handcrafted parser fixtures (pre-token) `[PAR]`, T1.03b — Real-excerpt fixture refresh `[TOKEN]`, T1.04 — Price ingestion AT + DE-LU `[CP]`, T1.05 — Load ingestion AT `[PAR]`, T1.06 — Generation ingestion AT (long format) `[PAR]` (+5 more)

### Community 32 - "SPEC-07 — Engineering, Tooling, CI/CD"
Cohesion: 0.15
Nodes (12): 1. Toolchain, 2. Repository layout (create exactly this; empty dirs get `.gitkeep`), 3. Dependencies (pin these in `pyproject.toml`; upgrades require ADR), 4. Configuration & secrets, 5. Makefile (canonical interface; targets and their meaning), 6. Logging & errors, 7. Testing policy, 8. GitHub Actions (+4 more)

### Community 33 - "PROJECT CHARTER — Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.15
Nodes (13): 10. Glossary, 11. Charter change log, 1.1 The four analytical questions (Q1–Q4), 1.2 The audience, 1. The business problem (read this first), 2. The reference consumer ("StyriaMetal GmbH"), 3. Data sources (all real; no synthetic market data — ever), 5. Epistemic framework (carried over from prior portfolio work, simplified) (+5 more)

### Community 34 - "load_settings"
Cohesion: 0.22
Nodes (12): load_settings(), Load and validate ``config/settings.yaml`` (EN-040). Cached per path., _profile_dict(), MonkeyPatch, Config loading + drift guards.  The committed YAML files are authoritative copie, test_day_shape_validator_rejects_missing_shape(), test_day_shape_validator_rejects_wrong_length(), test_entsoe_token_fails_fast_when_unset() (+4 more)

### Community 35 - "config.py"
Cohesion: 0.29
Nodes (11): BaseModel, ChristmasShutdownCfg, ForwardCfg, _Frozen, GeosphereCfg, IngestCfg, MaintenanceCfg, PathsCfg (+3 more)

### Community 36 - "SPEC-03 — Consumer Load Profile ("StyriaMetal GmbH")"
Cohesion: 0.17
Nodes (12): 1. Principles, 2. Construction algorithm (implement exactly in this order), 3.1 Day shapes (24 values each, index = hour_local 0–23), 3.2 Seasonal factors by month (mild winter uplift — process heat + lighting), 3.3 Special windows (recur every year), 3. Parameters (the values; also encoded in §6 YAML — YAML wins if they ever diverge), 4. Derived facts the rest of the project relies on, 5. Sensitivity variant (cheap, mandatory) (+4 more)

### Community 37 - "Goal Achievement"
Cohesion: 0.17
Nodes (11): Anti-Patterns Found, Behavioral Spot-Checks, Code Review Cycle, Gaps Summary, Goal Achievement, Human Verification Required, Key Link Verification, Observable Truths (ROADMAP Success Criteria) (+3 more)

### Community 38 - "Project State"
Cohesion: 0.17
Nodes (11): Accumulated Context, Blockers/Concerns, Current Position, Decisions, Deferred Items, Deferred Verification, Pending Todos, Performance Metrics (+3 more)

### Community 39 - "hourly_mean"
Cohesion: 0.30
Nodes (11): hourly_mean(), Aggregate sub-hourly rows to hourly by arithmetic MEAN — never sum (T-2)., _pt15m_hour(), DataFrame, Unit tests for `epra.ingest.entsoe.hourly_mean` — the ING-062 guard against the, One hour of 4 PT15M rows starting at `hour_start` (UTC ISO string)., test_hourly_mean_averages_quarters_not_sum(), test_hourly_mean_floors_ts_utc_to_the_hour() (+3 more)

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
Cohesion: 0.18
Nodes (10): Codebase Concerns, Dependencies at Risk, Fragile Areas, Known Bugs, Missing Critical Features, Performance Bottlenecks, Scaling Limits, Security Considerations (+2 more)

### Community 44 - "Graph Report - energy-procurement-risk-analyzer  (2026-07-22)"
Cohesion: 0.18
Nodes (10): Community Hubs (Navigation), Corpus Check, God Nodes (most connected - your core abstractions), Graph Freshness, Graph Report - energy-procurement-risk-analyzer  (2026-07-22), Import Cycles, Knowledge Gaps, Suggested Questions (+2 more)

### Community 45 - "write-session-snap.js"
Cohesion: 0.29
Nodes (10): { execSync }, extractSessionContinuity(), findContinueHere(), findPlanningRoot(), fs, gitMeta(), parseFrontmatter(), path (+2 more)

### Community 46 - "Doc Ingest Synthesis Summary"
Cohesion: 0.18
Nodes (10): Conflicts, Constraints, Context topics, Cross-ref cycle detection, Decisions (locked), Doc counts by type, Doc Ingest Synthesis Summary, Intel files (+2 more)

### Community 47 - "Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.18
Nodes (10): Active, Constraints, Context, Core Value, Energy Procurement Risk Analyzer (EPRA), Key Decisions, Out of Scope, Requirements (+2 more)

### Community 48 - "ConsumerProfileCfg"
Cohesion: 0.22
Nodes (8): ConsumerProfileCfg, SPEC-03 §6 schema. YAML wins over spec prose if they diverge., build_profile(), monthly_volumes(), DataFrame, Consumer load profile construction — "StyriaMetal GmbH" (M4).  Not yet implement, SPEC-03 §2 entrypoint: hourly ``ts_utc, load_mwh`` frame, deterministic., Aggregate to ``year_local, month_local, volume_mwh`` (LP-021).

### Community 49 - "test_scripts.py"
Cohesion: 0.40
Nodes (9): CompletedProcess, Path, Tests for the implemented governance scripts (EN-003 token guard, ING-101)., _run(), test_oespi_reconcile_accepts_matching_entries(), test_oespi_reconcile_rejects_mismatch(), test_oespi_reconcile_requires_both_entries(), test_token_guard_allows_env_placeholder() (+1 more)

### Community 50 - "00 — MASTER PLAN: The Execution Operating System"
Cohesion: 0.20
Nodes (10): 00 — MASTER PLAN: The Execution Operating System, 0.1 What this blueprint is — and is not, 0.2 Document map (reading order for a new contributor), 0.3 Mission restated (one sentence, from Charter §1), 0.4 Execution model, 0.5 Task metadata conventions, 0.6 Global Definition of Ready (DoR), 0.7 Global Definition of Done (DoD) (+2 more)

### Community 51 - "Coding Conventions"
Cohesion: 0.20
Nodes (9): Code Style, Coding Conventions, Comments, Error Handling, Function Design, Import Organization, Logging, Module Design (+1 more)

### Community 52 - "Testing Patterns"
Cohesion: 0.20
Nodes (9): Common Patterns, Coverage, Fixtures and Factories, Mocking, Test File Organization, Test Framework, Test Structure, Test Types (+1 more)

### Community 53 - "maybe-graphify-update.js"
Cohesion: 0.31
Nodes (9): currentBranch(), defaultBranch(), findGraphifyBin(), fs, isHeadAdvancing(), maybeGraphifyUpdate(), path, readConfig() (+1 more)

### Community 54 - "Requirements: Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.20
Nodes (9): Analytical Questions (Charter Q1–Q4), Extensions, Governance & Quality, Out of Scope, Pipeline Capabilities, Requirements: Energy Procurement Risk Analyzer (EPRA), Traceability, v1 Requirements (+1 more)

### Community 55 - "format.py"
Cohesion: 0.20
Nodes (9): format_eur(), format_eur_millions(), format_eur_mwh(), format_pct(), Euro / unit formatting — the ONE shared formatter module (RP-703).  Conventions, Whole euros with thousands separators: 1234567.8 → ``€1,234,568``., Millions of euros: 1_420_000 → ``€1.42 M``., Unit price with 1 decimal: 123.456 → ``123.5 EUR/MWh``. (+1 more)

### Community 56 - "3. Build order and gates (from Charter §7 — expanded into agent tasks)"
Cohesion: 0.22
Nodes (9): 3. Build order and gates (from Charter §7 — expanded into agent tasks), M0 — Bootstrap, M1 — ENTSO-E ingestion, M2 — Auxiliary data, M3 — dbt warehouse, M4 — Consumer profile, M5 — Analytics, M6 — Strategies (+1 more)

### Community 57 - "07 — QUALITY STANDARDS (measurable thresholds)"
Cohesion: 0.22
Nodes (9): 07 — QUALITY STANDARDS (measurable thresholds), 7.1 Code, 7.2 Runtime & memory budgets, 7.3 Determinism & reproducibility (hard, all from SPECs), 7.4 Scientific correctness, 7.5 Data quality, 7.6 Visualization (RP-70x, restated as pass/fail), 7.7 Documentation completeness (+1 more)

### Community 58 - "SPEC-04 — Market Analytics (modules A1–A4)"
Cohesion: 0.22
Nodes (8): §5 Degree-day definitions, §6 Deliverables checklist for M5 (all must exist), §7 Gates (M5 exit), A1 — Descriptive market structure (`analytics/descriptive.py`), A2 — AT–DE-LU spread (`analytics/spread.py`), A3 — Volatility regimes (`analytics/regimes.py`), A4 — Weather & load sensitivity (`analytics/weather.py`, deliberately small), SPEC-04 — Market Analytics (modules A1–A4)

### Community 59 - "SPEC-06 — Reporting, Dashboard, README"
Cohesion: 0.22
Nodes (8): 1. Artifact inventory, 2. Executive charts (exactly these four, in `reports/executive_charts/`), 3. Chart data flow, 4. Power BI dashboard (manual step, precisely specified), 5. `reports/EXEC_SUMMARY.md` (≤ 2 pages, structure mandatory), 6. README.md structure (order mandatory), 7. Chart standards (apply to every PNG in the repo), SPEC-06 — Reporting, Dashboard, README

### Community 60 - "Architecture"
Cohesion: 0.22
Nodes (8): Architecture, Cross-Cutting Concerns, Data Flow, Entry Points, Error Handling, Key Abstractions, Layers, Pattern Overview

### Community 61 - "External Integrations"
Cohesion: 0.22
Nodes (8): APIs & External Services, Authentication & Identity, CI/CD & Deployment, Data Storage, Environment Configuration, External Integrations, Monitoring & Observability, Webhooks & Callbacks

### Community 62 - "Phase 1: M0 Bootstrap Verification Report"
Cohesion: 0.22
Nodes (8): Gaps Summary, Goal Achievement, Human Verification Required, Observable Truths, Phase 1: M0 Bootstrap Verification Report, Required Artifacts, Requirements Coverage, Verification Metadata

### Community 63 - "Fixed Issues"
Cohesion: 0.22
Nodes (8): CR-01: `iter_chunks` groups 3 raw calendar months without bounding the window to ING-030's 90-day maximum, CR-02: Error-detail fallback can leak the real `securityToken` via `str(exc)` when the HTTP error response has no body, Fixed Issues, Phase EPRA-02: Code Review Fix Report — M1 ENTSO-E Ingestion, Skipped Issues, WR-01: `latest_complete_month`'s "complete" check only requires >=1 row per UTC day, not full-hour coverage, WR-02: Cache and parquet-writer temp files are not process-unique — concurrent runs can race on the same `.tmp` path, WR-03: `_dataset_root`/`_now_utc` helpers are independently reimplemented across modules

### Community 64 - "load_consumer_profile"
Cohesion: 0.28
Nodes (9): load_consumer_profile(), load_strategy_config(), Any, Path, Load and validate ``config/consumer_profile.yaml`` (LP-002)., Load and validate ``config/strategies.yaml`` (ST-003)., _read_yaml(), test_consumer_profile_matches_spec03() (+1 more)

### Community 65 - "geosphere.py"
Cohesion: 0.22
Nodes (8): discover_station(), ingest(), main(), date, GeoSphere Austria ingestion — daily mean temperature, Graz (M2).  Not yet implem, ING-091 discovery: return the chosen station's id/name/lat/lon.      The result, Ingest daily temperatures into monthly parquet per SPEC-01 §7 contract., CLI: ``python -m epra.ingest.geosphere --start YYYY-MM-DD --end YYYY-MM-DD`` (IN

### Community 66 - "conftest.py"
Cohesion: 0.28
Nodes (8): _ensure_entsoe_fixtures_dir(), entsoe_fixtures_dir(), Path, Shared pytest fixtures for ingest tests — tmp_path-backed Settings and the commi, Create `tests/fixtures/entsoe/` with a placeholder README if it's empty.      Ru, `Settings` with `data_raw`, `data_cache`, and `reports` redirected to `tmp_path`, Path to the committed ENTSO-E fixture directory (ING-070, T1.03a)., tmp_settings()

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

### Community 72 - "db.py"
Cohesion: 0.29
Nodes (7): DuckDBPyConnection, connect(), Path, DuckDB warehouse access (DM-001).  One helper, one file: ``data/warehouse/epra.d, Absolute path of the DuckDB warehouse file., Open the project warehouse, creating its parent directory if needed., warehouse_path()

### Community 73 - "LIMITATIONS"
Cohesion: 0.25
Nodes (8): 1. The consumer load profile is constructed, not measured, 2. ÖSPI as forward/contract price proxy, 3. The fixed-price premium is an assumption, 4. The bootstrap cannot simulate an unprecedented regime, 5. Grid fees, taxes, and levies are excluded, 6. Data-quality caveats for 2025, 7. No forecast-skill claim, LIMITATIONS

### Community 74 - "Technology Stack"
Cohesion: 0.25
Nodes (7): Configuration, Frameworks, Key Dependencies, Languages, Platform Requirements, Runtime, Technology Stack

### Community 75 - "Codebase Structure"
Cohesion: 0.25
Nodes (7): Codebase Structure, Directory Layout, Directory Purposes, Key File Locations, Naming Conventions, Special Directories, Where to Add New Code

### Community 76 - "build-session-briefing.js"
Cohesion: 0.39
Nodes (7): buildSessionBriefing(), findContinueHere(), findPlanningRoot(), fs, headLines(), path, resolveRepoRoot()

### Community 77 - "Phase 2 — Validation Strategy"
Cohesion: 0.25
Nodes (7): Manual-Only Verifications, Per-Task Verification Map, Phase 2 — Validation Strategy, Sampling Rate, Test Infrastructure, Validation Sign-Off, Wave 0 Requirements

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

### Community 83 - "run-graphify-rebuild.js"
Cohesion: 0.29
Nodes (5): fs, path, { spawnSync }, status, [statusFile, lockFile, headSha, msStart, graphifyBin, repoRoot]

### Community 84 - "Onboarding Summary"
Cohesion: 0.29
Nodes (6): Authority hierarchy, Current position, Next command, Onboarding Summary, Open warnings (non-blocking), What was done

### Community 85 - "02-UAT.md"
Cohesion: 0.29
Nodes (6): 1. Live backfill produces four dataset trees under data/raw/, 2. make validate-ingest reports ING-080..085 PASS on real data, Current Test, Gaps, Summary, Tests

### Community 86 - "Energy Procurement Risk Analyzer (EPRA)"
Cohesion: 0.29
Nodes (7): Architecture, Data sources, Energy Procurement Risk Analyzer (EPRA), How to reproduce (once M1+ lands), License & author, Project status, What is real vs. modeled

### Community 87 - "reconcile"
Cohesion: 0.43
Nodes (6): main(), Path, ÖSPI double-entry reconciliation (ING-101).  Workflow: a human (or two independe, Diff the two transcriptions; write ``out`` only if they fully agree., _read(), reconcile()

### Community 88 - "StrategyCfg"
Cohesion: 0.33
Nodes (6): SPEC-05 §8 schema — all simulator tunables (ST-003)., StrategyCfg, compute_anchors(), DataFrame, Calibration anchors — 2019 reference prices and ÖSPI base values (M6).  Not yet, Return the four anchors as a one-row frame; persisted for SSOT (ST-204).

### Community 89 - "test_logging_and_db.py"
Cohesion: 0.33
Nodes (5): Shared infrastructure: settings, logging, time handling, warehouse access., Path, Tests for epra.common.logging (EN-060) and epra.common.db (DM-001)., test_db_connect_creates_warehouse(), test_logging_setup_is_idempotent()

### Community 90 - "calendar.py"
Cohesion: 0.29
Nodes (6): build_calendar(), main(), DataFrame, Calendar generation — hourly spine with Austrian/Styrian holidays (M2).  Not yet, Return the hourly calendar frame per ING-110 (also persisted to parquet)., CLI: ``python -m epra.ingest.calendar`` (ING-002).

### Community 91 - "oespi.py"
Cohesion: 0.29
Nodes (6): load_oespi(), main(), DataFrame, ÖSPI loader — hand-curated monthly index CSV (M2).  Not yet implemented. Binding, Load + gate-check the reconciled ÖSPI CSV; returns month-indexed frame., CLI: ``python -m epra.ingest.oespi`` — validate the committed CSV (ING-103).

### Community 92 - "_write_report"
Cohesion: 0.29
Nodes (6): _last_sunday(), date, Path, First day-of-month's last Sunday — used for the ING-080 DST check dates., Render the full report: header, overall status, then every gate section., _write_report()

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

### Community 97 - "ADR-005: latest_complete_month() = min(AT prices, DE-LU prices) (adopts SG-02)"
Cohesion: 0.33
Nodes (5): ADR-005: latest_complete_month() = min(AT prices, DE-LU prices) (adopts SG-02), Consequences, Context, Decision, Spec deviations

### Community 98 - "ADR-006: Validation gates assert over complete Vienna-local years within the ingested window"
Cohesion: 0.33
Nodes (5): ADR-006: Validation gates assert over complete Vienna-local years within the ingested window, Consequences, Context, Decision, Spec deviations

### Community 99 - "BUILD_LOG (append-only, per AGENTS.md W-5)"
Cohesion: 0.33
Nodes (5): 2026-07-19 — Execution Blueprint (planning deliverable, owner-requested), 2026-07-19 — M0 Bootstrap (complete) + breadth foundation, 2026-07-21 — M1 ENTSO-E Ingestion (automated deliverables complete; live-data gate pending operator), 2026-07-22 — M1 live backfill run: two data-loss bugs found and fixed, BUILD_LOG (append-only, per AGENTS.md W-5)

### Community 100 - "M4 — Consumer profile (SPEC-03)"
Cohesion: 0.33
Nodes (6): M4 — Consumer profile (SPEC-03), T4.01 — Weight engine (algorithm steps 1–4) `[CP]`, T4.02 — Normalization incl. partial years `[CP]`, T4.03 — Outputs: hourly parquet, monthly volumes, peak share `[CP]`, T4.04 — flat_baseload variant + golden/property/meta tests `[CP]`, T4.05 — `make profile` wiring + M4 PR `[CP]` — CLI entry, Makefile target un-stubbed, stub-test rows for M4 deleted, BUILD_LOG, PR per template.

### Community 101 - "Phase 1: M0 Bootstrap Summary"
Cohesion: 0.33
Nodes (5): Accomplishments, Files Created/Modified, Next Phase Readiness, Phase 1: M0 Bootstrap Summary, Task Commits

### Community 102 - "Info"
Cohesion: 0.33
Nodes (5): IN-01: `ingested_at_utc` provenance column is a plain ISO string, inconsistent with `ts_utc`'s tz-aware timestamp dtype, IN-02: Fixture provenance documentation is inconsistent between `conftest.py`'s README template and `test_raw_contracts.py`'s docstring, Info, Phase EPRA-02: Code Review Report — M1 ENTSO-E Ingestion (Iteration 2), Summary

### Community 103 - "check_file"
Cohesion: 0.47
Nodes (5): check_file(), main(), Path, Pre-commit guard: no ENTSO-E token literal anywhere in the repo (EN-003, A-7)., Return violation descriptions ('file:line') for one file.

### Community 104 - "ingest_dataset"
Cohesion: 0.33
Nodes (6): ingest_dataset(), Fetch, parse, and persist one §7 dataset over `[start, end]` (ING-001, ING-030)., _cache_request_url(), Deterministic, cache-key-only URL — never sent over the network.      `EntsoeR, sha256 hex digest of ``url`` with the ``securitytoken`` query param removed., request_hash()

### Community 105 - "style.py"
Cohesion: 0.40
Nodes (5): hybrid_color(), _interpolate_hex(), Chart style constants — colors defined ONCE, stable across every chart (RP-704)., Linear RGB interpolation between two hex colors, t ∈ [0, 1]., Color for HYBRID_h: interpolate S1 (spot, ratio 0) → S3 (fixed, ratio 1).

### Community 106 - "forward_risk.py"
Cohesion: 0.33
Nodes (5): main(), Forward risk engine — seasonal block bootstrap, next 12 months (M6, Q3).  Not ye, Simulate N seeded paths; write forward_risk_summary + charts., CLI: ``python -m epra.strategies.forward_risk`` (ST-002)., run()

### Community 107 - "retrospective.py"
Cohesion: 0.33
Nodes (5): main(), Retrospective engine — what each strategy actually cost, 2021-2025 (M6, Q1).  No, Compute cost(strategy, year, month) for 2021-2025 + sensitivities., CLI: ``python -m epra.strategies.retrospective`` (ST-002)., run()

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

### Community 114 - "Deferred Items — EPRA-02 M1 ENTSO-E Ingestion"
Cohesion: 0.40
Nodes (4): Deferred Items — EPRA-02 M1 ENTSO-E Ingestion, From 02-02 (raw parquet writer `_io`), From 02-05 (ingest orchestration, CLI, Makefile), From 02-06 (validation gate framework, `validate-ingest`)

### Community 115 - "logging.py"
Cohesion: 0.40
Nodes (4): Path, Logging setup — stdlib logging, one canonical format.  Implements: EN-060 (forma, Configure root logging: INFO to stdout; optionally also to ``logfile``.      Ide, setup()

### Community 117 - "02 — WORK BREAKDOWN STRUCTURE"
Cohesion: 0.50
Nodes (4): 02 — WORK BREAKDOWN STRUCTURE, TP.01 — Activate ENTSO-E token `[HUMAN]` `[CP]`, TP.02 — GitHub remote, branch protection, CI secret `[HUMAN]`, TP — Preparatory / operations tasks

### Community 118 - "Synthesized Decisions (ADRs)"
Cohesion: 0.50
Nodes (3): ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored, ADR-002: Dev-only typing-stub packages for mypy --strict, Synthesized Decisions (ADRs)

### Community 119 - "4. Scope"
Cohesion: 0.50
Nodes (4): 4.1 In scope, 4.2 Explicitly OUT of scope (do not build these, even if tempting), 4.3 Analysis window, 4. Scope

### Community 120 - "descriptive.py"
Cohesion: 0.50
Nodes (3): A1 — Descriptive market structure (M5).  Not yet implemented. Binding contract:, Produce all A1 artifacts from marts; deterministic (AN-705)., run()

### Community 121 - "regimes.py"
Cohesion: 0.50
Nodes (3): A3 — Volatility regimes: HMM + GARCH complement (M5, build LAST).  Not yet imple, Produce all A3 artifacts from marts; seeded, deterministic (AN-705)., run()

### Community 122 - "spread.py"
Cohesion: 0.50
Nodes (3): A2 — AT vs DE-LU spread (M5).  Not yet implemented. Binding contract: SPEC-04 A2, Produce all A2 artifacts from marts; deterministic (AN-705)., run()

### Community 123 - "weather.py"
Cohesion: 0.50
Nodes (3): A4 — Weather & load sensitivity (M5, deliberately small).  Not yet implemented., Produce a4_load_vs_hdd.png + a4_load_weather.md from marts., run()

### Community 124 - "charts.py"
Cohesion: 0.50
Nodes (3): Executive + module charts (M5/M7).  Not yet implemented. Binding contracts: SPEC, Write the four executive PNGs to reports/executive_charts/., render_executive_charts()

## Knowledge Gaps
- **808 isolated node(s):** `fs`, `path`, `fs`, `path`, `{ spawn, execSync }` (+803 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `entsoe.py`, `test_entsoe_orchestration.py`, `test_io.py`, `_fetch.py`, `run_gates`, `test_fetch.py`, `validate.py`, `_io.py`, `load_settings`, `config.py`, `geosphere.py`, `conftest.py`, `db.py`, `StrategyCfg`, `calendar.py`, `oespi.py`, `_write_report`, `ingest_dataset`, `forward_risk.py`, `retrospective.py`, `descriptive.py`, `regimes.py`, `spread.py`, `weather.py`, `charts.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `02 — WORK BREAKDOWN STRUCTURE` connect `02 — WORK BREAKDOWN STRUCTURE` to `M3 — dbt warehouse (SPEC-02)`, `M4 — Consumer profile (SPEC-03)`, `M5 — Analytics (SPEC-04) — order A1→A2→A4→A3`, `M7 — Reporting, dashboard, refresh, release (SPEC-06, SPEC-07 §8)`, `M6 — Strategies (SPEC-05) — the heart; sequence is mandatory`, `M2 — Auxiliary data (SPEC-01 §§9–11) — merge FIRST (R-1)`, `00_MASTER_PLAN.md`, `M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `Settings` (e.g. with `_DatasetSpec` and `EntsoeQuery`) actually correct?**
  _`Settings` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fs`, `path`, `fs` to the rest of the system?**
  _808 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Communities (137 total, 18 thin omitted)` be split into smaller, more focused modules?**
  _Cohesion score 0.01694915254237288 - nodes in this community are weakly interconnected._
- **Should `entsoe.py` be split into smaller, more focused modules?**
  _Cohesion score 0.056429463171036205 - nodes in this community are weakly interconnected._
- **Should `test_entsoe_orchestration.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._