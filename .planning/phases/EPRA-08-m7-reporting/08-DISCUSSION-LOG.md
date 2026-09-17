# Phase 8 Discussion Log

**Phase:** EPRA-08-m7-reporting
**Date:** 2026-09-03

## Locked (from Charter / SPEC-06 / AGENTS)

| Topic | Decision | Source |
|-------|----------|--------|
| `.pbix` | Human task; agent writes handoff README only | AGENTS §2.5 |
| EXEC_SUMMARY §5 | Human co-write; no invented euros | SPEC-06 §5, A-6 |
| Six export CSVs | SPEC-02 §7 names exact | DM-070 |
| Charts from exports | RP-301 pytest recomputes RP-201 bars | SPEC-06 §3 |
| No fixture euros in README | GV-303 + D-04/D-05 | SPEC-08, M6 verify |

## HOW decisions (08-CONTEXT D-01..D-10)

See `08-CONTEXT.md`. Summary: fail closed without warehouse/simulate/SSOT; never type result euros; skip empty refresh PRs; DL ticks must stay honest.

## Open for human

1. Co-write EXEC_SUMMARY §5 after real SSOT exists.
2. Build `.pbix` + four screenshots.
3. DL-1 rehearsal on a machine with token + backfill.
4. Mark `ssot-check` / `dbt-check` required (TP.02).
