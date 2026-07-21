# Requirements: Energy Procurement Risk Analyzer

**Defined:** 2026-07-21  
**Core Value:** Quantify euro cost of wrong procurement (2021–2025) + forward P95 exposure per strategy

## v1 Requirements

### Analytics (Q1–Q4)

- [ ] **Q1-01**: Retrospective strategy costs 2021–2025 in EUR and EUR/MWh (DL-2)
- [ ] **Q2-01**: Market analytics artifacts pass SPEC-04 plausibility gates (DL-3)
- [ ] **Q3-01**: Forward 12-month cost distribution per strategy, seed-reproducible (DL-4)
- [ ] **Q4-01**: EXEC_SUMMARY CFO recommendation ≤2 pages (DL-5)

### Data & Pipeline

- [ ] **DATA-01**: ENTSO-E ingestion with ING-070..085 gates green (M1)
- [ ] **DATA-02**: GeoSphere, ÖSPI, calendar ingested (M2)
- [ ] **DATA-03**: dbt build green; mart schemas match SPEC-02 §5 (M3)
- [ ] **DATA-04**: Deterministic consumer profile; annual 50,000 MWh ±0.01 (M4)

### Engineering & Governance

- [ ] **ENG-01**: `make setup && make all` reproducible end-to-end (DL-1)
- [ ] **ENG-02**: Tests, lint, dbt, coverage ≥80%, CI green (DL-7)
- [ ] **GOV-01**: Epistemic tags, LIMITATIONS, SSOT-only public numbers (DL-9, DL-10)
- [ ] **OPS-01**: Monthly refresh cron rebuilds marts + SSOT (DL-8)
- [ ] **RPT-01**: Power BI dashboard + screenshots per SPEC-06 (DL-6)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Price forecasting | Charter O-1 |
| Web app / API | Charter O-4 |
| Governance-bootstrap kit | ADR-001, Charter O-5 |
| Fifth+ strategy family | Charter O-7 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENG-01 (partial) | Phase 1: M0 Bootstrap | Complete |
| ENG-02 (partial) | Phase 1: M0 Bootstrap | Complete |
| DATA-01 | Phase 2: M1 ENTSO-E Ingestion | Pending |
| DATA-02 | Phase 3: M2 Auxiliary Data | Pending |
| DATA-03 | Phase 4: M3 dbt Warehouse | Pending |
| DATA-04 | Phase 5: M4 Consumer Profile | Pending |
| Q2-01 | Phase 6: M5 Analytics | Pending |
| Q1-01, Q3-01, GOV-01 | Phase 7: M6 Strategy Simulator | Pending |
| Q4-01, RPT-01, OPS-01 | Phase 8: M7 Reporting & Refresh | Pending |

**Coverage:** 14 v1 requirements — 14 mapped — 0 unmapped

---
*Requirements defined: 2026-07-21 via docs ingest*
