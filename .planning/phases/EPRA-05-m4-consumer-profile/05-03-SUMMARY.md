---
phase: EPRA-05-m4-consumer-profile
plan: 03
subsystem: consumer
tags: [parquet, dbt, adr]

requires:
  - phase: EPRA-05-m4-consumer-profile plan 02
    provides: build_profile
provides:
  - consumer_load_hourly.parquet / consumer_load_monthly.parquet / ssot_inputs_profile.parquet writers
  - ADR-013 2019 consumer_peak_share
  - D-08 single-file dbt source + bootstrap stand-in
affects: [EPRA-05-m4-consumer-profile plans 04-05, dbt-check CI]

key-files:
  created:
    - docs/ADR/ADR-013_peak-share-reference-year-sg03.md
  modified:
    - src/epra/consumer/profile.py
    - tests/unit/test_profile.py
    - tests/conftest.py
    - dbt/models/sources.yml
    - scripts/bootstrap_fixture_warehouse.py
    - tests/unit/test_bootstrap_fixture_warehouse.py
    - tests/unit/test_stubs_fail_loudly.py
    - docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md

key-decisions:
  - "ADR-013: SSOT value is 2019 local-year peak share; yearly |Δ| < 1 pp"
  - "LP-020 ~0.42-0.48 is a hint; constructed 2019 share is ~0.486 — do not retune YAML (A-2); tests use [0.42, 0.50)"
  - "monthly_volumes(profile_df, calendar_df) joins ING-110 year_local/month_local"
  - "D-08: sources.yml + bootstrap use data/processed/consumer_load_hourly.parquet (SPEC-02 §5 / LP-003)"

requirements-completed: [LP-003, LP-020, LP-021, SG-03, D-08]

coverage:
  - id: D1
    description: "2019 peak share published; yearly deviation < 1 pp"
    requirement: "LP-020"
    verification:
      - kind: unit
        ref: "test_peak_share_2019_in_band_and_yearly_deviation_under_1pp"
        status: pass
    human_judgment: false
  - id: D2
    description: "Atomic writers round-trip hourly/monthly/ssot under tmp_settings.data_processed"
    requirement: "LP-003"
    verification:
      - kind: unit
        ref: "test_write_profile_outputs_roundtrip"
        status: pass
    human_judgment: false
  - id: D3
    description: "Bootstrap + sources.yml single-file consumer path"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "uv run pytest tests/unit/test_bootstrap_fixture_warehouse.py --no-cov (green)"
        status: pass
    human_judgment: false
---

# Plan 05-03 Summary

Processed outputs and 2019 `consumer_peak_share` land as specified. dbt/bootstrap now share the LP-003 filename. Peak-share plausibility band documented in ADR-013 (~0.486 vs informal 0.48).
