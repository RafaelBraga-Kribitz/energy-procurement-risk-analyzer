---
phase: EPRA-06-m5-analytics
plan: 04
subsystem: analytics
tags: [a4, ols, weather]

requires:
  - phase: EPRA-06-m5-analytics
    provides: epra.analytics._kit writers
provides:
  - src/epra/analytics/weather.py fit_load_hdd / OlsSummary / run
  - a4_load_vs_hdd.png a4_load_weather.md
affects: [EPRA-06-m5-analytics plans 07]

key-files:
  created:
    - tests/unit/test_analytics_a4.py
  modified:
    - src/epra/analytics/weather.py
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "Daily load is mean(load_at_mw) from hourly; HDD_18 is max of mart column (not from tavg)"
  - "OLS formula load_mw ~ hdd_18 + C(month_local), cov_type HC1"
  - "No A4 SSOT keys (not in D-03)"

requirements-completed: [AN-401, AN-402, AN-704]

coverage:
  - id: D1
    description: "synthetic HDD slope recovered positive; tavg ignored"
    requirement: "AN-401"
    verification:
      - kind: unit
        ref: "test_fit_load_hdd_recovers_positive_slope; test_hdd_column_used_as_given_not_recomputed_from_tavg"
        status: pass
    human_judgment: false
  - id: D2
    description: "invariance sentence and AN-704 on a4_load_weather.md"
    requirement: "AN-402"
    verification:
      - kind: unit
        ref: "test_invariance_sentence_in_prose; test_run_writes_artifacts_and_an704"
        status: pass
    human_judgment: false
---

# Plan 06-04 Summary

A4 `run(settings, hourly=...)` writes the load-vs-HDD scatter and month-FE HC1 markdown. Tests: **pytest tests/unit/test_analytics_a4.py tests/unit/test_analytics_a2.py tests/unit/test_stubs_fail_loudly.py -m "not live" --no-cov** → all passed (18).
