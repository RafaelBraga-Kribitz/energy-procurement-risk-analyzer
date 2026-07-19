# Energy Procurement Risk Analyzer (EPRA)

Quantifies electricity procurement strategy risk on the Austrian day-ahead market
(ENTSO-E) for a 50 GWh Styrian industrial consumer.

> **How much did buying electricity the wrong way cost a 50 GWh/year Styrian
> manufacturer in 2021–2025 — and what is the P95 cost exposure for the next
> 12 months under each procurement strategy?**

**The answer lands here at M6/M7.** Per project rule (RP-601 / GV-303), every
number in this README is copied from the auto-generated
[`reports/NUMERIC_SSOT.md`](reports/NUMERIC_SSOT.md) with its epistemic tag —
no results exist yet, so none are quoted yet.

<!-- M7: RP-201 chart embed goes here -->

## What is real vs. modeled

| Tag | Meaning | Applies to |
|-----|---------|-----------|
| VERIFIED | Computed from real external data, no modeling assumptions beyond unit conversion/aggregation | Spot prices, negative-hour counts, AT–DE spread |
| CALIBRATED | Derived via documented assumptions anchored to real data | Consumer load profile, ÖSPI→EUR/MWh translation, strategy costs |
| SIMULATED | Output of a seeded stochastic procedure | Bootstrap cost distributions (P95, CVaR95) |

Reference load profile is constructed (CALIBRATED), not measured; construction
rules in [SPEC-03](docs/SPEC-03_consumer_load_profile.md).

<!-- M6/M7: results tables (annual matrix + forward risk) from SSOT -->
<!-- M7: dashboard screenshots -->

## Project status

Foundation stage. Charter + eight SPECs are final; M0 (bootstrap) is complete;
M1–M7 are pending. Build order, gates, and per-milestone status:
[`PROJECT_CHARTER.md`](PROJECT_CHARTER.md) §7, [`AGENTS.md`](AGENTS.md),
[`docs/BUILD_LOG.md`](docs/BUILD_LOG.md).

## How to reproduce (once M1+ lands)

```bash
git clone <repo> && cd energy-procurement-risk-analyzer
cp .env.example .env       # add your ENTSO-E API token (SPEC-01 §2)
make setup
make backfill              # 2019 → latest complete month, all sources
make all                   # transform → profile → analyze → simulate → ssot → export → report
```

## Architecture

```
ENTSO-E / GeoSphere / ÖSPI(manual) / holidays
        │  ingestion (SPEC-01: retry, cache, validation gates)
        ▼
 data/raw parquet ──► DuckDB + dbt (SPEC-02: staging → marts)
        │
        ├─► analytics A1–A4 (SPEC-04) ──► reports/analytics/
        ├─► consumer profile (SPEC-03) ─┐
        └─► strategy simulator (SPEC-05)┴─► NUMERIC_SSOT.md / exports/*.csv
                                             │
                                             └─► Power BI + EXEC_SUMMARY (SPEC-06)
```

## Data sources

- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu) — AT/DE-LU
  day-ahead prices, AT load & generation (VERIFIED)
- [Austrian Energy Agency — ÖSPI](https://www.energyagency.at/fakten/strompreisindex)
  — monthly wholesale price index, hand-transcribed with double-entry validation (VERIFIED)
- [GeoSphere Austria Data Hub](https://data.hub.geosphere.at) — daily mean
  temperature, Graz (VERIFIED)
- `holidays` Python package — Austrian/Styrian holidays (VERIFIED)

Honesty artifacts: [`LIMITATIONS.md`](LIMITATIONS.md). Governance is
deliberately light (three mechanisms, [SPEC-08](docs/SPEC-08_governance_quality.md));
no audit-finding registry, no session handouts, no re-verification matrix, no
numbered finding IDs — if a reviewer wants to see that machinery, see the
decision-analytics-reconstruction repo instead.

## License & author

MIT — Rafael Braga-Kribitz, Seiersberg-Pirka, Austria.
