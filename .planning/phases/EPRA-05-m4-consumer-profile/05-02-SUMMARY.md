---
phase: EPRA-05-m4-consumer-profile
plan: 02
subsystem: consumer
tags: [pandas, spec-03]

requires:
  - phase: EPRA-05-m4-consumer-profile plan 01
    provides: hourly_weights / day_type / special_factor
provides:
  - build_profile (ts_utc, load_mwh)
  - normalize_by_local_year (LP-004, LP-034)
affects: [EPRA-05-m4-consumer-profile plans 03-05]

key-files:
  modified:
    - src/epra/consumer/profile.py
    - tests/unit/test_profile.py
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "Incomplete local years use Σw from build_calendar(end=Y-12-31) filtered to year_local==Y (Pattern 2)"
  - "A year is complete iff row count and ts_utc membership match that full-year calendar"
  - "build_profile removed from stub tests; empty/duplicate calendars raise ValueError"

requirements-completed: [LP-004, LP-034]

coverage:
  - id: D1
    description: "Full local years 2019/2020/2023/2024 sum to annual_consumption_mwh ± 0.01"
    requirement: "LP-004"
    verification:
      - kind: unit
        ref: "test_full_local_year_sums_to_annual"
        status: pass
    human_judgment: false
  - id: D2
    description: "LP-034 2023 H1 monthly volumes match full-year months 1-6"
    requirement: "LP-034"
    verification:
      - kind: unit
        ref: "test_lp034_partial_h1_2023_matches_full_year_months"
        status: pass
    human_judgment: false
  - id: D3
    description: "DST 2024-03-31=23h, 2024-10-27=25h; empty/duplicate rejected"
    requirement: "LP-041"
    verification:
      - kind: unit
        ref: "uv run pytest tests/unit/test_profile.py tests/unit/test_stubs_fail_loudly.py --no-cov: 31 passed"
        status: pass
    human_judgment: false
---

# Plan 05-02 Summary

`build_profile` is real. Full years hit 50 GWh ± 0.01; a 6-month 2023 slice keeps the same monthly volumes as the full-year run.
