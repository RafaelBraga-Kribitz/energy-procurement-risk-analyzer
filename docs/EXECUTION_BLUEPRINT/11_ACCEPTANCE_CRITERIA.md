# 11 — ACCEPTANCE CRITERIA (objective, runnable)

Task-level AC live on each WBS card ([02_WBS.md](02_WBS.md)). This document
covers (a) the rules for writing AC, (b) milestone-level acceptance, (c) the
expanded DL-1..10 release verification script for M7.

## 11.1 Rules for acceptance criteria (all tasks)

1. Every criterion is **checkable by command, test, or file existence** — never
   "clean", "reasonable", "good" without a number or a predicate.
2. Numeric criteria carry units and tolerances (e.g. "± 0.01 MWh", "≤ 24 hours/year").
3. A criterion that cannot fail is not a criterion — delete it.
4. If verifying a criterion requires the token/human, the task carries the label.

## 11.2 Milestone acceptance (beyond the gate matrix in [10_VALIDATION_GATES.md](10_VALIDATION_GATES.md))

| Milestone | Acceptance = gate matrix PLUS |
|-----------|-------------------------------|
| M1 | `make backfill && make validate-ingest` exits 0 end-to-end on a machine with only `.env` + clean `data/`; re-run of one month produces identical data columns (ING-003) |
| M2 | `python scripts/oespi_reconcile.py` exit 0 is in the PR evidence; calendar parquet row count equals Σ hours(2019-01-01 → forward end) |
| M3 | `cd dbt && dbt build` exit 0 twice in a row (idempotent); `information_schema` diff vs contract YAML empty |
| M4 | `make profile` ×2 → identical checksums; both profiles present; LP-020 value printed in PR |
| M5 | `make analyze` from deleted `reports/analytics/` regenerates all 12 files; SSOT inputs diff-identical across the two runs |
| M6 | `make simulate && make ssot` ×2 → `git diff reports/NUMERIC_SSOT.md` empty on second run; `python scripts/check_ssot_consistency.py` exit 0 |
| M7 | §11.3 below, all ten rows |

## 11.3 DL-1..10 release verification (M7, execute literally)

| DL | Verification procedure | Pass predicate |
|----|------------------------|----------------|
| DL-1 | Fresh clone to temp dir; `.env` with token; `make setup && make backfill && make all` | exit 0 unattended; all artifacts below exist |
| DL-2 | Open `reports/NUMERIC_SSOT.md` | 5×6 cost matrix keys + `wrong_strategy_cost_<year>`×5 + `wrong_strategy_cost_total` + `best_strategy_5yr` present with tags |
| DL-3 | `ls reports/analytics/` vs SPEC-04 §6 list | 12/12 files; each .md ends with ≥400-char prose (AN-704 test green) |
| DL-4 | grep SSOT for `p95_next12m_` and `cvar95_next12m_` | 6 strategies × both metrics, tag SIMULATED; `make simulate` rerun → identical |
| DL-5 | Read `reports/EXEC_SUMMARY.md` | §§1–6 present; ≤2 pages; both CFO recommendations carry EUR numbers; GV-303 green |
| DL-6 | `dashboards/epra.pbix` + `docs/assets/dashboard_p*.png` | .pbix committed; 4 screenshots embedded in README |
| DL-7 | CI dashboard on main | 4/4 jobs green; coverage ≥ 80%; ruff/mypy/dbt clean |
| DL-8 | Actions → refresh.yml → `workflow_dispatch` | run green; artifacts uploaded; PR opened or cleanly skipped (SG-18) |
| DL-9 | Read LIMITATIONS.md against SPEC-08 §6 items 1–7 | every item present with computed numbers where defined |
| DL-10 | Read README top-down | headline question → SSOT-tagged answer before any tooling mention; §6 order complete; GV-303 green |

## 11.4 Definition of Ready / Done

Global DoR/DoD are normative in [00_MASTER_PLAN.md](00_MASTER_PLAN.md) §0.6–0.7
and are part of acceptance: a "done" task failing any global DoD row is not done,
regardless of its local AC.
