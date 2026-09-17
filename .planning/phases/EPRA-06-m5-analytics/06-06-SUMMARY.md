---
phase: EPRA-06-m5-analytics
plan: 06
subsystem: analytics
tags: [a3, garch]

requires:
  - phase: EPRA-06-m5-analytics
    provides: regimes.daily_diff / fit_hmm / run HMM artifacts
provides:
  - fit_garch / a3_garch_vs_realized.png / garch_persistence SSOT
affects: [EPRA-06-m5-analytics plan 07]

key-files:
  created: []
  modified:
    - src/epra/analytics/regimes.py
    - tests/unit/test_analytics_a3.py

key-decisions:
  - "arch_model(..., rescale=False); divide d_t by 10 only if a warning message contains 'scale'"
  - "conditional_vol multiplied back by 10 after rescale so overlay matches original d_t units"
  - "persistence >= 1 documented as near-integrated; never clamped"

requirements-completed: [AN-303]

coverage:
  - id: D1
    description: "two-fit persistence identity; overlay+SSOT written"
    requirement: "AN-303"
    verification:
      - kind: unit
        ref: "test_garch_persistence_identity; test_run_writes_garch_overlay_and_ssot"
        status: pass
    human_judgment: false
  - id: D2
    description: "alpha+beta >= 1 reported not clamped"
    requirement: "AN-303"
    verification:
      - kind: unit
        ref: "test_near_integrated_persistence_is_not_clamped"
        status: pass
    human_judgment: false
---

# Plan 06-06 Summary

GARCH overlay and `garch_persistence` SSOT are in `regimes.run`. Tests: **pytest tests/unit/test_analytics_a3.py -m "not live" --no-cov** → all passed (12).
