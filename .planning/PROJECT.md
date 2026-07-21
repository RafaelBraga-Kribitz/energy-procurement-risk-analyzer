# Energy Procurement Risk Analyzer (EPRA)

## What This Is

A reproducible batch analytics pipeline that quantifies how much a 50 GWh/year Styrian industrial consumer paid (or would pay) under four electricity procurement strategies across 2021–2025, and estimates forward P95 cost exposure. Built for portfolio demonstration to Austrian energy-sector hiring managers — README leads with euro answers, not stack.

## Core Value

Answer the headline question: *How much did buying electricity the wrong way cost in 2021–2025 — and what is P95 exposure for the next 12 months per strategy?*

## Requirements

### Validated

- [x] M0 bootstrap — repo layout, Makefile, CI, smoke tests (Charter M0)

### Active

- [ ] M1 ENTSO-E ingestion with validation gates
- [ ] M2 auxiliary data (GeoSphere, ÖSPI, calendar)
- [ ] M3 dbt warehouse on DuckDB
- [ ] M4 consumer load profile
- [ ] M5 market analytics
- [ ] M6 strategy simulator + SSOT
- [ ] M7 reporting, dashboard handoff, refresh cron

### Out of Scope

- Price forecasting (O-1) — bootstrap on realized prices only
- Apps/APIs (O-4) — Power BI on CSV exports is the interactive deliverable
- Heavy governance kit (O-5) — light SPEC-08 governance only per ADR-001
- Grid fees, taxes, demand response (O-3)
- More than four strategy families (O-7)

## Context

Brownfield repo with M0 complete (`make setup && make lint && make test` green). Domain modules (`ingest`, `consumer`, `analytics`, `strategies`) are typed stubs. Authority: `PROJECT_CHARTER.md` > `docs/SPEC-01..08` > ADRs > execution blueprint. Ingested 11 planning docs (2026-07-21); see `.planning/intel/SYNTHESIS.md`.

## Constraints

- **Data**: Real ENTSO-E, ÖSPI, GeoSphere only — no synthetic prices (P-1)
- **Determinism**: Seeded stochastic steps; `make all` twice = identical SSOT (A-4)
- **Numbers**: README/EXEC_SUMMARY numbers only from `reports/NUMERIC_SSOT.md` (GV-303)
- **Stack**: Python 3.12, uv, DuckDB, dbt, pytest ≥80% coverage (SPEC-07)
- **Timezone**: Store UTC, analyze Europe/Vienna (T-1)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| No governance-bootstrap kit (ADR-001) | Charter O-5 caps governance weight | ✓ Good |
| Dev typing stubs for mypy strict (ADR-002) | EN-002 meaningful strict checking | ✓ Good |
| SPECs are implementation authority | Charter §9 build order | — Pending execution |
| SG gaps non-binding until ADR | GV-201..203 | — Pending (see INGEST-CONFLICTS) |

---
*Last updated: 2026-07-21 after docs ingest*
