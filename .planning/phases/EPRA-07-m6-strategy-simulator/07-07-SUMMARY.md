---
phase: EPRA-07-m6-strategy-simulator
plan: 07
subsystem: strategies
tags: [forward, st-406, adr-014, adr-015]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: S1-S4 cost functions, Anchors
  - phase: EPRA-06-m5-analytics
    provides: december_regime
provides:
  - CostCells simulate summarize ADR-014 ADR-015
affects: [EPRA-07-m6-strategy-simulator plans 08-10]

key-files:
  created:
    - docs/ADR/ADR-014_st401-day-mapping-sg07.md
    - docs/ADR/ADR-015_quantile-cvar-sg08.md
    - tests/unit/test_strategies_forward.py
  modified:
    - src/epra/strategies/forward_risk.py
    - src/epra/strategies/annual.py
    - tests/unit/test_stubs_fail_loudly.py
    - docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md

key-decisions:
  - "ADR-014: (day-of-month, hour_local); overflow last same is_weekend; DST forward-fill"
  - "ADR-015: quantile linear; CVaR ceil(0.05 N) highest"
  - "One default_rng; path-major month-minor; T-6 joint pool_year"
  - "Observed S3 lock on cells; drawn lock assembled in p_s3_forward"

requirements-completed: [ST-401, ST-402, ST-403, ST-404, ST-405, ST-406, ST-602, ADR-014, ADR-015]

coverage:
  - id: D1
    description: "mapping, cell S1 toy, determinism, ADR-015 CVaR=19, ST-602(c), drawn lock, no-crisis, CLI"
    requirement: "ST-406"
    verification:
      - kind: unit
        ref: "tests/unit/test_strategies_forward.py"
        status: pass
    human_judgment: false
---

# Plan 07-07 Summary

Forward ST-406 cells + seeded bootstrap + ADR-014/015 are in. Tests: **11 passed** (10 forward + stubs).
