---
phase: EPRA-07-m6-strategy-simulator
plan: 01
subsystem: strategies
tags: [align, st-101, duckdb]

requires:
  - phase: EPRA-05-m4-consumer-profile
    provides: ssot_inputs_profile.parquet consumer_peak_share
  - phase: EPRA-04-m3-dbt-warehouse
    provides: marts.fct_price_hourly / fct_consumer_load_hourly
provides:
  - src/epra/strategies/align.py AlignedVolumes
affects: [EPRA-07-m6-strategy-simulator plans 02-10]

key-files:
  created:
    - src/epra/strategies/align.py
    - tests/unit/test_strategies_align.py
  modified: []

key-decisions:
  - "NULL price hours dropped once after inner join on ts_utc"
  - "w_peak from profile parquet or FileNotFoundError/KeyError naming the path"
  - "Empty mart SQL raises RuntimeError including the SQL text"

requirements-completed: [ST-101, ST-501, D-01, D-02]

coverage:
  - id: D1
    description: "3 NULL hours → volume 3.0 identical across six strategy ids"
    requirement: "ST-101"
    verification:
      - kind: unit
        ref: "test_three_null_hours_drop_from_shared_monthly_volume"
        status: pass
    human_judgment: false
  - id: D2
    description: "w_peak loader reads parquet; missing file/key raises"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "test_load_w_peak_reads_profile_parquet; test_load_w_peak_missing_file_names_path"
        status: pass
    human_judgment: false
---

# Plan 07-01 Summary

Shared ST-101 aligner is in. Cost engines still stubs. Align tests: **6 passed**.
