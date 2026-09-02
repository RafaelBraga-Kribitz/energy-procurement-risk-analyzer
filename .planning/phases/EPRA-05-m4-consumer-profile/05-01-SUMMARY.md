---
phase: EPRA-05-m4-consumer-profile
plan: 01
subsystem: consumer
tags: [pandas, numpy, spec-03, adr]

requires:
  - phase: EPRA-03-m2-auxiliary-data
    provides: epra.ingest.calendar.build_calendar (ING-110 columns)
  - phase: EPRA-01-m0-bootstrap
    provides: ConsumerProfileCfg + config/consumer_profile.yaml
provides:
  - src/epra/consumer/profile.py hourly_weights / day_type / special_factor (SPEC-03 §2 steps 1-4)
  - docs/ADR/ADR-012_maintenance-week-sg04.md
  - tests/unit/test_profile.py rule tests
affects: [EPRA-05-m4-consumer-profile plans 02-05]

key-files:
  created:
    - docs/ADR/ADR-012_maintenance-week-sg04.md
    - tests/unit/test_profile.py
  modified:
    - src/epra/consumer/profile.py
    - docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md

key-decisions:
  - "ADR-012: first Monday m ≥ 1 August, window [m, m+6]; 2022-08-01..07 when 1 Aug is Monday"
  - "Vectorized weights via np.select + (3,24) shape table; Christmas mask from month/day wrap; maintenance via Series.isin of seven dates per year"
  - "build_profile / monthly_volumes remain NotImplementedError until 05-02/05-03"

requirements-completed: [REQ-LP-01, LP-001, LP-002, SG-04]

coverage:
  - id: D1
    description: "ADR-012 records SG-04 first-Monday-on-or-after-1-August rule"
    requirement: "SG-04"
    verification:
      - kind: other
        ref: "docs/ADR/ADR-012_maintenance-week-sg04.md; 14_SPEC_GAPS.md SG-04 adopted (ADR-012)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Rule tests green: 2022 Aug 1-7 maintenance, holiday Monday weekend, Dec 25=Dec 26 weights"
    requirement: "LP-001"
    verification:
      - kind: unit
        ref: "uv run pytest tests/unit/test_profile.py tests/unit/test_stubs_fail_loudly.py -m 'not live' --no-cov: 24 passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "No YAML literals 0.18/0.60/1.06 in src/"
    requirement: "LP-002"
    verification:
      - kind: other
        ref: "rg -n '0\\.18|0\\.60|1\\.06' src/ → no matches"
        status: pass
    human_judgment: false
---

# Plan 05-01 Summary

Shipped T4.01 weight engine and ADR-012. `hourly_weights` is vectorized; stubs for `build_profile`/`monthly_volumes` still fail loudly.

**Self-check:** AC met (tests, grep, ADR). No deviations from SPEC-03 steps 1–4.
