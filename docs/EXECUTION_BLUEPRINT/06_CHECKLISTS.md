# 06 — CHECKLISTS

Global lists apply to every milestone; per-milestone lists add the specifics.
A milestone PR description reproduces its lists with each row ticked + evidence
(test name, command output snippet, or file path). An unticked row = not done.

## 6.1 Global implementation checklist (every PR)

- [ ] Task cards' acceptance criteria verified against reality, one by one
- [ ] `uv run ruff check` + `ruff format --check` + `uv run mypy` clean
- [ ] `uv run pytest` green; coverage ≥ 80%; zero warnings introduced
- [ ] New/changed public functions: docstring with REQ IDs (W-2), ≤ ~60 lines (W-3)
- [ ] Stub-test rows for implemented functions deleted from `test_stubs_fail_loudly.py`
- [ ] Makefile target(s) un-stubbed exactly for what this milestone delivers
- [ ] No `data/` bulk files, no `.env`, no token anywhere (`git status` + guard hook)
- [ ] Conventional commit messages with REQ IDs (W-4, EN-090)

## 6.2 Global code-review checklist (reviewer or self-review before merge)

- [ ] Spec supremacy: every behavior traceable to a REQ ID or an ADR (A-1)
- [ ] No invented data, no gap-filling beyond ING-063's sanctioned rule (A-2)
- [ ] No scope creep: nothing from Charter §4.2 O-1..O-7 sneaked in (A-3)
- [ ] Determinism: no unseeded randomness, no dict/set iteration feeding output
      order, no wall-clock in computed values (A-4)
- [ ] Timezone doctrine: UTC stored, Vienna analyzed, conversions only in
      `timeutil`/`dim_calendar` (T-1, DM-011)
- [ ] Numbers in docs come from SSOT only (A-6) — or the doc is untouched
- [ ] Error paths raise; nothing warns-and-continues on a gate (EN-061)
- [ ] No duplicated logic vs existing modules (search performed)
- [ ] Anti-pattern scan against [09_ANTI_PATTERNS.md](09_ANTI_PATTERNS.md)

## 6.3 Global QA checklist (run, don't read)

- [ ] Full verification protocol (AGENTS §5) executed; outputs pasted into PR
- [ ] Idempotency spot-check: the milestone's `make` target run twice → second
      run changes nothing material (EN-050)
- [ ] One deliberate failure injected (bad fixture/config) → correct loud error
- [ ] New artifacts open/render (parquet readable, PNG viewable, md renders)

## 6.4 Scientific validation checklist (M4/M5/M6 only)

- [ ] Hand-computed micro-example reproduced by code (per module guide)
- [ ] Sanity relations hold: LP-040 ratios / AN-304 occupancy / ST-602 a–c
- [ ] Epistemic tags on every emitted SSOT row correct per Charter §5, E-2 honored
- [ ] Stochastic outputs: two clean runs → identical values (AN-705 / ST-405)
- [ ] Units verified end-to-end on one traced value (EUR vs EUR/MWh vs index — T-5)
- [ ] Caption rules present where required (LP-050, ST-502, RP-702)

## 6.5 Documentation checklist (every milestone)

- [ ] BUILD_LOG entry appended (date, shipped, gate evidence, open questions — W-5)
- [ ] Any SG resolution adopted → ADR merged, SG entry marked resolved
- [ ] Module docstrings updated from "not implemented" to real contracts
- [ ] This blueprint updated where reality diverged (status snapshot §0.9,
      checklist deltas) — blueprint drift is a bug

## 6.6 Repository hygiene checklist (every milestone)

- [ ] `.gitignore` still covers all bulk outputs; no stray committed artifacts
- [ ] `uv.lock` in sync with pyproject (`uv lock --check`)
- [ ] Directory layout still matches SPEC-07 §2 exactly
- [ ] CI required-jobs list matches the milestone's stage (jobs 3/4 added at M3/M6)

## 6.7 Per-milestone implementation specifics

**M1:** ING-070 contract tests green on real-excerpt fixtures · ING-080..085
green on real 2019→latest · validation report committed · SG-01/SG-02 ADRs
merged · cache dir populated locally but ignored by git.

**M2:** ING-111/094/101/103 green · reconciled ÖSPI CSV committed; entry files
deleted · ADR-003 station + ADR-004 series merged · calendar parquet covers
forward window.

**M3:** `dbt build` green on real AND fixture data · schema contract test
pinning §5 columns · CI job 3 required · SG-06/SG-13 ADRs merged · no model
reads files outside sources.yml mechanism.

**M4:** LP-040/041/042 green incl. persisted checksum · annual sums exact ·
peak share in [0.42, 0.48] and in SSOT inputs · flat_baseload built by config
switch only · SG-03/SG-04 ADRs merged.

**M5:** 12 artifacts regenerate from clean (AN-701) · AN-304 gate green ·
prose paragraphs pass AN-704 · `make analyze` ×2 identical (AN-705) · SSOT
input rows all VERIFIED.

**M6:** ST-601 goldens (human-approved) · ST-602 a/b/c hard-pass · ST-603
determinism + no-lookahead · ST-604 consistency · CI job 4 required · GV-302
key set complete · SG-07/SG-08/SG-09 ADRs merged.

**M7 / Release checklist:** DL-1..DL-10 each verified per
[11_ACCEPTANCE_CRITERIA.md](11_ACCEPTANCE_CRITERIA.md) §M7 · fresh-clone
rehearsal executed · refresh dry-run succeeded · screenshots embedded · GV-303
green over README + EXEC_SUMMARY · LIMITATIONS sections 1–7 finalized ·
SPEC-08 §7 sentence present in README.

## 6.8 Milestone record M1–M3 (reconciled 2026-09-30)

§6.1–6.6 are per-PR templates and stay unticked here; each milestone PR
reproduces and ticks them in its PR description, which this file does not
mirror. This section ticks the §6.7
per-milestone specifics that the repository itself evidences. An unticked row
is not done.

**M1**
- [x] ING-070 contract tests green on real-excerpt fixtures — `tests/test_raw_contracts.py`, fixtures under `tests/fixtures/entsoe/` (`docs/BUILD_LOG.md` 2026-07-21)
- [ ] ING-080..085 green on real 2019→latest — green only on data through 2024-02, with pass/fail scoped to complete years 2019–2023 (ADR-006, `reports/ingestion/validation_2026-07-23.md`); re-backfill to latest complete month outstanding
- [x] Validation report committed — `reports/ingestion/validation_2026-07-23.md`
- [x] SG-01/SG-02 ADRs merged — ADR-003, ADR-005
- [x] Cache dir ignored by git — `.gitignore` `data/cache/*`

**M2**
- [x] ING-111/094/103 green — `reports/ingestion/validation_2026-07-23.md`
- [x] ING-101 reconcile run exit 0 — recorded in `.planning/phases/EPRA-03-m2-auxiliary-data/03-VERIFICATION.md` (Post-Verification Resolution); not reproduced as a committed log
- [x] Reconciled ÖSPI CSV committed; entry files not in the repository — `data/manual/oespi_monthly.csv` (commit `9ab8999`); no `oespi_monthly_entry*.csv` tracked
- [ ] Station ADR + series ADR merged (§6.7 says "ADR-003 station + ADR-004 series"; the actual numbers are ADR-007 and ADR-008) — ADR-007 accepted; ADR-008 still `Status: proposed`
- [x] Calendar parquet covers the forward window — `dim_calendar`-spined marts run to 2028-01 (`reports/warehouse/dbt_build_2026-07-24.md`)

**M3**
- [x] `dbt build` green on real AND fixture data — `docs/BUILD_LOG.md` 2026-07-24 (real: PASS=63 WARN=1; fixture: PASS=64)
- [x] Schema contract test pinning §5 columns — `tests/unit/test_marts_contract.py` vs `dbt/contracts/marts_contract.yml`
- [ ] CI job 3 required — `dbt-check` job exists in `.github/workflows/ci.yml`; making it a required check (TP.02) is an open operator action (`.planning/STATE.md`)
- [x] SG-06/SG-13 ADRs merged — ADR-010, ADR-009
- [x] No model reads files outside the sources.yml mechanism — no `read_parquet`/`read_csv` in `dbt/models/` outside `sources.yml`

