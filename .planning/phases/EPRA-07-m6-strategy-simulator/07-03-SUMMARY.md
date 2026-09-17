---
phase: EPRA-07-m6-strategy-simulator
plan: 03
subsystem: strategies
tags: [s1, retrospective]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: align.AlignedVolumes
provides:
  - retrospective.cost_s1
affects: [EPRA-07-m6-strategy-simulator plans 04-06]

key-files:
  created:
    - tests/unit/test_strategies_retrospective.py
  modified:
    - src/epra/strategies/retrospective.py

key-decisions:
  - "cost_s1 does not drop NULLs; it rejects them"
  - "run()/main remain stubs until T6.05"

requirements-completed: [ST-101, ST-301]

coverage:
  - id: D1
    description: "1×10 + 2×20 = 50 EUR, volume 3"
    requirement: "ST-101"
    verification:
      - kind: unit
        ref: "test_cost_s1_hand_computed_month_to_the_cent"
        status: pass
    human_judgment: false
---

# Plan 07-03 Summary

S1 monthly spot cost is in. CLI still loud-fails. Tests: **2 passed** (plus stubs).
