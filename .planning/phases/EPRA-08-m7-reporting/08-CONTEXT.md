# Phase 8: M7 Reporting & Refresh - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning
**Mode:** Interactive discuss — spec-supremacy. `docs/SPEC-06_reporting_dashboard.md` (RP-xxx) and Charter §6 DL-1..DL-10 lock *what* to ship. WBS T7.01–T7.07 locks order. This discussion captures HOW to do that **without inventing SSOT euros** (A-2, A-6) in a checkout that has no `data/raw/` and no committed `NUMERIC_SSOT.md` (M6 D-04).

<domain>
## Phase Boundary

Ship reporting, exports, refresh, and honesty artifacts (REQ-RPT-01, REQ-Q4, REQ-GOV-01). One milestone. The `.pbix` and dashboard screenshots are **human** (AGENTS §2.5). EXEC_SUMMARY §5 recommendation is **human co-write**.

- **Code:** `scripts/export_marts.py`, `epra.report.charts.render_executive_charts`, `make export` / `make report`, `.github/workflows/refresh.yml`, `dashboards/README.md` handoff.
- **Docs:** EXEC_SUMMARY structure, README §6 order, LIMITATIONS §1–7, BUILD_LOG M7.
- **Not this phase:** fifth strategy, forecasting, inventing Q1/Q3 euros, marking GitHub checks required, regenerating ST-601 with real euros without human approval.

**Exit gate (SC):** (1) fresh clone `make setup && make all` — **operator with token + warehouse**; code must fail closed without them. (2) README leads with euro answer **only when SSOT exists**; until then keep GV-303 green (no unmatched tokens). (3) EXEC_SUMMARY / LIMITATIONS / exports / refresh / dashboard handoff live; coverage ≥ 80%. `.pbix` remains human.

</domain>

<decisions>
## Implementation Decisions

### Exports (T7.01 — DM-070)
- **D-01:** Exactly the six SPEC-02 §7 filenames. Marts via DuckDB read-only. `strategy_annual_summary.csv` and `forward_risk_summary.csv` come from processed strategy artifacts / `reports/strategies/` tables already written by M6 — **never typed by hand**. Missing warehouse → exit 1 with `make warehouse` hint. Missing strategy outputs → exit 1 with `make simulate` hint. Do not invent rows.
- **D-02:** UTF-8, ISO dates, `.` decimal. Idempotent overwrite. DM-070 tests on injected frames / tmp_settings (same pattern as M5/M6). Do not commit `exports/*.csv` from the CI fixture as Q1 evidence.

### Executive charts (T7.02 — RP-201..204, RP-301)
- **D-03:** Charts read **only** exports CSVs (RP-301). RP-201 bars = `wrong_strategy_cost_<year>` equivalent recomputed from `strategy_annual_summary.csv` (max−min per year); pytest asserts artist values match that recompute. LP-050 + ST-502 + RP-702 tags. STRATEGY_COLORS. Tag CALIBRATED on RP-201/202; SIMULATED on RP-203; VERIFIED on RP-204 market line.
- **D-04:** Do **not** commit fixture executive PNGs. Tests write under tmp_settings. Operator `make export && make report` on real data produces DL artifacts.

### EXEC_SUMMARY and README (T7.03–T7.04 — A-6, SG-12)
- **D-05:** Every euro in EXEC_SUMMARY/README is copy-pasted from `reports/NUMERIC_SSOT.md`. If that file is absent, EXEC_SUMMARY still has SPEC-06 §5 headings but **no invented numerals**; §5 recommendation is a labeled `<!-- HUMAN: co-write after SSOT -->` stub that GV-303 will not tokenize as EUR. Do not write "€X million" placeholders.
- **D-06:** README keeps the M0 skeleton until SSOT is committed; optional structure tweaks must not add result euros. Dashboard screenshot embeds wait for human `docs/assets/dashboard_p*.png`.

### LIMITATIONS (T7.04 — SPEC-08 §6)
- **D-07:** Finalize methodology sentences (constructed load, ÖSPI proxy, premium assumption, bootstrap limits, grid fees, 2025 caveats, no forecast). Sensitivity **numbers** (0/5/10 EUR/MWh, flat_baseload) are quoted from SSOT/sensitivity_matrix only when those files exist from a real simulate; otherwise state that the numbers appear after operator `make simulate` and point at the matrix path — do not paste toy golden 120/100 EUR.

### refresh.yml (T7.05 — EN-081..083)
- **D-08:** Cron `0 5 6 * *` plus `workflow_dispatch`. Steps: checkout, uv, `make refresh` with `ENTSOE_API_TOKEN` secret, upload `exports/` + `reports/` artifacts, ÖSPI coverage warning in PR body if latest complete month missing from `oespi_monthly.csv`, create-pull-request with path filter on committed report files, **skip PR when diff empty** (SG-18). Never auto-push to main. Workflow dry-run on GitHub is operator (needs secret).

### Power BI (T7.06 — human)
- **D-09:** Agent writes `dashboards/README.md` (relative CSV paths, relationships, four pages RP-401..405, German subtitle instruction). Does **not** fabricate screenshots or a dummy `.pbix`. Human builds `dashboards/epra.pbix` and `docs/assets/dashboard_p1.png`…`p4.png`.

### Close-out (T7.07)
- **D-10:** Un-stub `make export` / `make report`. Tick DL-1..DL-10 in the PR **honestly**: DL-1/DL-2/DL-4/DL-5/DL-6/DL-10 stay operator or human where this checkout cannot produce real euros or a `.pbix`. DL-7 coverage already ≥80%. DL-8 is the workflow file. DL-9 LIMITATIONS sections present. Do not claim GitHub required-checks.

### Claude's Discretion
- Export column lists follow marts_contract.yml / annual_summary columns.
- RP-204 regime bands: reuse M5 HMM labels if a persisted daily frame exists; otherwise load marts and `fit_hmm` like forward_risk (expensive) — prefer reading A3 markdown/CSV if already exported; if not, load `fct_price_daily` and fit with the same seeds (determinism).
- EXEC_SUMMARY length: aim ≤2 pages; if SSOT empty, the honesty stub is short on purpose.

</decisions>
