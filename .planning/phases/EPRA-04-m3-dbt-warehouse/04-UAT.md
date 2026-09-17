---
status: complete
phase: EPRA-04-m3-dbt-warehouse
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - 04-04-SUMMARY.md
  - 04-05-SUMMARY.md
  - 04-06-SUMMARY.md
  - 04-07-SUMMARY.md
  - 04-08-SUMMARY.md
started: 2026-09-01T17:02:00Z
updated: 2026-09-01T17:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. CI fixture dbt build is green network-free (SC#3)
expected: bootstrap_fixture_warehouse.py --force then dbt build exits 0 without a real backfill or network.
result: pass
source: automated
coverage_id: D2

### 2. Mart schemas byte-match SPEC-02 §5 (SC#2)
expected: pytest tests/unit/test_marts_contract.py diffs information_schema against marts_contract.yml for all 6 marts.
result: pass
source: automated
coverage_id: D3

### 3. Real-data dbt build report committed (SC#1)
expected: reports/warehouse/dbt_build_<date>.md records a green real-data make warehouse (per-year counts, month coverage, 2022-08 delta, stand-in flags).
result: pass
source: automated
coverage_id: D4
note: This cloud checkout has no data/raw backfill; SC#1 is evidenced by the committed 2026-07-24 report (A-2).

### 4. dbt-check is a separate EN-080 job 3
expected: ci.yml has a dbt-check job (bootstrap --force, dbt build, D-07 pytest) not folded into test:.
result: pass
source: automated
coverage_id: D1

### 5. TP.02 mark dbt-check required on main
expected: GitHub branch protection requires the dbt-check status check for merge to main.
result: skipped
reason: "Deferred follow-up: TP.02 is operator GitHub settings (out of code scope). The job exists and is green on PR #2; making it required is not a code change."
coverage_id: D5

## Summary

total: 5
passed: 4
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps

[none yet]

## Deferred Follow-Ups

- test: 5
  idea: "Mark GitHub dbt-check a required status check on main (TP.02)"
  deferred_at: 2026-09-01
