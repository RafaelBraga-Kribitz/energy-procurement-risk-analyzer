# Deferred Items — Phase EPRA-03 (m2-auxiliary-data)

Out-of-scope discoveries logged during plan execution (not fixed — scope
boundary rule: only auto-fix issues caused by the current task's changes).

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Formatting | `uv run ruff format --check src tests scripts` reports `tests/unit/test_io.py` would be reformatted. Pre-existing — file last touched by plan 03-01 (commit `58c69ca`), not modified by 03-02. | Open | 03-02 |
| Human checkpoint (D-03/D-06) | Real ÖSPI double-entry reconciliation pending. `data/manual/oespi_monthly_entry1.csv` and `oespi_monthly_entry2.csv` exist locally (human-transcribed) but are NOT yet reconciled — `data/manual/oespi_monthly.csv` is absent. ING-103 currently SOFT-PASSES informationally ("ING-101 double-entry human checkpoint pending (D-06), not a gate failure") per `reports/ingestion/validation_2026-07-23.md`. Resolve via `uv run python scripts/oespi_reconcile.py`, then delete the two entry files, then re-run `make validate-ingest` to confirm ING-103 real-data PASS. Documented in LIMITATIONS.md §6. **RESOLVED 2026-07-23**: human double-entry completed (entry1==entry2), `scripts/oespi_reconcile.py` exit 0 wrote `data/manual/oespi_monthly.csv` (92 months); `make validate-ingest` exit 0 with ING-103 substantive real-data PASS. | Resolved (2026-07-23) | 03-06 |
