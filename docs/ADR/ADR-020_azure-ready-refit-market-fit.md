# ADR-020: Azure-ready refit for market fit
Date: 2026-10-14  |  Status: accepted

Amends: Charter O-4 and DL-6 (where they conflict), SPEC-06 §4 (pages),
SPEC-07 (repo layout, Makefile, CI/CD). Related: ADR-016, ADR-018, ADR-019.

## Context

The owner's portfolio decision (17 Sep 2026) is to position this project for
the Austrian data/analytics job market: Azure-style scheduled ingestion,
SQL-first transformations, tests/CI, visible data-quality checks and a Power BI
report, framed for a Styrian industrial/energy employer. His own job-ad study
(16 Sep 2026, 719 Austrian ads with description) found Azure in 19% of ads
(AWS 9%, GCP 6%), Power BI in 18% (Tableau 3%), SQL in ~59%, and data quality /
ETL among the top junior-analyst terms. The core question, the four
strategies and the epistemic rules are NOT changed by this ADR.

## Decision

1. **SQL-first.** DuckDB + dbt stays the engine. All marts and simulator inputs
   are explicit-column SQL (CTEs, named JOINs). A top-level `sql/` folder holds
   the headline queries (Q1 cost matrix, Q1 wrong-strategy cost, Q3 P95/CVaR95,
   data-quality coverage); a test asserts each reproduces the Python result.
2. **Azure-ready publish path, local by default.** `epra.cloud` defines a
   `PublishTarget` interface: `local` (default; writes `exports/MANIFEST.json`)
   and `azure` (Blob Storage upload of raw parquet + exports, Azure SQL load of
   every export table). Switched by `config/settings.yaml cloud.target` or
   `make publish TARGET=azure`; secrets only via env / GitHub Actions secrets.
   Optional dependency extra `azure` (azure-storage-blob, azure-identity,
   pyodbc) — never installed by `make setup` or CI. IaC: `infra/azure/main.bicep`
   (Standard_LRS storage + Azure SQL serverless on the free offer with
   `useFreeLimit` + `AutoPause`). Guide and cost note: `docs/AZURE_DEPLOYMENT.md`.
   The README says "Azure-ready, deployment path documented" until a real
   deployment run exists; it never says "deployed on Azure" before that.
3. **Visible data-quality layer.** New mart `fct_data_quality_monthly`
   (coverage, DST days, PT15M/PT60M mix, negative hours, ÖSPI presence) and
   `reports/data_quality/DATA_QUALITY.md` from `make report`.
4. **Power BI build kit.** Exports gain `spread_monthly` (RP-402 needs it),
   `dim_strategy` (labels, colours), `data_quality_monthly`, `forward_paths`,
   `ssot` and `provenance`. SPEC-06 §4 gains page 5 "Data quality"; screenshots
   become `dashboard_p1…p5.png`. Charter O-4 is unchanged: no hosted app.
5. **Industrial framing.** README and EXEC_SUMMARY address a CFO / procurement
   lead in EUR first, with a short German summary; no fluency claim. The README
   leads with the answer and the headline chart, then ONE line naming the
   skills the project demonstrates (SQL, Python, dbt, DuckDB, Power BI, ETL,
   data quality, Azure-ready) before the run instructions — this amends
   SPEC-06 §6 RP-601's "stack names appear first in §8". A skill is named only
   if this repository demonstrates it.
6. **Monthly refresh (DL-8)** is a scheduled GitHub Action that rebuilds
   everything and opens a PR with the regenerated results, publishing to Azure
   only when the Azure secrets exist.

## Consequences

- One more mart (contract updated, 9 objects), six more export files, one
  optional extra in `pyproject.toml`/`uv.lock` (default install unchanged).
- Cloud code is tested with injected fakes; a real Azure run needs the owner's
  subscription (human action) and is not claimed until it has happened.

## Spec deviations (list REQ IDs affected, or "none")

SPEC-06 RP-401..406 (page 5 added, screenshot list), SPEC-06 §6 / RP-601
(skills line on the first screen), SPEC-02 §5 (new mart),
SPEC-02 §7 (export list extended), SPEC-07 §2/§5 (cloud/, infra/, sql/,
`make publish`, `refresh.yml`). Output contracts of existing artifacts unchanged.
