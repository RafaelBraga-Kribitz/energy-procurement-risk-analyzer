---
phase: EPRA-05-m4-consumer-profile
plan: 05
subsystem: consumer
tags: [cli, makefile, m4-closeout]

requires:
  - phase: EPRA-05-m4-consumer-profile plan 04
    provides: build_profile / write_profile_outputs / LP-040 golden
provides:
  - python -m epra.consumer.profile CLI (EN-050)
  - Makefile profile: + all: profile then transform (D-08)
  - warehouse report stand-in = fct_procurement_cost_monthly only
  - docs/BUILD_LOG.md M4 entry
affects: [EPRA-05-m4-consumer-profile verify-work]

key-files:
  created: []
  modified:
    - src/epra/consumer/profile.py
    - Makefile
    - src/epra/warehouse/report.py
    - tests/unit/test_profile.py
    - tests/unit/test_warehouse_report.py
    - docs/BUILD_LOG.md

key-decisions:
  - "CLI reads ING-110 calendar.parquet via _dataset_root; missing file exit 1"
  - "make profile does not invoke dbt"
  - "LIMITATIONS.md §1 LP-051 confirmed unchanged; no M6 euros invented"

requirements-completed: [EN-050, LP-051, D-08]

coverage:
  - id: D1
    description: "CLI writes hourly parquet twice with identical bytes; missing calendar exits 1; --profile flat_baseload differs"
    requirement: "EN-050"
    verification:
      - kind: unit
        ref: "test_cli_writes_identical_hourly_parquet_twice; test_cli_missing_calendar_exits_1; test_cli_profile_flat_baseload_differs_from_default"
        status: pass
    human_judgment: false
  - id: D2
    description: "Makefile profile recipe + all: profile then transform"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "test_makefile_profile_before_transform"
        status: pass
    human_judgment: false
  - id: D3
    description: "Warehouse stand-in is procurement only; LP-051 LIMITATIONS §1 confirmed"
    requirement: "LP-051"
    verification:
      - kind: unit
        ref: "test_stand_in_marts_flagged_in_render; LIMITATIONS.md §1"
        status: pass
    human_judgment: false
---

# Plan 05-05 Summary

Operator interface is live: `make profile` → `python -m epra.consumer.profile`. `all:` runs profile before transform. Consumer mart is no longer flagged as a stand-in. BUILD_LOG M4 entry appended. Ready for `/gsd-verify-work` Phase 5.

**Self-check:** AC met. No dbt from `make profile`. No `data/` committed. No invented SSOT euros.
