# Phase 4: M3 dbt Warehouse - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-23
**Phase:** 4-M3 dbt Warehouse
**Areas discussed:** Real-data close boundary, CI fixture bootstrap, Future-mart stand-ins, Contract & ADR governance

---

## Real-data close boundary

**Q1 — How does M3 close, and which gate is blocking?**

| Option | Description | Selected |
|--------|-------------|----------|
| Split by environment | CI blocking gate = `dbt build` on fixture warehouse (network-free); real-data `dbt build` in-phase locally, evidence committed as checkpoint; close = both green | ✓ |
| Real-data is the hard gate | Real `dbt build` primary blocking gate; can't actually block in CI (duckdb gitignored, no real data in CI) → local-only attestation | |
| CI-fixtures only to close | Close on CI-fixture green alone; real deferred — contradicts SC#1 | |

**User's choice:** Split by environment (Recommended).

**Q2 — What evidence does the real-data checkpoint commit?**

| Option | Description | Selected |
|--------|-------------|----------|
| Human-readable build report | `reports/warehouse/dbt_build_<date>.md` — models built, test pass/fail, key row counts + 2022-08 recon delta; consistent with reports/ingestion/ precedent | ✓ |
| dbt native artifacts | Commit `target/run_results.json` + `manifest.json`; large/noisy, not reviewer-friendly | |
| Both report + run_results.json | .md summary plus run_results.json; most thorough, heavier diff | |

**User's choice:** Human-readable build report (Recommended).
**Notes:** duckdb file stays gitignored (DM-001); `make warehouse`/`make dbt-check` naming left to implementer (Makefile-as-canonical-interface already locked).

---

## CI fixture bootstrap

**Q1 — How is the fixture warehouse shaped so DM-060..066 pass network-free?**

| Option | Description | Selected |
|--------|-------------|----------|
| Contiguous span covering hardcoded dates | Fixture spans ≥ 2022-01→2024-12: includes 2022-08 (DM-064), 2024 DST days (DM-065), ≥1 full year (DM-062), no gaps (DM-050); tests run UNMODIFIED, no ADR | ✓ |
| One synthetic year + parametrized tests | Smaller fixture; DM-064/065 dates become data-driven; deviates from spec-literal dates → ADR | |
| Minimal slices + scoped full-window tests | Only test periods present; DM-062/DM-050 skipped in CI → weakens gate | |

**User's choice:** Contiguous span covering the hardcoded dates (Recommended).

**Q2 — Where do the ~3 years of hourly rows come from?**

| Option | Description | Selected |
|--------|-------------|----------|
| Programmatic synthesis at CI time | bootstrap script generates deterministic synthetic hourly data at runtime; repo stays lean; deviates from WBS "from tests/fixtures/ parquet" → SG-06 note | ✓ |
| Committed multi-year fixture parquet, copied | Commit 2022–2024 parquet; matches WBS wording but adds MBs, breaks lean-excerpt convention | |
| Hybrid: committed edge cases + synthesized filler | Real excerpts for 2022-08/2024 DST + synthesized rest; two code paths | |

**User's choice:** Programmatic synthesis at CI time (Recommended).

---

## Future-mart stand-ins

**Q1 — What do the fct_consumer_load_hourly / fct_procurement_cost_monthly stand-ins contain, and how do DM-050/DM-063 behave until M4/M6?**

| Option | Description | Selected |
|--------|-------------|----------|
| Full-window valid stand-ins, environment-aligned | Synthesize valid rows spanning the same window as surrounding data (real 2019→latest local, synthetic 2022–2024 CI); every month × 6 strategy_ids; DM-050/063/060 pass unmodified; feeds both environments | ✓ |
| Empty schema-only stand-ins + scoped tests | 0 rows; DM-050/DM-063 scoped to exclude the two future marts (ADR/exemption); leaner but two tests carry a hole | |
| Minimal 1-row-per-key stand-ins | One row per month×strategy; satisfies DM-063 but not DM-050 no-gap → still needs scoping | |

**User's choice:** Full-window valid stand-ins, environment-aligned (Recommended).
**Notes:** `data/processed` is empty locally too, so the same stand-in mechanism feeds the local real-data build (Q1 of Area A), not just CI, until M4/M6 replace them.

---

## Contract & ADR governance

**Q1 — How is dbt/contracts/marts_contract.yml authored, and what does it cover?**

| Option | Description | Selected |
|--------|-------------|----------|
| Hand-author from SPEC-02 §5 + SG-05, all 6 marts | Write YAML by hand from spec's frozen lists; T3.05 test diff-checks information_schema vs it; matches spec's named mechanism | ✓ |
| Generate from information_schema, then freeze | Dump then commit; circular — a model bug gets frozen as correct; weaker | |
| dbt native model contracts instead | `contract: {enforced: true}` + data_types; idiomatic but deviates from spec-named file+test → ADR | |

**User's choice:** Hand-author from SPEC-02 §5 + SG-05, all 6 marts (Recommended).

**Q2 — How many ADRs for M3's spec-gap adoptions?**

| Option | Description | Selected |
|--------|-------------|----------|
| Granular: 3 single-topic ADRs | ADR-009 SG-13 schema macro; ADR-010 SG-06 fixture+stand-in; ADR-011 SG-14 peak+ÖSPI+LIMITATIONS; matches ADR-001..008 precedent + WBS triggers | ✓ |
| Consolidated: one M3 warehouse ADR | Single ADR bundling all three; breaks single-topic precedent | |
| Minimal: only SG-06 gets an ADR | Only fixture/stand-in ADR'd; skips WBS-mandated T3.01/T3.04 triggers | |

**User's choice:** Granular: 3 single-topic ADRs (Recommended).
**Notes:** SG-05 gets no ADR — the committed contract YAML is its adoption. Confirm ADR-009/010/011 are free against docs/ADR/ at planning time.

---

## Claude's Discretion

- `make warehouse` / `make dbt-check` target naming and Makefile wiring (Makefile-as-canonical-interface already locked in PROJECT.md).
- Month-spine test mechanism (DM-050): custom SQL macro vs `dbt_utils` dependency — minimal footprint preferred.
- Model/macro decomposition, staging CTE structure, synthetic-generator internals, seed/relationship-test scaffolding layout.
- Synthetic generator determinism knobs (seed value, curve shape) provided all DM-060..066 pass.

## Deferred Ideas

- BI exports (`scripts/export_marts.py`, `make export`, SPEC-02 §7 CSVs + DM-070 contract tests) → M7/Phase 8.
- Real consumer-load parquet replaces the consumer stand-in → M4/Phase 5 (SPEC-03).
- Real procurement-cost parquet replaces the procurement stand-in → M6/Phase 7 (SPEC-05).
- DM-066 freshness gate is refresh-only → wired now, exercised at M7 monthly refresh.
