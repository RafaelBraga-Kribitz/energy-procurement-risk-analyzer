# ADR-002: Dev-only typing-stub packages for mypy --strict
Date: 2026-07-19  |  Status: accepted

## Context
EN-002 mandates `mypy --strict` on `src/epra/` and allows `ignore_missing_imports`
only for entsoe/hmmlearn/arch. pandas and PyYAML (both in the pinned runtime
list) ship no inline type information, so strict mode cannot check code that
uses them without their community stub packages. SPEC-07 §3's dependency list
does not mention stubs; GV-203 makes any new dependency an ADR trigger.

## Decision
Add dev-only (never runtime) typing stubs to the `dev` extra: `pandas-stubs`,
`types-PyYAML`, `types-requests`. Additionally extend the sanctioned
`ignore_missing_imports` override to `statsmodels` (no stubs exist on PyPI as of
2026-07), keeping the EN-002 spirit: our own code is fully strict-checked.

## Consequences
- `uv run mypy` is meaningful and green; type errors in EPRA code fail CI.
- Stub packages track their upstreams loosely; a stub-only breakage is fixed by
  pinning the stub, never by loosening mypy strictness.

## Spec deviations
EN-002 (extended ignore_missing_imports to statsmodels; stub packages added as
dev dependencies beyond the SPEC-07 §3 list). Output contract preserved: strict
type checking of all first-party code.
