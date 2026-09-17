---
phase: EPRA-06-m5-analytics
plan: 03
subsystem: analytics
tags: [a2, spread, matplotlib]

requires:
  - phase: EPRA-06-m5-analytics
    provides: epra.analytics._kit upsert SSOT + frame_to_markdown
provides:
  - src/epra/analytics/spread.py spread_stats / run
  - a2_spread_monthly.png a2_spread_summary.md
  - SSOT keys spread_mean_<year>
affects: [EPRA-06-m5-analytics plans 07]

key-files:
  created:
    - tests/unit/test_analytics_a2.py
  modified:
    - src/epra/analytics/spread.py
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "spread_stats takes one hourly mart frame (not separate at/delu/calendar args)"
  - "Spread recomputed as AT minus DE-LU after dropna both sides"
  - "Zero line labeled 'zero' for artist tests"

requirements-completed: [AN-201, AN-202, AN-203, AN-704]

coverage:
  - id: D1
    description: "spread_stats hand-calc; NULL either side dropped"
    requirement: "AN-202"
    verification:
      - kind: unit
        ref: "test_spread_stats_matches_hand_calc; test_null_on_either_side_dropped_not_zero"
        status: pass
    human_judgment: false
  - id: D2
    description: "monthly chart axhline(0); AN-704 Germany localization prose"
    requirement: "AN-201"
    verification:
      - kind: unit
        ref: "test_monthly_chart_has_zero_line; test_run_writes_artifacts_ssot_and_an704"
        status: pass
    human_judgment: false
---

# Plan 06-03 Summary

A2 `run(settings, hourly=...)` writes the monthly zero-line chart and spread summary. Tests: **pytest tests/unit/test_analytics_a2.py tests/unit/test_analytics_a1.py tests/unit/test_stubs_fail_loudly.py -m "not live" --no-cov** → all passed (25).
