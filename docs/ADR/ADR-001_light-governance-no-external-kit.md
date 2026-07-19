# ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored
Date: 2026-07-19  |  Status: accepted

## Context
A reusable governance framework exists (`RafaelBraga-Kribitz/governance-bootstrap`:
audit-finding registry, Steward/Remediator/Adversary roles, ~20 quality-gate
scripts, ratchet CI, subtree sync across consumer repos). The bootstrap decision
for this repo was delegated to the build agent: use it or not.

The Charter already answers this. §4.2 O-5 explicitly prohibits "heavy governance
machinery (audit-finding registry, session handouts, agent gate ceremony beyond
what SPEC-08 defines)" and caps governance weight at ~30% of the
decision-analytics-reconstruction repo. SPEC-08 §7 states verbatim that no
audit-finding registry, finding IDs, or governance CI beyond its §4 exists here —
"it is a feature, not an omission."

## Decision
Do not vendor the governance-bootstrap kit. Governance in this repo is exactly
the three SPEC-08 mechanisms: epistemic tags (GV-101/102), append-only ADRs
(GV-201..203), and the SSOT mechanism with its CI consistency check
(GV-301..303), plus the CI gates of SPEC-07 §8.

## Consequences
- Governance stays proportional to a portfolio analytics repo; reviewers who
  want to see the heavy machinery are pointed to the
  decision-analytics-reconstruction repo (SPEC-08 §7 sentence, to be quoted in
  the README).
- No subtree/sync workflows to maintain; no upstream coupling.
- If the Charter's governance stance ever changes, that is a Charter change and
  requires a superseding ADR (GV-203).

## Spec deviations
none
