# Doc Ingest Synthesis Summary

**Mode:** new  
**Date:** 2026-07-21  
**Precedence:** ADR > SPEC > PRD > DOC

## Doc counts by type

| Type | Count | Sources |
|------|-------|---------|
| ADR | 2 | ADR-001, ADR-002 |
| SPEC | 8 | SPEC-01..08 |
| PRD | 0 | — |
| DOC | 1 | 14_SPEC_GAPS.md |
| **Total** | **11** | |

## Decisions (locked)

- **2 locked ADRs** — `docs/ADR/ADR-001_light-governance-no-external-kit.md`, `docs/ADR/ADR-002_typing-stub-dev-dependencies.md`
- See `.planning/intel/decisions.md`

## Requirements

- **0 PRD requirements** extracted (requirements live in SPEC REQ IDs and Charter)
- See `.planning/intel/requirements.md`

## Constraints

- **24 constraint entries** from SPEC-01..08
- Type breakdown: schema (8), protocol (9), nfr (7)
- See `.planning/intel/constraints.md`

## Context topics

- **1 DOC source** — specification gaps tracker with 18 SG entries (15 proposed, 2 resolved, 1 process note)
- Authority hierarchy: Charter + SPEC-01..08 > EXECUTION_BLUEPRINT > 14_SPEC_GAPS proposals
- See `.planning/intel/context.md`

## Cross-ref cycle detection

- Cycles detected among SPEC-01..08 mutual cross-refs (expected intra-suite references)
- Logged as INFO; not treated as synthesis blockers

## Conflicts

| Bucket | Count |
|--------|-------|
| BLOCKERS | 0 |
| WARNINGS | 11 |
| INFO | 6 |

Detail: `.planning/INGEST-CONFLICTS.md`

## Intel files

| File | Purpose |
|------|---------|
| `decisions.md` | Locked ADR decisions |
| `requirements.md` | PRD requirements (none in ingest) |
| `constraints.md` | SPEC technical constraints |
| `context.md` | DOC gaps tracker + authority notes |
| `SYNTHESIS.md` | This entry point |

## Status

**AWAITING USER** — 11 competing gap proposals (WARNINGS) need ADR adoption or explicit approval before routing implementations that diverge from explicit SPEC text. No hard blockers.
