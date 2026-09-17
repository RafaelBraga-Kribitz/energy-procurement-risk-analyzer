---
phase: EPRA-07-m6-strategy-simulator
plan: 09
subsystem: report
tags: [ssot, gv-303, ci]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: epra.report.ssot assemble ADR-016
provides:
  - epra.report.ssot_check CI ssot-check job
affects: [EPRA-07-m6-strategy-simulator plan 10]

key-files:
  created:
    - src/epra/report/ssot_check.py
    - scripts/ssot_whitelist.txt
    - tests/unit/test_ssot_check.py
  modified:
    - scripts/check_ssot_consistency.py
    - .github/workflows/ci.yml

key-decisions:
  - "Decimal ROUND_HALF_UP; 1.25 → 1.3 at 1 decimal (banker 1.2 fails)"
  - "Missing NUMERIC_SSOT.md skips GV-302; still scan docs"
  - "CI job ssot-check added; GitHub required-check is operator"

requirements-completed: [GV-303, EN-080, ADR-016]

coverage:
  - id: D1
    description: "half-up vs banker, whitelist 2022, mutation, missing SSOT exit 0, ci job"
    requirement: "GV-303"
    verification:
      - kind: unit
        ref: "tests/unit/test_ssot_check.py"
        status: pass
    human_judgment: false
---

# Plan 07-09 Summary

GV-303 checker + EN-080 job 4 are in. Tests: **11 passed**.
