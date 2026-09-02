---
phase: EPRA-06-m5-analytics
plan: 01
subsystem: analytics
tags: [kit, matplotlib, duckdb]

requires:
  - phase: EPRA-04-m3-dbt-warehouse
    provides: marts.fct_price_hourly / fct_price_daily
provides:
  - src/epra/analytics/_kit.py loaders/writers
  - python -m epra.analytics CLI shell
affects: [EPRA-06-m5-analytics plans 02-07]

key-files:
  created:
    - src/epra/analytics/_kit.py
    - src/epra/analytics/__main__.py
    - tests/unit/test_analytics_kit.py
  modified: []

key-decisions:
  - "Empty mart SQL raises RuntimeError including the SQL text"
  - "stamp_rp702 then save_png; tests inspect Figure artists not pixels"
  - "CLI still calls stub run() after warehouse exists; missing file exits 1 first"

requirements-completed: [AN-703, RP-701, RP-702, D-01, D-03, D-04]

coverage:
  - id: D1
    description: "Empty SQL raises; nonempty hourly load returns rows"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "test_load_price_hourly_raises_on_empty; test_load_price_hourly_returns_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "RP-702 source note + VERIFIED tag + FIGSIZE"
    requirement: "RP-702"
    verification:
      - kind: unit
        ref: "test_stamp_rp702_sets_size_source_and_tag"
        status: pass
    human_judgment: false
  - id: D3
    description: "Missing warehouse CLI exit 1; 12 SPEC-04 filenames"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "test_cli_missing_warehouse_exits_1; test_artifact_names_match_spec04_section_6"
        status: pass
    human_judgment: false
---

# Plan 06-01 Summary

Shared kit and `python -m epra.analytics` shell are in. A1–A4 `run()` remain stubs until 06-02+. Kit tests: **9 passed**.
