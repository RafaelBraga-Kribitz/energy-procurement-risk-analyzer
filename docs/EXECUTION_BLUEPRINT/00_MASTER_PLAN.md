# 00 — MASTER PLAN: The Execution Operating System

Created: 2026-07-19 · Owner: Rafael Braga-Kribitz · Status: **active planning artifact**

---

## 0.1 What this blueprint is — and is not

This directory turns the repository's specifications into an **execution operating
manual**: an engineer or coding agent starts at the next open task in
[02_WBS.md](02_WBS.md), satisfies its Definition of Ready, implements, passes the
gates in [10_VALIDATION_GATES.md](10_VALIDATION_GATES.md), and moves on — without
needing new architectural decisions.

**Authority hierarchy (binding, from Charter §Authority):**

```
PROJECT_CHARTER.md  >  docs/SPEC-01..08  >  docs/ADR/*  >  this blueprint  >  code comments
```

- The blueprint **never overrides** a Charter rule or SPEC requirement. Where it
  appears to, the Charter/SPEC wins and the blueprint has a bug — fix the blueprint.
- Where a SPEC is ambiguous, the blueprint does not silently assume: the ambiguity
  is registered in [14_SPEC_GAPS.md](14_SPEC_GAPS.md) with a **proposed** decision.
  A proposed decision becomes binding only when adopted via ADR (GV-201..203) in
  the PR that implements it.
- Charter §4.2 O-5 caps governance weight. This blueprint is a **planning**
  artifact created at the owner's explicit request; it adds **zero** new CI jobs,
  registries, roles, or ceremony. Governance remains exactly the three SPEC-08
  mechanisms. Nothing in this directory is a gate unless it restates a gate that
  already exists in a SPEC or the Charter.

## 0.2 Document map (reading order for a new contributor)

| # | Document | Read when |
|---|----------|-----------|
| 00 | this file | always, first |
| 01 | [01_PHASES.md](01_PHASES.md) | to know where the project is and what phase rules apply |
| 02 | [02_WBS.md](02_WBS.md) | to pick your task — the backlog, fully decomposed |
| 03 | [03_MODULES.md](03_MODULES.md) | before touching any module — its full behavioral contract |
| 04 | [04_DEPENDENCIES.md](04_DEPENDENCIES.md) | to check ordering, parallelism, and the critical path |
| 05 | [05_IMPLEMENTATION_GUIDES.md](05_IMPLEMENTATION_GUIDES.md) | during implementation — the "how", gotchas, worked examples |
| 06 | [06_CHECKLISTS.md](06_CHECKLISTS.md) | before opening and before merging every PR |
| 07 | [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md) | measurable thresholds for every deliverable |
| 08 | [08_PATTERNS.md](08_PATTERNS.md) | when designing inside a module |
| 09 | [09_ANTI_PATTERNS.md](09_ANTI_PATTERNS.md) | before review — the mistakes that get PRs rejected |
| 10 | [10_VALIDATION_GATES.md](10_VALIDATION_GATES.md) | the no-progression rules per milestone |
| 11 | [11_ACCEPTANCE_CRITERIA.md](11_ACCEPTANCE_CRITERIA.md) | objective, runnable milestone acceptance |
| 12 | [12_RISK_REGISTER.md](12_RISK_REGISTER.md) | at phase start and whenever something smells wrong |
| 13 | [13_TRACEABILITY_MATRIX.md](13_TRACEABILITY_MATRIX.md) | to verify nothing exists without a spec anchor |
| 14 | [14_SPEC_GAPS.md](14_SPEC_GAPS.md) | whenever a SPEC leaves interpretation room — check here first |

Also mandatory context (not part of this blueprint): `PROJECT_CHARTER.md`,
`AGENTS.md`, `docs/SPEC-01..08`, `docs/ADR/`, `docs/BUILD_LOG.md`.

## 0.3 Mission restated (one sentence, from Charter §1)

Compute, from real data only, what each of four procurement strategy families
cost a calibrated 50 GWh/year Styrian consumer in 2021–2025 and what the
next-12-month cost distribution per strategy is — delivered as SSOT-backed
euro numbers, charts, a Power BI dashboard, and an executive summary.

Anything not serving that sentence is out of scope (Charter §4.2).

## 0.4 Execution model

- **Unit of delivery:** the milestone (M1..M7). One milestone = one PR (A-5,
  EN-090). Task granularity below milestone level exists for session planning
  and commit structure, not for PRs.
- **Unit of work:** the task (see [02_WBS.md](02_WBS.md)), sized ≈ one focused
  coding session (0.5–4 h). Tasks produce commits with conventional prefixes +
  REQ IDs (W-4).
- **Merge order:** M0 → **M2 → M1** → M3 → M4 → M5 → M6 → M7. The M2-before-M1
  swap is explicitly sanctioned by Charter R-1 mitigation ("Until it arrives,
  build M0 and M2") because M1's exit gate needs the live token. Development may
  run ahead on branches per [04_DEPENDENCIES.md](04_DEPENDENCIES.md) §parallel;
  merges never skip the order above.
- **Humans in the loop:** tasks labeled `[HUMAN]` cannot be done by an agent
  (AGENTS.md §2): token registration, ÖSPI transcription entries, golden
  approval, Power BI build, EXEC_SUMMARY §5 co-write.
- **Agents:** any Sonnet-class-or-better agent. Every session follows §0.7.

## 0.5 Task metadata conventions

- **ID:** `T<milestone>.<nn>` (e.g. `T3.05`). Preparatory/ops tasks use `TP.<nn>`.
- **Labels:**
  - `[TOKEN]` — requires the live ENTSO-E token; blocked until it arrives.
  - `[HUMAN]` — requires the human owner.
  - `[PAR]` — parallelizable with other `[PAR]` tasks of the same milestone.
  - `[CP]` — on the critical path ([04_DEPENDENCIES.md](04_DEPENDENCIES.md)).
- **Effort:** S (≤1 h), M (1–3 h), L (3–6 h; consider splitting before starting).
- **Traces:** every task lists the REQ IDs it implements. A task with no REQ ID
  must trace to a Charter § or an SG entry — otherwise it must not exist
  ([13_TRACEABILITY_MATRIX.md](13_TRACEABILITY_MATRIX.md)).

## 0.6 Global Definition of Ready (DoR)

A task may start only when ALL of the following hold (per-task cards add deltas):

1. All tasks in its `Depends on` list are merged or explicitly stacked on a branch.
2. The relevant SPEC sections and its [03_MODULES.md](03_MODULES.md) entry have
   been read in this session (not recalled from memory).
3. Any SG entry the task references has been resolved by ADR, or the task's work
   includes writing that ADR.
4. Required inputs exist (fixtures, config keys, upstream artifacts) — verified,
   not assumed.
5. For `[TOKEN]`/`[HUMAN]` labels: the dependency is actually available.

## 0.7 Global Definition of Done (DoD)

A task is done only when ALL of the following hold (per-task cards add deltas —
they never subtract):

1. Code complete per the task's acceptance criteria; no `TODO`/`FIXME`/commented-out
   code left behind.
2. `uv run ruff check` + `ruff format --check` + `mypy` clean; zero new warnings
   in pytest output.
3. Tests for the task's contracts exist **in the same commit** (W-1) and the full
   suite passes with coverage ≥ 80% (EN-071).
4. Public functions' docstrings carry their REQ IDs (W-2); functions ≤ ~60 lines (W-3).
5. No duplicated logic (search before writing: `grep -r` for the concept).
6. Determinism preserved: if the task touches anything stochastic or ordering-
   sensitive, the relevant determinism test (AN-705 / ST-405 / LP-040) passes twice.
7. No number typed into README/EXEC_SUMMARY except copied from the current SSOT (A-6).
8. Artifacts the task claims to produce actually exist at the specified paths.
9. Milestone-relevant checklist rows in [06_CHECKLISTS.md](06_CHECKLISTS.md)
   remain satisfiable (spot-check the ones your change touches).
10. `docs/BUILD_LOG.md` updated only at milestone completion (W-5) — not per task.

## 0.8 Session protocol for coding agents

**Start of session:** read this file §0.1–0.7 → `AGENTS.md` §1–2 → the milestone's
phase card in [01_PHASES.md](01_PHASES.md) → your task card in [02_WBS.md](02_WBS.md)
→ the module contracts in [03_MODULES.md](03_MODULES.md) → the milestone guide in
[05_IMPLEMENTATION_GUIDES.md](05_IMPLEMENTATION_GUIDES.md). Verify DoR. Then code.

**End of session:** run the verification protocol (AGENTS.md §5); tick the task's
acceptance criteria one by one against reality (not intention); commit with REQ IDs;
if the milestone is complete, walk [06_CHECKLISTS.md](06_CHECKLISTS.md) and
[10_VALIDATION_GATES.md](10_VALIDATION_GATES.md) and write the BUILD_LOG entry.

**Never:** silently deviate from a SPEC (A-1), invent data (A-2), widen a gate
without ADR, mix milestones in one PR (A-5), or leave a stub half-implemented
(a function either raises `NotImplementedError` naming its milestone, or is fully
implemented and tested — nothing in between).

## 0.9 Current status snapshot (update on every milestone merge)

| Milestone | State | Evidence |
|-----------|-------|----------|
| M0 bootstrap | **DONE** (commit `chore: M0 bootstrap…`, 2026-07-19) | ruff/mypy clean, 51 tests, cov 99.67% |
| M1 ENTSO-E ingestion | not started — code tasks unblocked, live backfill `[TOKEN]` (~3 days) | — |
| M2 auxiliary data | not started — fully unblocked | — |
| M3 dbt warehouse | not started | — |
| M4 consumer profile | not started | — |
| M5 analytics | not started | — |
| M6 strategies | not started | — |
| M7 reporting & refresh | not started | — |

Blocked-only-by-token work is exactly: T1.09 (live backfill+validation) and the
fixture-refresh half of T1.03. Everything else in M1–M7 is specifiable and much
of it buildable now — see [04_DEPENDENCIES.md](04_DEPENDENCIES.md) §token-window.
