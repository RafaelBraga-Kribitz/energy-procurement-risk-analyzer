---
phase: EPRA-07-m6-strategy-simulator
plan: 04
subsystem: strategies
tags: [s2, s3, s4, st-503]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: cost_s1, Anchors
provides:
  - p_s2 p_s3 cost_s2 cost_s3 cost_s4 ST502_SENTENCE
affects: [EPRA-07-m6-strategy-simulator plans 05-07]

key-files:
  created: []
  modified:
    - src/epra/strategies/retrospective.py
    - tests/unit/test_strategies_retrospective.py

key-decisions:
  - "p_s3 takes w_peak keyword-only (not on StrategyCfg)"
  - "ST-503 is a poisoned 2021-06 ÖSPI row that must not move p_s3(2022)"
  - "ASCII hyphen in ST-502 caption (RUF001); ÖSPI umlaut kept (spec)"

requirements-completed: [ST-102, ST-103, ST-104, ST-105, ST-106, ST-107, ST-502, ST-503]

coverage:
  - id: D1
    description: "ÖSPI=ref identity; no-lookahead; hybrid between legs"
    requirement: "ST-503"
    verification:
      - kind: unit
        ref: "test_st503_p_s3_2022_ignores_2021_june; test_st602b_hybrid_between_legs"
        status: pass
    human_judgment: false
---

# Plan 07-04 Summary

S2/S3/S4 formulas are in; T-5 identities hold; ST-503 green. `run()` still stubbed. Retrospective tests: **10 passed**.
