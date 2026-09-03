---
phase: EPRA-07-m6-strategy-simulator
plan: 06
subsystem: strategies
tags: [st-303, sensitivities]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: retrospective.run cost engine
provides:
  - reports/strategies/sensitivity_matrix.md
affects: [EPRA-07-m6-strategy-simulator plans 07-10]

key-files:
  created:
    - src/epra/strategies/sensitivities.py
    - tests/unit/test_strategies_sensitivities.py
  modified:
    - src/epra/strategies/retrospective.py
    - src/epra/strategies/align.py
    - tests/unit/test_strategies_annual.py

key-decisions:
  - "Exactly three ## headings; FORBIDDEN_HEADING peak_available absent"
  - "flat_baseload goes through build_profile then align_hourly"
  - "run(sensitivities=False) keeps baseline tests from requiring a calendar"

requirements-completed: [ST-303, D-14]

coverage:
  - id: D1
    description: "three headings, ST-502, premium +10 EUR/MWh * volume, lock window moves S3, flat volumes differ"
    requirement: "ST-303"
    verification:
      - kind: unit
        ref: "tests/unit/test_strategies_sensitivities.py"
        status: pass
    human_judgment: false
---

# Plan 07-06 Summary

ST-303 three config-delta reruns are in. Tests: **4 passed** (plus 17 related retrospective/annual).
