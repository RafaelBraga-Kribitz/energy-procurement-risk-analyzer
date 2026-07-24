# AGENTS.md — Build Playbook for AI Agents

You are an AI coding agent (Sonnet-class or better) building the Energy Procurement Risk
Analyzer. This file tells you HOW to work. WHAT to build is in `PROJECT_CHARTER.md` and
`docs/SPEC-01…08`. Read them in the Charter §9 order before writing any code.

**Claude Code ↔ Cursor:** progress and intent live only under `.planning/` (not chat history).
Before switching runtimes run `/gsd-pause-work`; after a limit/crash open the other runtime and
run `/gsd-resume-work` or `/gsd-next`. Prefer `.planning/graphs/GRAPH_REPORT.md` /
`/gsd-graphify query` for codebase orientation. Full playbook: `.planning/CONTINUITY.md`.

---

## 1. Non-negotiable rules

- A-1 **Spec supremacy.** If code and spec disagree, the spec wins. If two specs disagree,
  the Charter wins. If reality (an API, a library) makes a requirement impossible AS
  WRITTEN, you: (1) write an ADR (SPEC-08 §2), (2) implement the closest behavior that
  preserves the requirement's OUTPUT CONTRACT, (3) reference the ADR in the code docstring.
  You never silently deviate.
- A-2 **No invented data.** You never fabricate a price, index value, temperature, or any
  external fact. Gaps stay NULL and get documented. If a validation gate fails, you
  investigate the pipeline — you do not adjust data to pass, and you do not widen gates
  without an ADR.
- A-3 **No scope creep.** Charter §4.2 lists prohibited work (forecasting, apps, more
  strategies, more sensitivities, heavy governance). If you think something extra would be
  "nice", write it as one line under "Future work" in the README and move on.
- A-4 **Determinism.** Every stochastic step is seeded per spec. Two consecutive runs of
  `make all` on the same data must produce identical SSOT values. If you find
  nondeterminism, fixing it takes priority over new features.
- A-5 **One milestone, one PR.** Never mix milestones. PR description lists each exit-gate
  item with its status.
- A-6 **Numbers only from SSOT.** You never type a result number into README/EXEC_SUMMARY
  by hand except by copying from the current `reports/NUMERIC_SSOT.md`, and CI will check
  you did (GV-303).
- A-7 **Secrets.** The ENTSO-E token exists only as env var. If you ever print, commit, or
  log it, stop everything and tell the human to rotate it.
- A-8 **Honesty artifacts are load-bearing.** LIMITATIONS.md, epistemic tags, and caption
  rules (ST-502, LP-050) are acceptance criteria, not decoration.

## 2. When to STOP and ask the human

1. ENTSO-E registration/token issues (human owns the account).
2. Any gate failure you cannot root-cause within 2 focused attempts.
3. ÖSPI source page structure/methodology ambiguity (ING-102 decision) — propose, ask,
   then ADR.
4. Anything that would require touching Charter §4.2 prohibitions.
5. Power BI build (M7): the .pbix is a human task; you prepare `exports/` and the
   `dashboards/README.md` build instructions per SPEC-06 §4 and hand off.
6. Golden regeneration (EN-072/ST-601): propose the regeneration with a diff of old vs
   new values and WHY; human approves.

## 3. Build order and gates (from Charter §7 — expanded into agent tasks)

### M0 — Bootstrap
Create repo layout (SPEC-07 §2), pyproject with pinned deps (SPEC-07 §3), Makefile
targets as no-op stubs that fail with "not implemented" (so `make all` fails loudly, not
silently), ruff/mypy/pre-commit config, `ci.yml` with lint+test jobs, one smoke test.
**Gate:** `make setup && make lint && make test` green locally and in CI.

### M1 — ENTSO-E ingestion
Implement `common/` (config, logging, timeutil, db) first, then `ingest/entsoe.py` +
`ingest/validate.py` per SPEC-01 §§2–8. Write fixture-based unit tests (EN-070) including
the 15-min aggregation fixture (ING-062) and DST fixtures. Run real backfill locally
(human supplies token), run `make validate-ingest`, commit the validation report.
**Gate:** ING-070 contract tests green; ING-080…085 gates green on real 2019→latest data.

### M2 — Auxiliary data
`geosphere.py` (with ING-091 discovery, ADR the station), `oespi.py` loader +
`scripts/oespi_reconcile.py` (the human or a second agent session does the second
transcription entry), `calendar.py`. **Gate:** ING-094/101/103/111 green;
`data/manual/oespi_monthly.csv` committed with both entries reconciled.

### M3 — dbt warehouse
dbt project per SPEC-02. Build the fixture-bootstrap script for CI (EN-080 job 3).
**Gate:** `dbt build` green on real data AND on fixtures in CI; mart schemas byte-match
SPEC-02 §5 (schema test comparing information_schema to a committed contract YAML).

### M4 — Consumer profile
`consumer/profile.py` per SPEC-03 algorithm, both profiles, golden + property tests.
**Gate:** LP-040…042 green; `consumer_peak_share` lands in SSOT inputs.

### M5 — Analytics
A1→A2→A4→A3 (regimes last; they're the fiddly ones). Charts obey SPEC-06 §7.
**Gate:** AN-701…705, including the AN-304 crisis-regime sanity gate.

### M6 — Strategies
`calibration.py` (ST-201…204) → `retrospective.py` (S1 first, then S2/S3/S4) →
sensitivities → `forward_risk.py` (implement the vectorized ST-406 design directly) →
`generate_ssot.py`. **Gate:** ST-601…604; especially ST-602 sanity relations — if
(a) fails, debug calibration before anything else.

### M7 — Reporting & refresh
Exports, executive charts, EXEC_SUMMARY (human co-writes §5 recommendation), README,
LIMITATIONS, `refresh.yml`, dashboards handoff docs, dashboard screenshots (human).
**Gate:** Charter §6 DL-1…DL-10 checklist, each item ticked in the PR description.

## 4. Working style requirements

- W-1: TDD-lean: for every REQ with a testable contract, the test lands in the same
  commit as the implementation.
- W-2: Docstrings on public functions state the REQ IDs they implement (`Implements:
  ING-063, ING-080`). This makes spec-tracing greppable: `grep -r "ING-063" src tests`.
- W-3: Keep functions under ~60 lines; pipelines are compositions, not monoliths.
- W-4: Commit messages: conventional prefix + REQ IDs touched.
- W-5: After each milestone, update a short `docs/BUILD_LOG.md` entry: date, what
  shipped, gate evidence (test run output snippet), open questions. Append-only.

## 5. Verification protocol (run before claiming any milestone done)

```
make lint && make test          # code quality
make validate-ingest            # if data-touching milestone
(cd dbt && dbt build)           # if model-touching milestone
make ssot && git diff reports/NUMERIC_SSOT.md   # results changed? explain in PR
python scripts/check_ssot_consistency.py        # doc/number integrity
```

Then re-read the milestone's gate list in this file and tick every item explicitly in
the PR. An unticked item means the milestone is NOT done — no exceptions.

## 6. Known traps (learn from these in advance)

- T-1: Timezones. Everything analytic is Europe/Vienna local; everything stored is UTC.
  If an annual mean looks ~right but gates fail marginally, check DST handling first.
- T-2: 15-min vs hourly (R-2). Mean, not sum, when aggregating prices; mean of MW for
  load. ING-062's fixture exists because agents get this wrong.
- T-3: Negative prices break log-returns. SPEC-04 uses arithmetic differences on purpose.
  Do not "improve" this with logs.
- T-4: entsoe-py returns tz-aware pandas Series with local or UTC indexes depending on
  version — normalize to UTC immediately at the ingestion boundary (ING-031) and never
  think about it again.
- T-5: ÖSPI index base ≠ EUR/MWh. The translation runs through P_ref anchors (ST-201…204).
  If S3 costs come out absurd (10× spot), you multiplied an index by volume directly.
- T-6: The bootstrap must draw a month's PRICES and ÖSPI together (ST-401 step 2) —
  drawing them independently destroys the spot/contract correlation the whole comparison
  rests on.
