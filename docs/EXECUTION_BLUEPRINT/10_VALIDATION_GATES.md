# 10 — VALIDATION GATES: the no-progression ladder

Every milestone passes ALL of its gates before its PR merges. Gates restate
existing SPEC/Charter requirements organized into six lanes; **no new gate
machinery is introduced** (Charter O-5) — this document is an index with
evidence requirements.

**Evidence rule:** each gate row in the milestone PR carries either a test name
(`pytest tests/…::test_x`), a command + trailing output lines, or an artifact
path. "It works" is not evidence.

## Gate lanes

| Lane | What it proves | Mechanism |
|------|----------------|-----------|
| **G-ENG** Engineering | code quality, types, tests, coverage | CI jobs 1–2 (ruff/mypy/pytest, EN-080) |
| **G-DATA** Data quality | real data within plausibility contracts | ING/DM gate suites (SPEC-01 §§8–11, SPEC-02 §6) |
| **G-SCI** Scientific | formulas correct, sanity relations hold, determinism | golden/property/sanity tests (LP/AN/ST series) |
| **G-DOC** Documentation | honesty artifacts + logs current | checklist 6.5; GV-303 from M6 |
| **G-GOV** Governance | tags, ADRs, SSOT integrity | SPEC-08 mechanisms; CI job 4 from M6 |
| **G-REL** Release/Portfolio | audience-ready deliverables | Charter §6 DL-1..10 (M7 only) |

## Per-milestone gate matrix

| Milestone | G-ENG | G-DATA | G-SCI | G-DOC | G-GOV | G-REL |
|-----------|-------|--------|-------|-------|-------|-------|
| M1 | CI 1–2 green | ING-070; ING-080..085 on real data; report committed | resolution/DST/A03 fixture tests | BUILD_LOG entry | SG-01/02 ADRs | — |
| M2 | CI 1–2 | ING-094, 101, 103, 111 | calendar property tests | BUILD_LOG | ADR-003/004 | — |
| M3 | CI 1–3 (job 3 added+required) | DM-060..066 on real + fixtures | DM-064 reconciliation ≤ 0.01; DM-065 DST | dbt model YAML docs | SG-06/13 ADRs; schema contract committed | — |
| M4 | CI 1–3 | profile parquet feeds fct_consumer_load_hourly, DM tests still green | LP-040..042 incl. checksum ×2 | LIMITATIONS §1 draft | SG-03/04 ADRs; peak share in SSOT inputs (CALIBRATED) | — |
| M5 | CI 1–3 | marts unchanged (no drift) | AN-304 hard; AN-705 ×2; AN-704 prose | 12 artifacts + interpretation paragraphs | AN-703 VERIFIED-only rows | — |
| M6 | CI 1–4 (job 4 added+required) | ÖSPI coverage over window | **ST-602 a/b/c**; ST-601 golden; ST-603 determinism+no-lookahead | sensitivity table; captions ST-502 | GV-301/302 complete; GV-303 green; SG-07/08/09 ADRs; goldens human-approved | — |
| M7 | CI 1–4 | refresh dry-run gates green | RP-301 chart-reproducibility test | README §6 order; EXEC ≤2 pages; LIMITATIONS 1–7 final | GV-303 over README+EXEC; E-1 tags on headlines | **DL-1..10 all verified** |

## Stop conditions (halt the milestone, do not route around)

1. ING-082 out of range → guide §5.1 protocol; ADR before any gate change.
2. AN-304 fails → standardization/restart investigation; ADR to widen (last resort).
3. ST-602(a) fails → ÖSPI translation broken; debug calibration FIRST (SPEC-05 §9).
4. Any determinism check fails → fixing it outranks all feature work (A-4).
5. Token appears anywhere → stop everything; human rotates (A-7).
6. Milestone > 2× effort budget → blocker ADR before continuing (Charter §7).

## Gate lifecycle

Gates never weaken silently: constants live in specs/config, changes require
ADR (GV-203 "gate widening"). Gates strengthen freely (tightening needs no ADR
but does need a BUILD_LOG note). CI required-job set grows at M3 (job 3) and M6
(job 4) and never shrinks.
