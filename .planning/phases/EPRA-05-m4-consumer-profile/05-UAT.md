---
status: complete
phase: EPRA-05-m4-consumer-profile
source:
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
  - 05-04-SUMMARY.md
  - 05-05-SUMMARY.md
started: 2026-09-02T14:20:00Z
updated: 2026-09-02T14:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. LP-040..042 green with committed checksum (SC#1)
expected: golden digest matches tests/golden/consumer_load_2023.sha256; LP-041 properties; LP-042 50001 breaks digest; LP-040 is bit-stable across two runs.
result: pass
source: automated
coverage_id: D1

### 2. Full local years sum to 50,000.00 ± 0.01 (SC#2)
expected: 2019/2020/2023/2024 (incl. DST) normalize to annual_consumption_mwh ± 0.01; LP-034 partial H1 matches full-year months.
result: pass
source: automated
coverage_id: D2

### 3. consumer_peak_share ready for SSOT (SC#3)
expected: ssot_inputs_profile.parquet one CALIBRATED 2019 row; yearly deviation < 1 pp (ADR-013).
result: pass
source: automated
coverage_id: D3

### 4. Isolated dbt-check still green after D-08 single-file path
expected: bootstrap --force --data-root (isolated) then dbt build PASS=64; committed oespi_monthly.csv untouched.
result: pass
source: automated
coverage_id: D4

### 5. make profile CLI + all: order + LP-051
expected: make profile is python -m epra.consumer.profile; all: starts with profile then transform; LIMITATIONS §1 unchanged.
result: pass
source: automated
coverage_id: D5

### 6. EN-072 golden regeneration
expected: Human approves any rewrite of tests/golden/consumer_load_2023.sha256.
result: skipped
reason: "Deferred follow-up: golden is committed and stable. Regeneration is human-only per AGENTS.md."
coverage_id: D6

### 7. TP.02 mark dbt-check required on main
expected: GitHub branch protection requires the dbt-check status check.
result: skipped
reason: "Deferred follow-up: TP.02 is operator GitHub settings (out of code scope since M3)."
coverage_id: D7

## Summary

total: 7
passed: 5
issues: 0
pending: 0
skipped: 2
blocked: 0

## Gaps

[none yet]

## Deferred Follow-Ups

- test: 6
  idea: "EN-072: human approval before regenerating consumer_load_2023.sha256"
  deferred_at: 2026-09-02
- test: 7
  idea: "Mark GitHub dbt-check a required status check on main (TP.02)"
  deferred_at: 2026-09-01
