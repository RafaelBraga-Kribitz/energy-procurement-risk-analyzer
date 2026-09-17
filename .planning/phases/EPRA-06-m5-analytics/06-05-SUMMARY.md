---
phase: EPRA-06-m5-analytics
plan: 05
subsystem: analytics
tags: [a3, hmm, an-304]

requires:
  - phase: EPRA-06-m5-analytics
    provides: epra.analytics._kit writers + load_price_daily
provides:
  - src/epra/analytics/regimes.py fit_hmm / check_an304 / december_regime / run
  - a3_realized_vol.png a3_regimes.png a3_regime_stats.md
affects: [EPRA-06-m5-analytics plans 06-07]

key-files:
  created:
    - tests/unit/test_analytics_a3.py
  modified:
    - src/epra/analytics/regimes.py
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "d_t diffs on a calendar reindex so a NULL day does not span into the next priced day"
  - "AN-304 complete = 90% of calendar days labeled in 2019 and in 2021-09-01..2023-06-30; skip otherwise"
  - "run() raises RuntimeError on AN-304 fail; logs skip; does not write GARCH yet"
  - "december_regime ties break toward calm"

requirements-completed: [AN-301, AN-302, AN-304, AN-705]

coverage:
  - id: D1
    description: "arithmetic d_t; HMM two-fit identity; labels by std"
    requirement: "AN-302"
    verification:
      - kind: unit
        ref: "test_daily_diff_is_arithmetic_not_log; test_fit_hmm_deterministic_and_labels_by_std"
        status: pass
    human_judgment: false
  - id: D2
    description: "AN-304 skip vs fail-closed vs pass; december majority"
    requirement: "AN-304"
    verification:
      - kind: unit
        ref: "test_check_an304_skip_without_2019; test_check_an304_fail_closed_when_coverage_exists; test_december_regime_majority_and_calm_tiebreak"
        status: pass
    human_judgment: false
---

# Plan 06-05 Summary

A3 HMM `run(settings, daily=...)` writes realized-vol and regime artifacts. AN-304 skip is not a pass. Tests: **pytest tests/unit/test_analytics_a3.py tests/unit/test_stubs_fail_loudly.py -m "not live" --no-cov** → all passed (15).
