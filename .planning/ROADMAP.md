# Roadmap: Energy Procurement Risk Analyzer (EPRA)

## Overview

Deliver a reproducible batch pipeline from real Austrian market data through dbt marts to strategy cost comparison and forward risk — aligned to Charter milestones M0–M7. M0 is shipped; execution begins at M1 ENTSO-E ingestion. Success is DL-1..DL-10 all green with README leading in euros traceable to `reports/NUMERIC_SSOT.md`.

## Phases

**Phase Numbering:** Phases 1–8 map 1:1 to Charter milestones M0–M7.

- [x] **Phase 1: M0 Bootstrap** — Repo layout, tooling, CI, smoke tests (shipped)
- [ ] **Phase 2: M1 ENTSO-E Ingestion** — Prices, load, generation with validation
- [x] **Phase 3: M2 Auxiliary Data** — GeoSphere, ÖSPI, calendar (completed 2026-07-23)
- [ ] **Phase 4: M3 dbt Warehouse** — Staging + marts on DuckDB
- [ ] **Phase 5: M4 Consumer Profile** — Deterministic StyriaMetal load
- [ ] **Phase 6: M5 Analytics** — Market structure analytics A1–A4
- [ ] **Phase 7: M6 Strategy Simulator** — Retrospective, forward risk, SSOT
- [ ] **Phase 8: M7 Reporting & Refresh** — Exports, exec report, dashboard handoff, cron

## Phase Details

### Phase 1: M0 Bootstrap

**Goal**: A fresh clone can run quality gates and the Makefile pipeline skeleton fails loudly until domain milestones ship
**Depends on**: Nothing (first phase)
**Requirements**: REQ-ENG-01
**Success Criteria** (what must be TRUE):

  1. Operator runs `make setup && make lint && make test` and all three pass locally and in CI
  2. Repository layout matches SPEC-07 §2 with `src/epra/` package and dbt skeleton present
  3. Every Makefile pipeline target exists; unimplemented stages exit non-zero with a milestone message

**Plans**: TBD

### Phase 2: M1 ENTSO-E Ingestion

**Goal**: Real ENTSO-E market data lands in validated raw parquet for 2019→latest
**Depends on**: Phase 1
**Requirements**: (progress toward REQ-ING-01)
**Success Criteria** (what must be TRUE):

  1. Operator runs `make backfill` with a valid token and AT/DE-LU prices, AT load, and AT generation appear under `data/raw/`
  2. ING-070 contract tests and 15-min aggregation + DST fixtures pass in CI
  3. `make validate-ingest` produces a validation report with ING-080..085 gates green on real data

**Plans**: 7/7 plans executed

Plans:

- [x] 02-01-PLAN.md — Wave 0 ADRs (SG-01, pyarrow, SG-02), exceptions, conftest
- [x] 02-02-PLAN.md — Raw parquet writer (_io) with atomic monthly writes
- [x] 02-03-PLAN.md — ENTSO-E fetch transport (_fetch) cache, retry, politeness
- [x] 02-04-PLAN.md — XML parsers, fixtures, ING-062 hourly mean (TDD)
- [x] 02-05-PLAN.md — Backfill/incremental orchestration, CLI, Makefile
- [x] 02-06-PLAN.md — Validation gates ING-080..085 and validate-ingest
- [x] 02-07-PLAN.md — ING-070 contract tests, live backfill checkpoint, BUILD_LOG

### Phase 3: M2 Auxiliary Data

**Goal**: All non-ENTSO-E sources ingested and ingestion layer complete
**Depends on**: Phase 2
**Requirements**: REQ-ING-01
**Success Criteria** (what must be TRUE):

  1. GeoSphere daily temperature, reconciled ÖSPI CSV, and calendar parquet are present and gate-clean
  2. ING-094/101/103/111 gates pass; `data/manual/oespi_monthly.csv` is double-entry reconciled
  3. Full ingestion validation suite passes for 2019→latest complete month

**Plans**: 6/6 plans executed

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Extend _io.write_month with additive key_column (date-grain writes for GeoSphere)
- [x] 03-02-PLAN.md — Calendar hourly spine (ING-110/111): Styrian holidays, DST, timeutil peak flags

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-03-PLAN.md — GeoSphere station discovery (ING-091) + ADR-007, live-first/fixture-fallback

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-04-PLAN.md — GeoSphere ingest + ING-094 gate + §7 raw-contract row (date-keyed)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 03-05-PLAN.md — ÖSPI loader + ING-103 gates + ADR-008 + synthetic CSV (ships without real data)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 03-06-PLAN.md — M2 assembly: validate-ingest full suite + real ÖSPI/GeoSphere human checkpoint

### Phase 4: M3 dbt Warehouse

**Goal**: Analysts and simulators read contract-tested marts from DuckDB — no raw parquet in analytics code
**Depends on**: Phase 3
**Requirements**: REQ-DWH-01
**Success Criteria** (what must be TRUE):

  1. Operator runs `dbt build` on real data and all models + tests pass
  2. Mart schemas byte-match the committed SPEC-02 §5 contract YAML
  3. CI fixture bootstrap enables `dbt build` green without a full local backfill

**Plans**: 6/8 plans executed

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Sources + generate_schema_name macro + month_spine/accepted_range helpers + ADR-009 (T3.01)

**Wave 2** *(blocked on Wave 1)*

- [x] 04-02-PLAN.md — 8 staging models + staging.yml (dedup, hourly mean/n_subhours, DM-020) (T3.02)

**Wave 3** *(blocked on Wave 2)*

- [x] 04-03-PLAN.md — dim_calendar (weather join, season, degree-days, no TZ calls) + dims.yml (T3.03)

**Wave 4** *(blocked on Wave 3; 04-04 and 04-05 run in parallel)*

- [x] 04-04-PLAN.md — Price & generation marts (fct_price_hourly/daily/monthly, fct_generation_monthly) + ADR-011 + LIMITATIONS §2 (T3.04a)
- [x] 04-05-PLAN.md — Fixture/stand-in generator + future marts (fct_consumer_load_hourly, fct_procurement_cost_monthly) + ADR-010 (T3.04b/T3.06 generator)

**Wave 5** *(blocked on Wave 4)*

- [x] 04-06-PLAN.md — dbt test suite DM-050/062/064/065/066 + marts_contract.yml + schema-contract pytest (T3.05)

**Wave 6** *(blocked on Wave 5)*

- [ ] 04-07-PLAN.md — Build-report writer (D-02) + Makefile transform/warehouse targets (T3.05/operator interface)

**Wave 7** *(blocked on Wave 6)*

- [ ] 04-08-PLAN.md — CI dbt-check job + phase close-out (real+CI builds green, BUILD_LOG, M3 PR) (T3.06/T3.07)

### Phase 5: M4 Consumer Profile

**Goal**: Deterministic hourly load profile available for all strategy cost calculations
**Depends on**: Phase 4
**Requirements**: REQ-LP-01
**Success Criteria** (what must be TRUE):

  1. Golden and property tests (LP-040..042) pass with fixed seed/config
  2. Each local calendar year sums to 50,000.00 MWh ± 0.01 after normalization
  3. `consumer_peak_share` is computed and ready for SSOT inputs

**Plans**: TBD

### Phase 6: M5 Analytics

**Goal**: Reviewer can read market structure evidence answering Charter Q2
**Depends on**: Phase 5
**Requirements**: REQ-ANA-01, REQ-Q2
**Success Criteria** (what must be TRUE):

  1. Analytics artifacts in `reports/analytics/` match SPEC-04 §6 enumeration and pass plausibility gates
  2. Crisis-regime sanity gate AN-304 passes on real 2021–2023 data
  3. Charts carry epistemic tags and obey SPEC-06 §7 caption rules

**Plans**: TBD

### Phase 7: M6 Strategy Simulator

**Goal**: Reviewer can read retrospective costs and forward risk distributions answering Charter Q1 and Q3
**Depends on**: Phase 6
**Requirements**: REQ-ST-01, REQ-Q1, REQ-Q3
**Success Criteria** (what must be TRUE):

  1. ST-601..604 gates pass; ST-602 sanity relations hold (calibration checked first if (a) fails)
  2. Two consecutive runs with the same seed produce identical SSOT numeric values
  3. `reports/NUMERIC_SSOT.md` contains the 5-year cost matrix and forward-risk table with correct epistemic tags

**Plans**: TBD

### Phase 8: M7 Reporting & Refresh

**Goal**: Project meets full Definition of Done — DL-1..DL-10 green
**Depends on**: Phase 7
**Requirements**: REQ-RPT-01, REQ-Q4, REQ-GOV-01
**Success Criteria** (what must be TRUE):

  1. Fresh clone with token runs `make setup && make all` end-to-end without manual intervention
  2. README leads with the euro answer; every quoted number passes `check_ssot_consistency.py`
  3. EXEC_SUMMARY, LIMITATIONS, exports, dashboard handoff docs, and monthly refresh cron are live; test coverage ≥ 80%

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → … → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. M0 Bootstrap | 0/TBD | Complete | 2026-07-19 |
| 2. M1 ENTSO-E | 7/7 | In Progress|  |
| 3. M2 Auxiliary | 6/6 | Complete    | 2026-07-23 |
| 4. M3 dbt | 6/8 | In Progress|  |
| 5. M4 Profile | 0/TBD | Not started | - |
| 6. M5 Analytics | 0/TBD | Not started | - |
| 7. M6 Strategies | 0/TBD | Not started | - |
| 8. M7 Reporting | 0/TBD | Not started | - |
