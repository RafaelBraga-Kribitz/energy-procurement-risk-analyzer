---
phase: EPRA-07-m6-strategy-simulator
plan: 02
subsystem: strategies
tags: [calibration, anchors, st-201]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: align.AlignedVolumes
provides:
  - src/epra/strategies/calibration.py Anchors
affects: [EPRA-07-m6-strategy-simulator plans 03-10]

key-files:
  created:
    - tests/unit/test_strategies_calibration.py
  modified:
    - src/epra/strategies/calibration.py
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "p_ref_base is volume-weighted; ST-202 hour means are unweighted"
  - "IncompleteReferenceYearError for D-06 skip-if-incomplete"
  - "p_ref_peak < p_ref_base is AssertionError STOP"

requirements-completed: [ST-201, ST-202, ST-203, ST-204]

coverage:
  - id: D1
    description: "Synthetic 2019 p_ref_base=70 and p_ref_peak=80*(70/60)"
    requirement: "ST-201"
    verification:
      - kind: unit
        ref: "test_synthetic_2019_anchors_match_hand_calc"
        status: pass
    human_judgment: false
---

# Plan 07-02 Summary

2019 anchors are computable from injected frames. `compute_anchors` stub row removed. Tests: **4 passed** (+ align + remaining stubs).
