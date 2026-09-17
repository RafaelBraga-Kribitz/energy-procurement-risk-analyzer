---
phase: EPRA-04-m3-dbt-warehouse
plan: 08
subsystem: infra
tags: [github-actions, dbt, duckdb, ci, makefile]

# Dependency graph
requires:
  - phase: EPRA-04-m3-dbt-warehouse plan 05
    provides: scripts/bootstrap_fixture_warehouse.py (D-04 network-free 2022-2024 synth the dbt-check job runs)
  - phase: EPRA-04-m3-dbt-warehouse plan 06
    provides: tests/unit/test_marts_contract.py, dbt/contracts/marts_contract.yml (D-07 schema contract SC#2)
  - phase: EPRA-04-m3-dbt-warehouse plan 07
    provides: make warehouse / src/epra/warehouse/report.py (D-02 build-report writer whose runtime markdown this plan commits)
provides:
  - .github/workflows/ci.yml dbt-check job (EN-080 job 3) — bootstrap --force then cd dbt && dbt build, network-free, separate from test:
  - reports/warehouse/dbt_build_2026-07-24.md — committed D-02 real-data build report
  - docs/BUILD_LOG.md M3 entry — both-builds-green evidence, data/ uncommitted
affects: [EPRA-05-m4-consumer-profile (M3 closed; fct_consumer_load_hourly stand-in replaced at M4), EPRA-08-m7-reporting (EN-080 job 4 ssot-check still placeholder)]

# Actuals
actuals:
  tokens: 2200
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EN-080 job 3 is a genuinely separate GitHub Actions job (not folded into test:) so it can be made a required check independently (TP.02)"
    - "CI dbt-check is network-free: bootstrap_fixture_warehouse.py --force synthesizes the 2022-2024 window; never requires ENTSOE_API_TOKEN or a real backfill (D-01 split-by-environment)"
    - "Only markdown evidence is committed (reports/warehouse/dbt_build_<date>.md + BUILD_LOG); epra.duckdb and synthesized parquet stay gitignored (DM-001/D-02)"

key-files:
  created:
    - reports/warehouse/dbt_build_2026-07-24.md
  modified:
    - .github/workflows/ci.yml
    - docs/BUILD_LOG.md

key-decisions:
  - "dbt-check stays a separate job from test: (EN-080 job 3, TP.02); the job runs bootstrap --force then cd dbt && dbt build then the D-07 schema-contract pytest --no-cov (the contract is meaningful only after dbt build, so the test: job skips it when the warehouse is absent)."
  - "SC#3 is proven in an isolated data root (--data-root) so this repository's committed data/manual/oespi_monthly.csv is never overwritten by --force."
  - "TP.02 (GitHub branch-protection required-check flip for dbt-check) remains operator-only and out of code scope — the job exists; making it required is a GitHub settings action."

patterns-established:
  - "Pattern: CI jobs that need a warehouse run the D-04 generator first; pytest that reads information_schema skips (does not false-pass) when epra.duckdb is missing"
  - "Pattern: milestone close-out commits the runtime markdown report + BUILD_LOG entry and asserts git status --porcelain data/ is empty"

requirements-completed: [REQ-DWH-01, D-01, D-02]

coverage:
  - id: D1
    description: "ci.yml has a required-check-ready dbt-check job (bootstrap --force then dbt build), separate from test:, network-free (EN-080 job 3, SC#3)"
    requirement: "REQ-DWH-01"
    verification:
      - kind: other
        ref: "python -c yaml.safe_load ci.yml → 'dbt-check job present'; job steps = checkout, setup-uv 3.12, uv venv --clear && uv pip install -e '.[dev]', bootstrap_fixture_warehouse.py --force, cd dbt && uv run dbt build, pytest tests/unit/test_marts_contract.py -m 'not live' --no-cov"
        status: pass
    human_judgment: false
  - id: D2
    description: "Network-free CI fixture dbt build is green without a full local backfill (SC#3) — isolated data root, PASS=64 WARN=0 ERROR=0 SKIP=0 TOTAL=64"
    requirement: "D-01"
    verification:
      - kind: other
        ref: "2026-09-01 re-run: uv run python scripts/bootstrap_fixture_warehouse.py --force --data-root /tmp/iso-epra/data then dbt build --project-dir /tmp/iso-epra/dbt → Done. PASS=64 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=64 (1.30s). Workspace data/raw and data/manual/oespi_monthly.csv untouched."
        status: pass
    human_judgment: false
  - id: D3
    description: "D-07 schema-contract pytest is green so mart schemas byte-match SPEC-02 §5 (SC#2)"
    requirement: "REQ-DWH-01"
    verification:
      - kind: unit
        ref: "uv run pytest tests/unit/test_marts_contract.py -m 'not live' --no-cov: 6 passed (2026-09-01, against the isolated fixture warehouse copied to gitignored data/warehouse/epra.duckdb)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Committed D-02 real-data build report + BUILD_LOG M3 entry; git status clean of data/ (DM-001)"
    requirement: "D-02"
    verification:
      - kind: other
        ref: "reports/warehouse/dbt_build_2026-07-24.md committed in df68473 (per-year counts, month coverage, 2022-08 delta=0.0000, stand-in flags); docs/BUILD_LOG.md M3 entry; git status --porcelain data/ empty → DATA_CLEAN"
        status: pass
    human_judgment: false
  - id: D5
    description: "Phase-exit checkpoint — operator confirms both builds green and TP.02 required-check flip; M3 PR/ceremony close-out"
    requirement: "D-01"
    verification:
      - kind: other
        ref: "Automated how-to-verify items 2–4 re-run 2026-09-01 (SC#3 fixture build, SC#2 contract, git clean of data/). SC#1 real-data make warehouse is evidenced by the committed 2026-07-24 report (this cloud checkout has no data/raw backfill; A-2: not fabricated)."
        status: pass
      - kind: manual_procedural
        ref: "TP.02 GitHub branch-protection: mark dbt-check required for merge on main — operator GitHub settings, out of code scope"
        status: unknown
    human_judgment: true
    rationale: "TP.02 (branch-protection required-check flip) is a GitHub org/repo settings action the agent cannot perform. Automated SC#1/#2/#3 evidence is in D1–D4; do not auto-approve the GitHub settings change."

duration: 40min
completed: 2026-09-01
status: complete
---

# Phase EPRA-04 Plan 08: CI dbt-check Job + M3 Close-Out Summary

**Required `dbt-check` CI job (EN-080 job 3) runs the network-free 2022–2024 fixture warehouse then `dbt build`; the committed D-02 real-data report + BUILD_LOG M3 entry close REQ-DWH-01's three success criteria**

## Performance

- **Duration:** ~40 min (GSD close-out 2026-09-01; production Tasks 1–2 committed 2026-07-24)
- **Started:** 2026-09-01T16:47:00Z (close-out resume; original execution 2026-07-24T09:54:56Z)
- **Completed:** 2026-09-01T16:55:00Z
- **Tasks:** 3/3 (Tasks 1–2 already on `main`; Task 3 ceremony + re-verification this session)
- **Files modified:** 3 (1 created at original execution: `reports/warehouse/dbt_build_2026-07-24.md`; 2 modified: `.github/workflows/ci.yml`, `docs/BUILD_LOG.md`) plus this SUMMARY / STATE / ROADMAP close-out

## Accomplishments
- `.github/workflows/ci.yml` `dbt-check` job is live and separate from `test:`: checkout → setup-uv Python 3.12 → `uv venv --clear && uv pip install -e ".[dev]"` → `bootstrap_fixture_warehouse.py --force` → `cd dbt && uv run dbt build` → D-07 schema-contract pytest `--no-cov`. Top-of-file comment records jobs 1–3 live; job 4 (`ssot-check`) remains an M6 placeholder.
- Isolated, network-free SC#3 re-run (2026-09-01): `bootstrap_fixture_warehouse.py --force --data-root /tmp/iso-epra/data` then `dbt build` against a copied `dbt/` tree → **PASS=64 WARN=0 ERROR=0 SKIP=0 TOTAL=64** in 1.30s. This repository's `data/raw/` (empty) and committed `data/manual/oespi_monthly.csv` were not touched.
- D-07 schema contract (SC#2) re-run: `uv run pytest tests/unit/test_marts_contract.py -m "not live" --no-cov` → **6 passed**.
- D-02 real-data report `reports/warehouse/dbt_build_2026-07-24.md` is committed (SC#1 evidence from the 2026-07-24 local `make warehouse`: dbt PASS=63 WARN=1 `predup_count_prices` ERROR=0; 2022-08 delta `0.0000`; stand-in flags). `git status --porcelain data/` is empty (DM-001).
- `docs/BUILD_LOG.md` M3 entry records both-builds-green status. Production Task 1/2 commits were already on `main` via PR #1; this close-out writes the missing GSD `04-08-SUMMARY.md` (illegal partial-plan state: production commits existed without SUMMARY).

## Task Commits

Each task was committed atomically:

1. **Task 1: CI dbt-check job — bootstrap fixture warehouse + dbt build** - `422aabe` (feat)
2. **Task 2: Real-data dbt build + committed build report + BUILD_LOG entry** - `df68473` (docs)
3. **Task 3: Phase-exit checkpoint — both builds green + PR assembly** - this SUMMARY commit (docs); automated how-to-verify items re-run 2026-09-01. TP.02 branch-protection flip remains operator-only.

**Plan metadata:** this commit `docs(04-08): complete CI dbt-check + M3 close-out plan`

Follow-up CI fixes already on `main` (not this plan's `files_modified`, recorded as issues below): `09b682f` (`uv venv --clear`), `ad68b36` (skip marts contract when warehouse missing).

## Files Created/Modified
- `.github/workflows/ci.yml` - `dbt-check` job (EN-080 job 3) replacing the commented placeholder
- `reports/warehouse/dbt_build_2026-07-24.md` - D-02 real-data build report (per-year counts, month coverage, 2022-08 delta, stand-in flags)
- `docs/BUILD_LOG.md` - append-only M3 entry
- `.planning/phases/EPRA-04-m3-dbt-warehouse/04-08-SUMMARY.md` - this file
- `.planning/STATE.md` / `.planning/ROADMAP.md` - plan counter + Phase 4 8/8

## Decisions Made
- Keep `dbt-check` a genuinely separate job from `test:` so it can be made a required check independently (EN-080 job 3, TP.02). The D-07 pytest lives on `dbt-check` (needs a built warehouse) rather than on `test:` (fresh checkout has no `epra.duckdb`).
- Prove SC#3 in an isolated `--data-root` so `--force` cannot clobber the committed ÖSPI CSV (the bootstrap guard treats `data/manual/oespi_monthly.csv` as populated real data).
- Do not fabricate a real-data `make warehouse` in this cloud checkout (no `data/raw/` backfill; A-2). SC#1 remains evidenced by the committed 2026-07-24 report from the original operator machine.
- TP.02 (mark `dbt-check` required on `main`) is human GitHub settings — not auto-approved (plan `gate="blocking-human"`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `uv venv --clear` so setup-uv's pre-created `.venv` does not fail the job**
- **Found during:** Task 1 CI after the original `422aabe` job shape (`uv venv && uv pip install`)
- **Issue:** `astral-sh/setup-uv@v5` may already create `.venv`; a bare `uv venv` then fails with "venv already exists"
- **Fix:** `uv venv --clear` on lint/test/dbt-check (commit `09b682f`, already on `main`)
- **Files modified:** `.github/workflows/ci.yml`
- **Verification:** subsequent CI jobs start; local isolated dbt-check sequence green 2026-09-01
- **Committed in:** `09b682f` (follow-up, already on `main`)

**2. [Rule 1 - Bug] Schema-contract pytest skips when warehouse missing (no false pass on `test:`)**
- **Found during:** CI `test:` job on a fresh checkout (no `epra.duckdb`)
- **Issue:** `connect(..., read_only=True)` raised IOException; `test:` would fail even though D-07 is only meaningful after `dbt build`
- **Fix:** `_marts_schema_populated()` returns False when the warehouse file is absent; tests skip. The `dbt-check` job runs the same pytest after `dbt build` so SC#2 is still enforced.
- **Files modified:** `tests/unit/test_marts_contract.py`
- **Verification:** `test:` job no longer requires a warehouse; this session's post-build pytest 6 passed
- **Committed in:** `ad68b36` (follow-up, already on `main`)

**3. [Rule 2 - Missing Critical] `dbt-check` also runs the D-07 pytest after `dbt build`**
- **Found during:** Task 1 (the plan's literal job was bootstrap + `dbt build` only)
- **Issue:** `test:` skipping the contract when the warehouse is absent would leave SC#2 unenforced in CI unless `dbt-check` runs it
- **Fix:** extra step on `dbt-check`: `uv run pytest tests/unit/test_marts_contract.py -m "not live" --no-cov`
- **Files modified:** `.github/workflows/ci.yml`
- **Verification:** isolated fixture build + pytest 6 passed (2026-09-01)
- **Committed in:** `ad68b36` / current `ci.yml` on `main`

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 bug) — all already on `main` before this close-out
**Impact on plan:** CI reliability only; no change to warehouse models or DM-06x tests. Isolated SC#3 proof matches the plan's "do not run --force against real data" prohibition.

## Issues Encountered
- This plan's production commits (`422aabe`, `df68473`) landed on `main` via PR #1 without a `04-08-SUMMARY.md`, leaving GSD in the illegal partial-plan state (production commits, no SUMMARY). Close-out writes the SUMMARY and advances STATE/ROADMAP rather than re-implementing Tasks 1–2.
- This cloud checkout has no real `data/raw/` ENTSO-E/GeoSphere parquet (only committed `data/manual/oespi_monthly.csv`). SC#1 is not re-run here (A-2); it is evidenced by the committed 2026-07-24 report. SC#3 is re-run in an isolated tree.
- TP.02 (GitHub branch-protection required-check flip) is still operator-only.

## User Setup Required

**GitHub settings (TP.02, operator):** on `main` branch protection, mark the `dbt-check` job a required status check alongside `lint` and `test`. The job is already in `ci.yml`; this flip is not a code change.

No new secrets. `dbt-check` must stay credential-free (D-01).

## Next Phase Readiness

All eight Phase EPRA-04 plans now have SUMMARYs. Ready for `/gsd-verify-work` (Phase 4) then `/gsd-discuss-phase` Phase 5 (M4 consumer profile). `fct_consumer_load_hourly` / `fct_procurement_cost_monthly` remain stand-ins until M4/M6. No code blockers; TP.02 is GitHub settings only.

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-09-01*

## Self-Check: PASSED

- `[ -f .github/workflows/ci.yml ]` `[ -f docs/BUILD_LOG.md ]` `[ -f reports/warehouse/dbt_build_2026-07-24.md ]` `[ -f .planning/phases/EPRA-04-m3-dbt-warehouse/04-08-SUMMARY.md ]` — all present
- `git log --oneline --all --grep="04-08"` returns `422aabe`, `df68473` (and this SUMMARY commit)
- Acceptance criteria: yaml `dbt-check` present; isolated bootstrap+`dbt build` PASS=64; pytest contract 6 passed; `git status --porcelain data/` empty
- Plan-level verification: SC#2 and SC#3 re-green 2026-09-01; SC#1 evidenced by committed report (no local `data/raw/`)
