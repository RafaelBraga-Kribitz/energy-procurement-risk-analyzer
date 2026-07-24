---
phase: 4
slug: m3-dbt-warehouse
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-24
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `04-RESEARCH.md` § Validation Architecture. Per-task rows are keyed by
> DM-id / artifact here (task IDs not yet assigned at plan-phase time); validate-phase §6
> re-keys them to concrete `04-NN-MM` task IDs after planning.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (warehouse)** | dbt's own `build`/`test` framework (generic + singular tests) — not pytest |
| **Framework (Python glue)** | pytest (existing project framework; `tests/unit/`) |
| **Config file** | `dbt/dbt_project.yml` (already committed); no new pytest config needed |
| **Quick run command (dbt)** | `cd dbt && dbt build --select staging` |
| **Quick run command (pytest)** | `uv run pytest tests/unit/test_marts_contract.py -x` |
| **Full suite command (dbt)** | `cd dbt && dbt build` (full DAG: seeds → staging → marts → all tests) |
| **Full suite command (pytest)** | `uv run pytest -m "not live"` (existing project-wide command, unchanged) |
| **Estimated runtime** | dbt build (fixture): < 5 min (CI gate target, T3.06); pytest contract: ~seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd dbt && dbt build --select <changed_layer>` (e.g. `--select staging` while iterating staging models)
- **After every plan wave:** Run `cd dbt && dbt build` (full DAG) + `uv run pytest tests/unit/test_marts_contract.py tests/unit/test_bootstrap_fixture_warehouse.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Phase gate:** BOTH the local real-data `dbt build` (D-01, SC#1) AND the CI fixture `dbt build` (SC#3) green, plus schema-contract pytest green (SC#2)
- **Max feedback latency:** ~300 seconds (fixture `dbt build`)

---

## Per-Task Verification Map

*Keyed by requirement/DM-id until plan-phase assigns task IDs. `File Exists` ❌ W0 = artifact created in this phase's Wave 0.*

| DM / Item | Requirement | Secure Behavior | Test Type | Automated Command | File Exists |
|-----------|-------------|-----------------|-----------|-------------------|-------------|
| DM-004 | REQ-DWH-01 | Raw parquet read once per source; no other model touches files | dbt build (source smoke) | `cd dbt && dbt build --select source:raw+` | ❌ W0 (`sources.yml`) |
| DM-003 / SG-13 | REQ-DWH-01 | Schemas literally `staging`/`marts` | dbt build + info_schema query | `cd dbt && dbt build && duckdb data/warehouse/epra.duckdb -c "select schema_name from information_schema.schemata"` | ❌ W0 (`macros/generate_schema_name.sql`) |
| DM-005 / §3 | REQ-DWH-01 | 8 staging models, exact columns | dbt generic (unique/not_null) | `cd dbt && dbt build --select staging` | ❌ W0 (`models/staging/*.sql`) |
| DM-011 / §4 | REQ-DWH-01 | `dim_calendar` no independent TZ calls; season/hdd/cdd correct | dbt build + singular spot-check | `cd dbt && dbt build --select dim_calendar` | ❌ W0 (`models/marts/dim_calendar.sql`) |
| DM-050 / §5 | REQ-DWH-01 | Marts no-gap; `price_peak_eur_mwh` NULL on no-peak days | dbt singular test | `cd dbt && dbt build --select marts` | ❌ W0 (`tests/no_gap_*.sql`) |
| DM-060 | REQ-DWH-01 | unique/not_null on grain keys | dbt generic test | `cd dbt && dbt build` | ❌ W0 (`models/*/*.yml`) |
| DM-061 | REQ-DWH-01 | Accepted ranges | dbt generic test (hand-rolled) | `cd dbt && dbt build` | ❌ W0 (`macros/test_accepted_range.sql`) |
| DM-062 | REQ-DWH-01 | Row counts 8760/8784 ±24 per year | dbt singular test | `cd dbt && dbt build` | ❌ W0 (`tests/fct_price_hourly_row_count_per_year.sql`) |
| DM-063 | REQ-DWH-01 | strategy_id FK → dim_strategy | dbt generic `relationships` | `cd dbt && dbt build` | ❌ W0 (`models/marts/marts.yml`) |
| DM-064 | REQ-DWH-01 | 2022-08 monthly base == mean of hourly | dbt singular test | `cd dbt && dbt build` | ❌ W0 (`tests/reconcile_price_monthly_2022_08.sql`) |
| DM-065 | REQ-DWH-01 | DST hour counts (2024-03-31=23h, 2024-10-27=25h) | dbt singular test | `cd dbt && dbt build` | ❌ W0 (`tests/dst_hour_counts_fct_price_hourly.sql`) |
| DM-066 | REQ-DWH-01 | Freshness, refresh-only (wired, not exercised in normal build) | dbt singular test (var-gated) | `cd dbt && dbt build --vars '{check_freshness: true}'` | ❌ W0 (`tests/freshness_stg_prices_at_hourly.sql`) |
| D-07 contract | REQ-DWH-01 | Mart schemas byte-match SPEC-02 §5 | pytest (`information_schema` diff, `yaml.safe_load`) | `uv run pytest tests/unit/test_marts_contract.py` | ❌ W0 (`tests/unit/test_marts_contract.py`, `dbt/contracts/marts_contract.yml`) |
| D-04 CI bootstrap | REQ-DWH-01 | Deterministic 2022–2024 window synthesized; guard against overwriting real `data/raw/` | pytest | `uv run pytest tests/unit/test_bootstrap_fixture_warehouse.py` | ❌ W0 (`scripts/bootstrap_fixture_warehouse.py`) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky — all ⬜ pending at plan time.*

---

## Wave 0 Requirements

- [ ] `dbt/models/sources.yml` — DM-004 external `read_parquet` sources
- [ ] `dbt/macros/generate_schema_name.sql` — SG-13 / ADR-009
- [ ] `dbt/macros/month_spine.sql`, `dbt/macros/test_accepted_range.sql` — DM-050 / DM-061 helpers (no `dbt_utils` dep)
- [ ] `dbt/models/staging/*.sql` (8) + `staging.yml` — §3
- [ ] `dbt/models/marts/dim_calendar.sql`, `dbt/models/marts/fct_*.sql` (6) + `marts.yml` — §4/§5
- [ ] `dbt/tests/*.sql` (singular: DM-050/062/064/065/066)
- [ ] `dbt/contracts/marts_contract.yml` — D-07
- [ ] `tests/unit/test_marts_contract.py` — D-07 pytest diff
- [ ] `scripts/bootstrap_fixture_warehouse.py` + `tests/unit/test_bootstrap_fixture_warehouse.py` — D-04
- [ ] Build-report writer (D-02) → `reports/warehouse/dbt_build_<date>.md`
- [ ] `Makefile` `transform:` target body (un-stub to `cd dbt && dbt build`)
- [ ] `.github/workflows/ci.yml` `dbt-check` job (add, wire as required — TP.02)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Local real-data `dbt build` green (SC#1, D-01) | REQ-DWH-01 | Real `data/raw/` (2019→2024) present only on the operator's machine; not run in network-free CI | `cd dbt && dbt build` against real warehouse; capture build report at `reports/warehouse/dbt_build_<date>.md` (D-02) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
