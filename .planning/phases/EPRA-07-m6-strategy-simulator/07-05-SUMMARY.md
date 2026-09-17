---
phase: EPRA-07-m6-strategy-simulator
plan: 05
subsystem: strategies
tags: [annual, st-304, parquet, st-602]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: cost_s1..cost_s4
provides:
  - annual_summary dual-write charts retrospective.run
affects: [EPRA-07-m6-strategy-simulator plans 06-10]

key-files:
  created:
    - src/epra/strategies/annual.py
    - tests/unit/test_strategies_annual.py
  modified:
    - src/epra/strategies/retrospective.py
    - src/epra/warehouse/report.py
    - tests/unit/test_warehouse_report.py
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "ST-602(a)/(b) skip if incomplete, RuntimeError if fail (not widen)"
  - "dual-write wipes procurement_cost_monthly glob then writes int64 year/month"
  - "ssot_inputs_strategies.parquet includes wrong_strategy_cost_* and ST-204 anchors"
  - "warehouse _STAND_IN_MARTS empty; procurement is M6 dual-write"

requirements-completed: [ST-001, ST-204, ST-301, ST-302, ST-304, ST-602]

coverage:
  - id: D1
    description: "rank/delta, ST-602 skip-fail-pass, dual-write wipe, charts+SSOT, CLI exit 1"
    requirement: "ST-301"
    verification:
      - kind: unit
        ref: "tests/unit/test_strategies_annual.py"
        status: pass
    human_judgment: false
---

# Plan 07-05 Summary

Annual summary, ST-304 charts (STRATEGY_COLORS, ST-502/LP-050, CALIBRATED), dual-write parquet, and un-stubbed `retrospective.run`/`main` are in. ST-602(a) skip-if-incomplete; fail-closed when 2022 S1/S3 exist. Tests: **28 passed** (annual + retrospective + warehouse + stubs).
