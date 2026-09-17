---
phase: EPRA-07-m6-strategy-simulator
plan: 08
subsystem: report
tags: [ssot, gv-301, adr-016]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: ssot_inputs_strategies.parquet
provides:
  - epra.report.ssot assemble ADR-016
affects: [EPRA-07-m6-strategy-simulator plans 09-10]

key-files:
  created:
    - src/epra/report/ssot.py
    - docs/ADR/ADR-016_ssot-updated-at-rounding-sg09.md
    - tests/unit/test_ssot.py
  modified:
    - scripts/generate_ssot.py
    - src/epra/strategies/retrospective.py
    - tests/unit/test_strategies_annual.py
    - docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md

key-decisions:
  - "updated_at = max input mtime ISO-8601 UTC Z second precision; no datetime.now"
  - "GV-302 completeness is year-adaptive; missing years omitted not zero-filled"
  - "cost_<strategy>_<year> emitted by retrospective producer"
  - "Do not commit synthetic NUMERIC_SSOT.md (D-04)"

requirements-completed: [GV-301, GV-302, ST-204, ADR-016]

coverage:
  - id: D1
    description: "byte-identical assemble, duplicate raise, glob load, GV-302 complete/incomplete, tag copy"
    requirement: "GV-301"
    verification:
      - kind: unit
        ref: "tests/unit/test_ssot.py"
        status: pass
    human_judgment: false
---

# Plan 07-08 Summary

SSOT assembler + ADR-016 are in. Tests: **8 passed** (`tests/unit/test_ssot.py`) plus annual SSOT key asserts.
