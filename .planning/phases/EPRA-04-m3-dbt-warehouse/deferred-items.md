# Deferred Items — EPRA-04 M3 dbt Warehouse

Out-of-scope discoveries logged during plan execution (not fixed, per the
executor's scope-boundary rule: only auto-fix issues directly caused by the
current task's changes).

## 04-04

- **`dbt/models/staging/staging.yml` — `unique_combination_of_columns` top-level
  arguments deprecation.** dbt 1.12's `MissingArgumentsPropertyInGenericTestDeprecation`
  warns that `stg_gen_at_hourly`'s `unique_combination_of_columns` test in
  `staging.yml` (added in 04-02) passes `combination_of_columns` as a
  top-level test argument instead of nesting it under an `arguments:` key.
  Non-blocking (build still exits 0); `facts_price.yml` (this plan) uses the
  new nested-`arguments:` form for its own `accepted_range`/
  `unique_combination_of_columns` invocations. `staging.yml` is out of scope
  for 04-04 (owned by 04-02, already committed) — fix in a future
  housekeeping pass or the next time `staging.yml` is touched.

## 04-07

- **`scripts/bootstrap_fixture_warehouse.py` / `tests/unit/test_bootstrap_fixture_warehouse.py`
  — ruff format drift.** `make lint`'s `ruff format --check src tests scripts`
  reports both files "would be reformatted". Both files are owned by 04-05
  (already committed) and are not in this plan's `files_modified`
  (`src/epra/warehouse/__init__.py`, `src/epra/warehouse/report.py`,
  `tests/unit/test_warehouse_report.py`, `Makefile`) — out of scope per the
  executor's scope-boundary rule. `uv run ruff format --check
  src/epra/warehouse tests/unit/test_warehouse_report.py` (this plan's own
  files) reports "3 files already formatted", clean. Fix whenever
  `bootstrap_fixture_warehouse.py`/its test is next touched.
