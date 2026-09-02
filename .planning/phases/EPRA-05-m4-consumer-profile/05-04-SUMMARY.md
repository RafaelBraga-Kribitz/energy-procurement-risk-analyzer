---
phase: EPRA-05-m4-consumer-profile
plan: 04
subsystem: consumer
tags: [golden, spec-03]

requires:
  - phase: EPRA-05-m4-consumer-profile plan 03
    provides: build_profile / monthly_volumes
provides:
  - tests/golden/consumer_load_2023.sha256 (LP-040 payload SHA-256)
  - LP-030 flat_baseload via profile_name
  - LP-040..042 tests
affects: [EPRA-05-m4-consumer-profile plan 05]

key-files:
  created:
    - tests/golden/consumer_load_2023.sha256
  modified:
    - src/epra/consumer/profile.py
    - tests/unit/test_profile.py

key-decisions:
  - "Checksum is SHA-256 of sorted 2023 load_mwh float64 bytes (not parquet file bytes)"
  - "flat_baseload is cfg.model_copy(profile_name=...) — no second YAML"
  - "EN-072: regenerating the golden needs human approval"

requirements-completed: [LP-030, LP-040, LP-041, LP-042]

coverage:
  - id: D1
    description: "LP-040 2023 sum, ratio band, Aug<Jul, Dec25=Dec26, golden digest"
    requirement: "LP-040"
    verification:
      - kind: unit
        ref: "test_lp040_2023_golden_ratio_aug_lt_jul_dec25_eq_dec26"
        status: pass
    human_judgment: false
  - id: D2
    description: "LP-041 properties + LP-042 50001 breaks checksum; two in-process checksums identical"
    requirement: "LP-042"
    verification:
      - kind: unit
        ref: "test_lp041_properties_and_lp042_checksum_sensitivity"
        status: pass
    human_judgment: false
  - id: D3
    description: "flat_baseload pre-norm weights are 1.0; annual still 50 GWh"
    requirement: "LP-030"
    verification:
      - kind: unit
        ref: "test_flat_baseload_unit_weights_then_same_annual"
        status: pass
    human_judgment: false
---

# Plan 05-04 Summary

Golden `consumer_load_2023.sha256` is committed. LP-040..042 and LP-030 pass. Do not regenerate the digest without human approval (EN-072).
