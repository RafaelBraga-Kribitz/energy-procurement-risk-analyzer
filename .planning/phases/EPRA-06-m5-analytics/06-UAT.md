---
status: complete
phase: EPRA-06-m5-analytics
source:
  - 06-01-SUMMARY.md
  - 06-02-SUMMARY.md
  - 06-03-SUMMARY.md
  - 06-04-SUMMARY.md
  - 06-05-SUMMARY.md
  - 06-06-SUMMARY.md
  - 06-07-SUMMARY.md
started: 2026-09-03T10:00:00Z
updated: 2026-09-03T10:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. SPEC-04 §6 artifacts regenerate (SC#1)
expected: after wiping the 12 known filenames, `python -m epra.analytics` writes all 12; four md files have ≥400 characters after the last table.
result: pass
source: automated
coverage_id: D1

### 2. AN-304 on real 2021–2023 (SC#2)
expected: ≥70% of 2021-09-01..2023-06-30 days in elevated+crisis and ≥60% of 2019 days calm on real marts.
result: skipped
reason: "Deferred follow-up: this checkout has no data/raw warehouse. Unit tests prove skip ≠ pass and fail-closed when coverage exists. Operator runs make warehouse && make analyze."
coverage_id: D2

### 3. SPEC-06 §7 tags and notes (SC#3)
expected: RP-701 figsize/dpi; RP-702 SOURCE_NOTE + VERIFIED; 2022 vermillion; A2 zero line; A4 invariance sentence.
result: pass
source: automated
coverage_id: D3

### 4. AN-705 SSOT identity
expected: two CLI runs on the same injected frames yield identical ssot_inputs_analytics.parquet values.
result: pass
source: automated
coverage_id: D4

### 5. make analyze does not invoke dbt
expected: Makefile analyze recipe is python -m epra.analytics.
result: pass
source: automated
coverage_id: D5

### 6. Full lint + suite
expected: make lint green; pytest -m "not live" ≥80% coverage.
result: pass
source: automated
notes: "330 passed, 2 skipped, coverage 93.21%"
coverage_id: D6

### 7. Fixture PNGs not committed (D-05)
expected: no reports/analytics PNG in git as Q2 evidence.
result: pass
source: automated
coverage_id: D7

### 8. TP.02 mark dbt-check required on main
expected: GitHub branch protection requires the dbt-check status check.
result: skipped
reason: "Deferred follow-up: TP.02 is operator GitHub settings (out of code scope since M3)."
coverage_id: D8
