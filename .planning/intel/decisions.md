# Synthesized Decisions (ADRs)

## ADR-001: Light governance per SPEC-08; governance-bootstrap kit NOT vendored
- source: docs/ADR/ADR-001_light-governance-no-external-kit.md
- status: locked
- decision: Do not vendor the governance-bootstrap kit. Governance in this repo is exactly the three SPEC-08 mechanisms: epistemic tags (GV-101/102), append-only ADRs (GV-201..203), and the SSOT mechanism with its CI consistency check (GV-301..303), plus the CI gates of SPEC-07 §8.
- scope: governance-bootstrap kit, SPEC-08, epistemic tags, ADRs, SSOT, CI gates, SPEC-07

## ADR-002: Dev-only typing-stub packages for mypy --strict
- source: docs/ADR/ADR-002_typing-stub-dev-dependencies.md
- status: locked
- decision: Add dev-only (never runtime) typing stubs to the `dev` extra: `pandas-stubs`, `types-PyYAML`, `types-requests`. Additionally extend the sanctioned `ignore_missing_imports` override to `statsmodels` (no stubs exist on PyPI as of 2026-07), keeping the EN-002 spirit: our own code is fully strict-checked.
- scope: mypy, typing stubs, pandas-stubs, types-PyYAML, types-requests, statsmodels, dev dependencies, EN-002, SPEC-07
