# Energy Procurement Risk Analyzer (EPRA)

## What This Is

A spec-driven batch Python pipeline that quantifies the euro cost of wrong electricity procurement for a 50 GWh/year Styrian manufacturer. It answers four analytical questions (Q1–Q4) using real ENTSO-E, ÖSPI, and GeoSphere data (2019→latest), a calibrated load profile, four procurement strategies, and a block-bootstrap forward risk model — then publishes the answer in euros via README and `reports/NUMERIC_SSOT.md`. The interactive deliverable is Power BI on exported CSVs; there is no app or API.

Built for hiring managers and senior analysts at Austrian energy companies and industrial procurement teams who read business documents first.

## Core Value

Quantify the euro cost of wrong electricity procurement for a 50 GWh/year Styrian manufacturer (2021–2025 retrospective + forward P95 exposure), with every headline number traceable to `reports/NUMERIC_SSOT.md`.

## Requirements

### Validated

- ✓ **REQ-ENG-01**: Reproducible engineering baseline (uv, Makefile, ruff, mypy, pre-commit, pytest smoke, CI) — Phase 1 / M0

### Active

- [ ] **REQ-Q1**: Retrospective strategy costs 2021–2025 in EUR and EUR/MWh (Charter Q1, DL-2)
- [ ] **REQ-Q2**: Market structure analytics driving strategy differences (Charter Q2, DL-3)
- [ ] **REQ-Q3**: Forward 12-month cost distribution per strategy (mean, P5, P50, P95, CVaR95) (Charter Q3, DL-4)
- [ ] **REQ-Q4**: CFO recommendation — risk-averse vs cost-minimizing choice with price of risk reduction (Charter Q4, DL-5)
- [ ] **REQ-ING-01**: Real market data ingestion with validation gates (D1–D4, SPEC-01)
- [ ] **REQ-DWH-01**: DuckDB + dbt warehouse with contract-tested marts (SPEC-02)
- [ ] **REQ-LP-01**: Deterministic calibrated consumer load profile (SPEC-03)
- [ ] **REQ-ANA-01**: Market analytics modules A1–A4 with plausibility gates (SPEC-04)
- [ ] **REQ-ST-01**: Procurement strategy simulator — retrospective + forward bootstrap (SPEC-05)
- [ ] **REQ-RPT-01**: Executive reporting, exports, Power BI handoff, monthly refresh (SPEC-06, DL-1, DL-6, DL-8, DL-10)
- [ ] **REQ-GOV-01**: SSOT generation, CI numeric consistency, epistemic tags, and LIMITATIONS.md (SPEC-08, DL-7, DL-9)

### Out of Scope

- Price forecasting models — evaluates against realized prices and bootstrap resampling only (Charter O-1)
- Intraday, balancing, or futures microstructure (Charter O-2)
- Grid fees, taxes, levies, PPAs, on-site generation, batteries, demand response (Charter O-3)
- FastAPI, Streamlit, or any hosted backend — Power BI on CSV exports is the interactive deliverable (Charter O-4)
- Heavy governance machinery beyond SPEC-08 light governance (Charter O-5; locked ADR-001)
- Gas, heat, or commodities other than electricity (Charter O-6)
- More than four strategy families S1–S4 (Charter O-7)

## Context

**Brownfield state (2026-07-20):** M0 bootstrap is complete. `src/epra/common/` and `src/epra/report/` format/style helpers are implemented; domain modules (`ingest`, `consumer`, `analytics`, `strategies`) are typed stubs raising `NotImplementedError`. dbt project skeleton exists; Makefile pipeline targets are wired but unimplemented stages fail loudly.

**Authority hierarchy:** PROJECT_CHARTER.md → docs/SPEC-01..08 → docs/ADR/* → docs/EXECUTION_BLUEPRINT/ (non-binding proposals until ADR adoption).

**Ingest warnings (informational):** SG-01 (EntsoeRawClient vs entsoe-py raw cache) and SG-14 (holiday-aware peak definition) pending ADR adoption at implementation time — see `.planning/INGEST-CONFLICTS.md`.

**Runtime:** Cursor + Claude Code; batch Python pipeline orchestrated via Makefile; human builds Power BI `.pbix` at M7. Cross-runtime continuity: `.planning/CONTINUITY.md` (SSOT = `.planning/`; pause with `/gsd-pause-work`, resume with `/gsd-resume-work`).

**Reference consumer:** StyriaMetal GmbH — 50,000 MWh/year, parameters in `config/consumer_profile.yaml` only.

**Success metric:** DL-1..DL-10 all green; README leads with euro answer traceable to NUMERIC_SSOT.md.

## Constraints

- **Spec supremacy**: Code implements SPEC REQ IDs; silent deviation forbidden — ADR required (AGENTS A-1)
- **No invented data**: Gaps stay NULL; validation gates fail fast (AGENTS A-2, Charter P-1..P-3)
- **Determinism**: Seeded stochastic steps; two `make all` runs produce identical SSOT (AGENTS A-4)
- **Secrets**: `ENTSOE_API_TOKEN` env var only; never logged or committed (AGENTS A-7)
- **Tech stack**: Python 3.12, uv, DuckDB, dbt-duckdb, entsoe-py, pytest, ruff, mypy --strict (SPEC-07)
- **Timezone**: Stored UTC; analytic Europe/Vienna local (T-1)
- **Numbers**: README/exec summary numbers only from `reports/NUMERIC_SSOT.md` (AGENTS A-6)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored | Charter O-5 caps governance weight; governance is exactly epistemic tags (GV-101/102), append-only ADRs (GV-201..203), and SSOT mechanism with CI check (GV-301..303) plus SPEC-07 §8 CI gates | ✓ Locked |
| ADR-002: Dev-only typing stubs (`pandas-stubs`, `types-PyYAML`, `types-requests`); `statsmodels` ignore_missing_imports | Preserve EN-002 mypy --strict on own code without runtime stub dependencies | ✓ Locked |
| Makefile as canonical operator interface | Single entry point for local ops and CI cron; EN-050 | — Pending |
| DuckDB warehouse as sole boundary between ingest and analytics | Prevents cross-layer imports; mart reader pattern | — Pending |
| ÖSPI as forward-price proxy (not EEX futures) | Charter P-2; documented approximation in LIMITATIONS | — Pending |

---
*Last updated: 2026-07-21 after new-project-from-ingest initialization*
