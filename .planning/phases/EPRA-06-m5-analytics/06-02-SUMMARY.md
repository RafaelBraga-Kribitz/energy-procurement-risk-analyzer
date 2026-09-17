---
phase: EPRA-06-m5-analytics
plan: 02
subsystem: analytics
tags: [a1, matplotlib, ssot]

requires:
  - phase: EPRA-06-m5-analytics
    provides: epra.analytics._kit loaders/writers
provides:
  - src/epra/analytics/descriptive.py annual_summary / run
  - A1 artifacts a1_annual_summary.md+csv, heatmap, duration, negative hours
  - SSOT keys annual_mean_price_<year> and neg_hours_<year>
affects: [EPRA-06-m5-analytics plans 03-07]

key-files:
  created:
    - tests/unit/test_analytics_a1.py
  modified:
    - src/epra/analytics/descriptive.py
    - src/epra/analytics/_kit.py
    - tests/unit/test_analytics_kit.py
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "NULL price_at_eur_mwh dropped; never treated as 0 (logged in md)"
  - "Heatmap complete year = 12 distinct month_local with at least one priced hour; else empty panel"
  - "write_ssot_rows upserts by key (keep last) so A2+ cannot wipe A1"
  - "Duration 2022 = Okabe-Ito vermillion; yscale linear; x 0-100% of hours"
  - "AN-105 numbers interpolated via format_eur_mwh / format_pct; 2022 missing window quotes no invented EUR"

requirements-completed: [AN-101, AN-102, AN-103, AN-104, AN-105, AN-704]

coverage:
  - id: D1
    description: "annual_summary hand-calc; NULL hours dropped not zeroed"
    requirement: "AN-101"
    verification:
      - kind: unit
        ref: "test_annual_summary_matches_hand_calc_and_drops_null; test_null_price_is_not_treated_as_zero"
        status: pass
    human_judgment: false
  - id: D2
    description: "five heatmap panels; incomplete years empty; shared clim"
    requirement: "AN-102"
    verification:
      - kind: unit
        ref: "test_heatmap_five_panels_empty_incomplete_shared_clim"
        status: pass
    human_judgment: false
  - id: D3
    description: "2022 vermillion duration curve; linear y; AN-704 prose"
    requirement: "AN-103"
    verification:
      - kind: unit
        ref: "test_duration_curves_2022_vermillion_linear_not_log; test_run_writes_artifacts_ssot_and_an704"
        status: pass
    human_judgment: false
---

# Plan 06-02 Summary

A1 descriptive `run(settings, hourly=...)` writes the four SPEC-04 A1 artifacts plus CSV. Kit SSOT writer now upserts. Tests: **pytest tests/unit/test_analytics_a1.py tests/unit/test_analytics_kit.py tests/unit/test_stubs_fail_loudly.py -m "not live" --no-cov** → all passed (30).
