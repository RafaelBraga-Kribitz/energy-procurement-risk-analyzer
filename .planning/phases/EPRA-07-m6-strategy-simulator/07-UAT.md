---
status: complete
phase: EPRA-07-m6-strategy-simulator
source:
  - 07-01-SUMMARY.md
  - 07-02-SUMMARY.md
  - 07-03-SUMMARY.md
  - 07-04-SUMMARY.md
  - 07-05-SUMMARY.md
  - 07-06-SUMMARY.md
  - 07-07-SUMMARY.md
  - 07-08-SUMMARY.md
  - 07-09-SUMMARY.md
  - 07-10-SUMMARY.md
started: 2026-09-03T19:15:00Z
updated: 2026-09-03T19:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. ST-601 synthetic golden (SC#1 partial)
expected: `tests/test_golden_strategies.py` recomputes `annual_summary` and matches `tests/golden/strategy_annual_summary.json`; disclaimer is not market evidence.
result: pass
source: automated
coverage_id: D1

### 2. ST-602(a) on real 2019+2022 (SC#1 remainder)
expected: cost(S1, 2022) > cost(S3, 2022) on real marts; skip if 2019 incomplete.
result: skipped
reason: "Deferred follow-up: this checkout has no data/raw warehouse. Unit tests prove skip ≠ pass and fail-closed when 2022 S1/S3 exist. Operator runs make warehouse && make simulate. If (a) fails, debug calibration."
coverage_id: D2

### 3. Two seeded runs identical (SC#2)
expected: two simulate/assemble calls on unchanged injected inputs yield identical numeric summaries / markdown.
result: pass
source: automated
coverage_id: D3

### 4. Committed NUMERIC_SSOT 5-year matrix (SC#3)
expected: `reports/NUMERIC_SSOT.md` in git with GV-302 keys and epistemic tags from a real make ssot.
result: skipped
reason: "D-04: do not commit fixture-warehouse euros. Assembler unit tests cover the table shape on tmp_settings."
coverage_id: D4

### 5. make simulate / ssot do not invoke dbt
expected: Makefile recipes are the Python CLIs.
result: pass
source: automated
coverage_id: D5

### 6. Full lint + suite
expected: make lint green; pytest -m "not live" ≥80% coverage.
result: pass
source: automated
notes: "392 passed, 2 skipped, coverage 92.55%"
coverage_id: D6

### 7. GV-303 current README with missing SSOT
expected: checker exit 0 (no result euros yet; whitelist years).
result: pass
source: automated
coverage_id: D7

### 8. M6 stubs gone
expected: test_stubs_fail_loudly only M7 charts.
result: pass
source: automated
coverage_id: D8
