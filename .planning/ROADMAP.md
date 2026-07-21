# Roadmap: Energy Procurement Risk Analyzer

## Overview

Deliver a reproducible pipeline from real Austrian market data through dbt marts to strategy cost comparison and forward risk — aligned to Charter milestones M0–M7. M0 is shipped; execution begins at M1 ENTSO-E ingestion.

## Phases

- [x] **Phase 1: M0 Bootstrap** — Repo layout, tooling, CI, smoke tests
- [ ] **Phase 2: M1 ENTSO-E Ingestion** — Prices, load, generation with validation
- [ ] **Phase 3: M2 Auxiliary Data** — GeoSphere, ÖSPI, calendar
- [ ] **Phase 4: M3 dbt Warehouse** — Staging + marts on DuckDB
- [ ] **Phase 5: M4 Consumer Profile** — Deterministic StyriaMetal load
- [ ] **Phase 6: M5 Analytics** — Market structure analytics A1–A4
- [ ] **Phase 7: M6 Strategy Simulator** — Retrospective, forward risk, SSOT
- [ ] **Phase 8: M7 Reporting & Refresh** — Exports, exec report, dashboard handoff, cron

## Phase Details

### Phase 1: M0 Bootstrap
**Goal**: Runnable repo with quality gates and stub module layout  
**Depends on**: Nothing  
**Requirements**: ENG-01 (partial), ENG-02 (partial)  
**Success Criteria**:
  1. `make setup && make lint && make test` passes locally and in CI
  2. Repo layout matches SPEC-07 §2
  3. All Makefile targets exist (stubs fail loudly)
**Plans**: TBD

### Phase 2: M1 ENTSO-E Ingestion
**Goal**: Real ENTSO-E data in `data/raw/` with validation report  
**Depends on**: Phase 1  
**Requirements**: DATA-01  
**Success Criteria**:
  1. ING-070..085 contract tests green on 2019→latest backfill
  2. 15-min aggregation and DST fixtures pass
  3. `make validate-ingest` produces committed validation report
**Plans**: TBD

### Phase 3: M2 Auxiliary Data
**Goal**: Temperature, ÖSPI, and calendar pipelines operational  
**Depends on**: Phase 2  
**Requirements**: DATA-02  
**Success Criteria**:
  1. ING-094/101/103/111 gates green
  2. `data/manual/oespi_monthly.csv` double-entry reconciled
  3. GeoSphere station ADR'd if discovery differs
**Plans**: TBD

### Phase 4: M3 dbt Warehouse
**Goal**: Tested analytical warehouse with contract marts  
**Depends on**: Phase 3  
**Requirements**: DATA-03  
**Success Criteria**:
  1. `dbt build` green on real data and CI fixtures
  2. Mart schemas byte-match SPEC-02 §5 contract YAML
  3. Fixture bootstrap script enables CI without full data
**Plans**: TBD

### Phase 5: M4 Consumer Profile
**Goal**: Deterministic hourly load for all strategies  
**Depends on**: Phase 4  
**Requirements**: DATA-04  
**Success Criteria**:
  1. LP-040..042 golden + property tests pass
  2. Annual sum = 50,000.00 MWh ± 0.01 per local year
  3. `consumer_peak_share` in SSOT inputs
**Plans**: TBD

### Phase 6: M5 Analytics
**Goal**: Descriptive market analytics answering Q2  
**Depends on**: Phase 5  
**Requirements**: Q2-01  
**Success Criteria**:
  1. AN-701..705 gates pass including crisis-regime sanity (AN-304)
  2. Charts obey SPEC-06 §7 caption rules
  3. Artifacts in `reports/analytics/` pass plausibility gates
**Plans**: TBD

### Phase 7: M6 Strategy Simulator
**Goal**: Retrospective + forward risk + NUMERIC_SSOT  
**Depends on**: Phase 6  
**Requirements**: Q1-01, Q3-01, GOV-01  
**Success Criteria**:
  1. ST-601..604 gates pass; ST-602 sanity relations hold
  2. Golden metrics test green; bootstrap seeded and reproducible
  3. `reports/NUMERIC_SSOT.md` generated with cost matrix + forward table
**Plans**: TBD

### Phase 8: M7 Reporting & Refresh
**Goal**: Ship all DL-1..DL-10 deliverables  
**Depends on**: Phase 7  
**Requirements**: Q4-01, RPT-01, OPS-01, ENG-01, ENG-02  
**Success Criteria**:
  1. README leads with euro answer traceable to SSOT
  2. EXEC_SUMMARY, LIMITATIONS, exports complete
  3. Monthly refresh workflow live; dashboard handoff docs ready
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. M0 Bootstrap | — | Complete | 2026-07-19 |
| 2. M1 ENTSO-E | 0/TBD | Not started | - |
| 3. M2 Auxiliary | 0/TBD | Not started | - |
| 4. M3 dbt | 0/TBD | Not started | - |
| 5. M4 Profile | 0/TBD | Not started | - |
| 6. M5 Analytics | 0/TBD | Not started | - |
| 7. M6 Strategies | 0/TBD | Not started | - |
| 8. M7 Reporting | 0/TBD | Not started | - |
