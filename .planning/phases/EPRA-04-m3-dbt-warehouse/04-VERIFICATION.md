---
phase: EPRA-04-m3-dbt-warehouse
verified: 2026-09-01T17:10:00Z
status: passed
score: 3/3 ROADMAP criteria met — CI fixture dbt build PASS=64 (SC#3); D-07 schema contract 6 passed (SC#2); SC#1 evidenced by committed reports/warehouse/dbt_build_2026-07-24.md
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "On GitHub branch protection for main, mark the dbt-check job a required status check alongside lint and test (TP.02)"
    expected: "A PR cannot merge to main while dbt-check is failing or pending; the job is already defined in .github/workflows/ci.yml"
    why_human: "TP.02 is a GitHub repository settings action, explicitly out of code scope in 04-08-PLAN.md. The job exists and ran green on PR #2 (lint/test/dbt-check). Do not auto-approve the required-check flip."
---

# Phase 4: M3 dbt Warehouse Verification Report

**Phase Goal:** Analysts and simulators read contract-tested marts from DuckDB — no raw parquet in analytics code
**Verified:** 2026-09-01T17:10:00Z
**Status:** passed
**Re-verification:** No — initial verification (GSD close-out after 04-08 SUMMARY)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator runs `dbt build` on real data and all models + tests pass | ✓ VERIFIED (artifact) | Committed `reports/warehouse/dbt_build_2026-07-24.md`: **PASS=63 WARN=1** (`predup_count_prices`, informational) **ERROR=0**; 2022-08 delta `0.0000` (`482.7263` both sides); stand-in flags present. This cloud checkout has no `data/raw/` backfill — SC#1 is not re-run here (A-2). |
| 2 | Mart schemas byte-match the committed SPEC-02 §5 contract YAML | ✓ VERIFIED | `uv run pytest tests/unit/test_marts_contract.py -m "not live" --no-cov` → **6 passed** (2026-09-01, against the isolated fixture warehouse). |
| 3 | CI fixture bootstrap enables `dbt build` green without a full local backfill | ✓ VERIFIED | Isolated `--data-root /tmp/iso-epra/data`: `bootstrap_fixture_warehouse.py --force` then `dbt build` → **PASS=64 WARN=0 ERROR=0 SKIP=0 TOTAL=64** (1.30s), network-free. PR #2 `dbt-check` job also green. Committed `data/manual/oespi_monthly.csv` untouched. |

**Score:** 3/3 ROADMAP criteria verified.

### Plan-Level Must-Haves (spot-checked this session)

| Plan | Truth (condensed) | Status | Evidence |
|------|-------------------|--------|----------|
| 04-01 | Literal `staging`/`marts` schemas (ADR-009); sources via `../data/` globs; no `packages.yml` | ✓ VERIFIED | Isolated warehouse `information_schema.schemata` contains `staging` and `marts` (not `main_staging`). `sources.yml` 9 globs all `../data/...`. No `dbt/packages.yml`. `generate_schema_name.sql` trims custom schema only. |
| 04-02 | 8 staging views; no model TZ calls | ✓ VERIFIED | Isolated warehouse: 8 `staging.*` views. `rg "AT TIME ZONE" dbt/models` empty. Fixture `dbt build` includes all staging tests PASS. |
| 04-03 | `dim_calendar` + `dim_strategy`; DST 23/25; 6 strategy seed rows | ✓ VERIFIED | `dim_strategy` = S1,S2,S3,S4_30,S4_50,S4_70. `fct_price_hourly` 2024-03-31=23 rows, 2024-10-27=25 rows (DM-012/DM-065). |
| 04-04 | Price/generation marts; DM-064 reconciliation; no exports | ✓ VERIFIED | 2022-08 monthly vs hourly mean **delta=0.0**. `make export` still the M7 loud-fail stub. |
| 04-05 | Synthesizer + never-disabled future marts | ✓ VERIFIED | `tests/unit/test_bootstrap_fixture_warehouse.py` in the 22-test pytest bundle this session. Isolated build created `fct_consumer_load_hourly` + `fct_procurement_cost_monthly`. ADR-010 present. |
| 04-06 | DM-050/062/064/065/066 + D-07 contract | ✓ VERIFIED | Fixture `dbt build` ran `fct_price_hourly_row_count_per_year`, `reconcile_price_monthly_2022_08`, `dst_hour_counts_fct_price_hourly`, `no_gap_monthly_marts` — all PASS. Contract pytest 6 passed. `yaml.safe_load` in `test_marts_contract.py`. |
| 04-07 | D-02 report writer + `make transform`/`warehouse` | ✓ VERIFIED | `tests/unit/test_warehouse_report.py` in the 22-test bundle. Makefile `transform:` = `cd dbt && $(UV) run dbt build`; `warehouse:` composes transform + `python -m epra.warehouse.report`. Report committed. |
| 04-08 | `dbt-check` job; both builds; git clean of `data/` | ✓ VERIFIED | `ci.yml` jobs = lint, test, dbt-check. Isolated PASS=64. `git status --porcelain data/` empty. |

**Score:** 8/8 plans' must-have clusters verified (TP.02 required-check flip remains human — not a code must-have).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `dbt/models/sources.yml` | 9 external globs, `../data/` prefix | ✓ VERIFIED | ENTSO-E ×4, GeoSphere, calendar, ÖSPI, 2 processed stand-ins |
| `dbt/macros/generate_schema_name.sql` | ADR-009 | ✓ VERIFIED | Omits default_schema prefix |
| `dbt/macros/month_spine.sql` | DM-050 helper | ✓ VERIFIED | Present; used by `no_gap_monthly_marts.sql` |
| `dbt/macros/test_accepted_range.sql` | DM-061 | ✓ VERIFIED | Present |
| 8 `dbt/models/staging/stg_*.sql` | SPEC-02 §3 | ✓ VERIFIED | All 8 present + `staging.yml` |
| `dbt/models/marts/dim_calendar.sql` | SPEC-02 §4 | ✓ VERIFIED | Present + `dims.yml` |
| 6 `fct_*.sql` marts | SPEC-02 §5 | ✓ VERIFIED | price hourly/daily/monthly, generation monthly, 2 stand-ins |
| `dbt/contracts/marts_contract.yml` | D-07 | ✓ VERIFIED | Hand-authored; pytest-enforced |
| `dbt/tests/*.sql` | DM-050/062/064/065/066 | ✓ VERIFIED | 5 singular tests present (`freshness` var-gated) |
| `scripts/bootstrap_fixture_warehouse.py` | D-04 | ✓ VERIFIED | `--force` / `--processed-only` / `--data-root`; ADR-010 |
| `src/epra/warehouse/report.py` | D-02 | ✓ VERIFIED | Read-only DuckDB; writes `reports/warehouse/dbt_build_<date>.md` |
| `Makefile` `transform`/`warehouse` | operator interface | ✓ VERIFIED | Un-stubbed |
| `.github/workflows/ci.yml` `dbt-check` | EN-080 job 3 | ✓ VERIFIED | Separate job; PR #2 CI green |
| `reports/warehouse/dbt_build_2026-07-24.md` | D-02 | ✓ VERIFIED | Committed |
| `docs/BUILD_LOG.md` M3 entry | W-5 | ✓ VERIFIED | 2026-07-24 section |
| `docs/ADR/ADR-009..011` | D-08 | ✓ VERIFIED | All three files present |
| `04-08-SUMMARY.md` | GSD close-out | ✓ VERIFIED | Written 2026-09-01 |

**Artifacts:** 17/17 verified

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `dbt-check` CI job | `bootstrap_fixture_warehouse.py --force` then `dbt build` | `ci.yml` | ✓ WIRED |
| Staging models | `source('raw'/'raw_*')` only | `sources.yml` | ✓ WIRED |
| Marts | `dim_calendar` on `ts_utc` | SQL joins | ✓ WIRED (no `AT TIME ZONE` in models) |
| `fct_procurement_cost_monthly` | `dim_strategy` | `relationships` test PASS in fixture build | ✓ WIRED |
| `make warehouse` | `dbt build` + `epra.warehouse.report` | Makefile | ✓ WIRED |
| D-07 pytest | `marts_contract.yml` + `information_schema` | `yaml.safe_load` + `db.connect(read_only=True)` | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Isolated fixture `dbt build` | bootstrap `--force --data-root /tmp/iso-epra/data` then `dbt build` | PASS=64 WARN=0 ERROR=0 TOTAL=64 | ✓ PASS |
| Schema contract | `pytest tests/unit/test_marts_contract.py -m "not live" --no-cov` | 6 passed | ✓ PASS |
| Warehouse report + bootstrap unit tests | `pytest tests/unit/test_warehouse_report.py tests/unit/test_bootstrap_fixture_warehouse.py --no-cov` | included in **22 passed** this session | ✓ PASS |
| Literal schemas | DuckDB `information_schema.schemata` | `staging`, `marts` present | ✓ PASS |
| DST hour counts | `fct_price_hourly` 2024-03-31 / 2024-10-27 | 23 / 25 | ✓ PASS |
| DM-064 2022-08 delta | monthly base vs mean of hourly | `0.0` | ✓ PASS |
| `git status` clean of `data/` | `git status --porcelain data/` | empty | ✓ PASS |
| PR #2 CI | lint + test + dbt-check | all green on `6dcf144` | ✓ PASS |
| Real-data `make warehouse` | N/A in this checkout | committed 2026-07-24 report | ✓ PASS (artifact) |
| TP.02 required-check flip | GitHub settings | out of code scope | → human |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| REQ-DWH-01 | ✓ SATISFIED | SC#1/#2/#3 all verified; REQUIREMENTS.md already marked Complete |
| D-01 (split-by-environment) | ✓ SATISFIED | CI fixture vs local real-data report |
| D-02 (build report, gitignore duckdb) | ✓ SATISFIED | markdown committed; `data/warehouse/` gitignored |
| EN-080 job 3 | ✓ SATISFIED | `dbt-check` in `ci.yml`; CI green |

**Coverage:** 4/4 in-scope IDs satisfied. TP.02 remains operator GitHub settings.

## Human Verification Required

1. **TP.02** — mark `dbt-check` required on `main` branch protection. Code and CI job are done; this is settings-only.

## Gaps Summary

**No code gaps.** Phase goal achieved. Ready to proceed to Phase 5 (M4 consumer profile). `fct_consumer_load_hourly` remains a stand-in until M4 produces `data/processed/consumer_load_hourly.parquet`.

Deferred (not blocking): TP.02 required-check flip; 04-04 `staging.yml` nested-`arguments:` deprecation (logged in `deferred-items.md`).

---

## Verification Metadata

**Verification approach:** Goal-backward against ROADMAP Phase 4 success criteria + independent re-run of SC#2/#3 + artifact/schema spot-checks on the isolated fixture warehouse
**Must-haves source:** 04-01..04-08 PLAN.md `must_haves.truths`
**Automated checks:** isolated `dbt build` PASS=64; contract pytest 6; warehouse+bootstrap+contract pytest 22; PR #2 CI 3/3 green
**Human checks required:** 1 (TP.02 GitHub settings)
**Basis:** commits through `6dcf144` (04-08 close-out + calendar mypy fix); verified 2026-09-01

---
*Verified: 2026-09-01*
