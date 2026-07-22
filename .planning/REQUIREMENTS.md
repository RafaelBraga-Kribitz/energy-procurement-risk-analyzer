# Requirements: Energy Procurement Risk Analyzer (EPRA)

**Defined:** 2026-07-21
**Core Value:** Quantify the euro cost of wrong electricity procurement for a 50 GWh/year Styrian manufacturer (2021–2025 retrospective + forward P95 exposure)

## v1 Requirements

Requirements for initial release. Each maps to exactly one roadmap phase (Charter milestones M0–M7).

### Analytical Questions (Charter Q1–Q4)

- [ ] **REQ-Q1**: Pipeline produces the 5-year × 4-strategy cost matrix in EUR and EUR/MWh plus the "cost of the wrong strategy" headline (max − min per year) in `reports/NUMERIC_SSOT.md` (DL-2)
- [ ] **REQ-Q2**: Pipeline produces market structure analytics artifacts in `reports/analytics/` per SPEC-04 §6, each passing plausibility gates (DL-3)
- [ ] **REQ-Q3**: Pipeline produces forward-risk table (mean/P5/P50/P95/CVaR95 per strategy) in SSOT, seed-reproducible (DL-4)
- [ ] **REQ-Q4**: `reports/EXEC_SUMMARY.md` (≤ 2 pages) delivers the CFO recommendation — risk-averse vs cost-minimizing choice and price of risk reduction in EUR (DL-5)

### Pipeline Capabilities

- [x] **REQ-ENG-01**: Fresh clone runs `make setup && make lint && make test` green locally and in CI; Makefile skeleton, ruff/pre-commit, pytest smoke, pinned deps per SPEC-07 (M0)
- [ ] **REQ-ING-01**: ENTSO-E (AT + DE-LU prices, AT load, AT generation), GeoSphere temperature, ÖSPI manual CSV (double-entry), and calendar/holidays ingested with validation gates green for 2019→latest (SPEC-01, M1+M2)
- [ ] **REQ-DWH-01**: `dbt build` green on real data and CI fixtures; mart schemas byte-match SPEC-02 §5 contract YAML (M3)
- [ ] **REQ-LP-01**: Deterministic consumer load profile with golden test; annual sum = 50,000.00 MWh ± 0.01 per local year; `consumer_peak_share` in SSOT inputs (SPEC-03, M4)
- [ ] **REQ-ANA-01**: Analytics modules A1–A4 complete with SPEC-04 §7 exit gates including crisis-regime sanity gate AN-304 (M5)
- [ ] **REQ-ST-01**: Strategy simulator — calibration, retrospective S1–S4, forward block bootstrap, golden metrics and ST-602 sanity relations pass (SPEC-05, M6)
- [ ] **REQ-RPT-01**: Exports to `exports/`, executive charts, Power BI handoff docs, README per SPEC-06 §6 leading with euro answer, monthly refresh cron live (SPEC-06, M7; DL-1, DL-6, DL-8, DL-10)

### Governance & Quality

- [ ] **REQ-GOV-01**: `reports/NUMERIC_SSOT.md` auto-generated only by `scripts/generate_ssot.py`; CI `check_ssot_consistency.py` passes; epistemic tags on headline numbers; `LIMITATIONS.md` covers SPEC-08 §6 (DL-7, DL-9)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extensions

- **V2-01**: Additional procurement strategy families beyond S1–S4
- **V2-02**: Grid fees, taxes, and levies in total cost of energy
- **V2-03**: Price forecasting models with claimed forecast skill
- **V2-04**: Hosted web app or API for interactive exploration

## Out of Scope

Explicitly excluded per Charter §4.2. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Price forecasting | Charter O-1; bootstrap of realized prices only |
| Intraday/balancing/futures microstructure | Charter O-2 |
| Grid fees, taxes, PPAs, on-site gen, batteries, DR | Charter O-3; isolates procurement lever |
| FastAPI / Streamlit / hosted backend | Charter O-4; Power BI on CSV exports |
| Heavy governance-bootstrap kit | Charter O-5; ADR-001 locked |
| Non-electricity commodities | Charter O-6 |
| Fifth+ strategy family | Charter O-7 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-ENG-01 | Phase 1 (M0) | Complete |
| REQ-ING-01 | Phase 3 (M2) | Pending (M1/Phase 2 ENTSO-E slice implemented; completes at M2) |
| REQ-DWH-01 | Phase 4 (M3) | Pending |
| REQ-LP-01 | Phase 5 (M4) | Pending |
| REQ-ANA-01 | Phase 6 (M5) | Pending |
| REQ-Q2 | Phase 6 (M5) | Pending |
| REQ-ST-01 | Phase 7 (M6) | Pending |
| REQ-Q1 | Phase 7 (M6) | Pending |
| REQ-Q3 | Phase 7 (M6) | Pending |
| REQ-RPT-01 | Phase 8 (M7) | Pending |
| REQ-Q4 | Phase 8 (M7) | Pending |
| REQ-GOV-01 | Phase 8 (M7) | Pending |

**Coverage:**

- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

**Note:** Phase 2 (M1) implements ENTSO-E ingestion as progress toward REQ-ING-01; the requirement completes when Phase 3 auxiliary gates pass. Phase 7 generates SSOT; REQ-GOV-01 completes at Phase 8 when CI consistency, tags, and LIMITATIONS are all green.

---
*Requirements defined: 2026-07-21*
*Last updated: 2026-07-21 after roadmap creation*
