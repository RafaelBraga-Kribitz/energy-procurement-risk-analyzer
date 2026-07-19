# 07 — QUALITY STANDARDS (measurable thresholds)

Where a threshold restates a SPEC gate, the SPEC citation is authoritative.
Blueprint-added thresholds are marked **[BP]** — advisory unless promoted by ADR;
they exist so "good enough" is never a judgment call.

## 7.1 Code

| Standard | Threshold | Enforcement |
|----------|-----------|-------------|
| Line coverage `src/epra` | ≥ 80% (EN-071); **[BP]** aim ≥ 90% for `common`, `consumer`, `strategies` | pytest `--cov-fail-under=80` (hard) |
| Function length | ≤ ~60 lines (W-3) | review |
| Cyclomatic complexity | **[BP]** ≤ 10 per function; a function needing more is decomposed | review (no new tooling — O-5) |
| Module length | **[BP]** ≤ 500 lines; split before exceeding | review |
| Typing | mypy `--strict`, zero `# type: ignore` without a reason comment | CI job 1 |
| Lint/format | ruff clean, line 100 (EN-002) | CI job 1 |
| Warnings | pytest runs warning-clean; new warnings are fixed or explicitly filtered with a comment | review |
| TODO/FIXME | zero in merged code; open work lives in WBS/BUILD_LOG | review + **[BP]** grep check |

## 7.2 Runtime & memory budgets

| Operation | Budget | Source |
|-----------|--------|--------|
| `make all` (data present) | < 30 min laptop | EN-050 |
| Forward bootstrap N=2000 | < 10 min | ST-406 |
| `make backfill` (live) | **[BP]** < 90 min incl. politeness sleeps | guide §5.1 |
| `dbt build` (real data) | **[BP]** < 5 min | T3.05 |
| Full pytest suite | **[BP]** < 120 s (fixture-based, no network) | EN-070 |
| Peak memory any step | **[BP]** < 4 GB (hourly frames ≈ 60k rows × few cols — far below; exceeding it signals an algorithmic bug, not a hardware need) | review |

## 7.3 Determinism & reproducibility (hard, all from SPECs)

- Two consecutive `make all` runs on identical data ⇒ identical SSOT values (A-4).
- Profile: bit-stable sha256 golden (LP-040); config change ⇒ checksum change (LP-042).
- Analytics: `make analyze` ×2 ⇒ identical SSOT inputs (AN-705); HMM restarts
  seeded 42..51, deterministic tie-break (guide §5.5).
- Strategies: seed 42, pinned draw order; `make simulate` ×2 ⇒ clean diff (ST-405).
- Fixtures pinned; dependency pins changed only via ADR (SPEC-07 §3).
- **[BP]** Nothing computed may depend on: wall clock (except sanctioned
  `updated_at`/`ingested_at` metadata columns), env vars other than the token,
  locale, or filesystem iteration order.

## 7.4 Scientific correctness

- Every published number: exactly one epistemic tag; E-1/E-2/E-3 honored.
- Sanity gates are hard: ING-082 ranges, AN-304 occupancy, ST-602 relations —
  failing means investigate, never widen (ADR required for any widening).
- Unit discipline: column names carry units (DM-005); one traced end-to-end
  unit check per milestone (checklist 6.4).
- Statistical method pins: quantiles/CVaR per SG-08; HMM/GARCH exact
  configurations per AN-302/303 — no "improvements" without ADR.

## 7.5 Data quality

- Raw is raw (ING-004): zero transformations in `data/raw` beyond metadata columns.
- NULLs stay NULL (P-1); the only sanctioned fills: ING-063 (A03, counted+logged)
  and dbt dedup (DM-020, counted+warned).
- Gate coverage: every dataset entering the warehouse has at least existence,
  range, coverage, and cross-dataset gates (SPEC-01 §§8–11 enumerate them).

## 7.6 Visualization (RP-70x, restated as pass/fail)

Every PNG: 12×6 in @150 dpi Agg · business-phrased title · axis labels with
units · source note bottom-left · epistemic tag bottom-right when CALIBRATED/
SIMULATED shown · Okabe-Ito strategy colors from `style.STRATEGY_COLORS` only ·
English/dot-decimal · **[BP]** chart tests inspect matplotlib objects, never
pixel-diff (cross-platform font variance).

## 7.7 Documentation completeness

- README: §6 order, zero non-SSOT numbers (RP-601/GV-303-checked), reproduce
  block ≤ 5 commands.
- EXEC_SUMMARY: ≤ 2 pages, §§1–6 present, recommendation carries euro numbers.
- LIMITATIONS: sections 1–7 (SPEC-08 §6) each with concrete computed values
  where applicable — no vague hedging.
- BUILD_LOG: one entry per milestone with gate evidence.
- Blueprint status snapshot current ([00_MASTER_PLAN.md](00_MASTER_PLAN.md) §0.9).

## 7.8 Coding standards (beyond lint — normative)

- **Naming:** snake_case modules/functions; frozen dataclasses/pydantic models
  in PascalCase; units in column AND variable names for physical quantities
  (`price_eur_mwh`, never `price`); REQ-ID-bearing constants UPPER_SNAKE with a
  citation comment. Test names state the behavior, not the function
  (`test_dst_day_hour_counts`, not `test_local_hours`).
- **Folder ownership:** `common/` = shared infra only (imports nothing from
  epra); `ingest/` = source→raw; `dbt/` = raw→marts; `consumer|analytics|
  strategies/` = marts→results; `report/` = results→artifacts; `scripts/` =
  CLI shells over `epra` functions. A file that doesn't fit one owner is a
  design smell — stop and check [03_MODULES.md](03_MODULES.md).
- **Import rules:** the layer law in [04_DEPENDENCIES.md](04_DEPENDENCIES.md)
  §4.1; stdlib → third-party → first-party grouping (ruff I); no relative
  imports beyond one dot; no `import *`; heavyweight libs (hmmlearn, arch,
  matplotlib) imported inside the modules that use them, never in `common`.
- **Logging pattern:** `logger = logging.getLogger(__name__)` per module;
  f-strings; one INFO per pipeline step with counts; per-request lines per
  ING-008; no print() in `src/` (scripts may print user-facing output).
- **Configuration pattern:** constructor-inject `Settings`/cfg objects; new
  keys = model + YAML + drift test, same commit; secrets only via
  `entsoe_token()`.
- **Error handling:** custom exceptions per package (`IngestAuthError`,
  `ContractError`, `GateFailure`, …) subclassing a package base; messages carry
  expected-vs-actual; never catch to continue past a contract.
- **Testing philosophy:** contract-first (fixtures pin external shapes; schema
  tests pin internal shapes; goldens pin results); every gate has a failing-case
  test; no test touches the network (EN-070) or wall-clock; synthetic data is
  crafted so expected values are hand-computable.
- **Docstrings:** public functions: one-line summary + `Implements: <REQ IDs>`
  (W-2); modules: contract summary. No redundant param prose for obvious types.
- **Commits:** conventional prefix + REQ IDs (W-4, EN-090); one logical change;
  imperative mood.
- **PRs:** one milestone (A-5); description = gate checklist with evidence
  ([06_CHECKLISTS.md](06_CHECKLISTS.md)); no drive-by refactors.
- **ADR requirements:** GV-203 triggers verbatim + every SG adoption; ADRs are
  append-only; superseding references the old.
- **Refactoring policy:** allowed within a milestone's PR only for code that
  milestone touches; cross-cutting refactors are their own `chore:` PR between
  milestones with zero behavior change (SSOT/goldens byte-identical as proof).
- **Technical debt policy:** debt is either (a) a WBS note with an owner
  milestone, or (b) not accepted. No TODO comments in code; no "temporary"
  hacks without a WBS row and a removal criterion.
