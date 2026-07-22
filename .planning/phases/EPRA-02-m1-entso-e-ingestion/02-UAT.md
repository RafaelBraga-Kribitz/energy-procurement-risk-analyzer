---
status: passed
phase: 02-m1-entso-e-ingestion
source: [02-VERIFICATION.md]
started: 2026-07-22
updated: 2026-07-22
---

> RESOLVED 2026-07-22: both items were run against the real ENTSO-E API (token in
> `.env`) — not deferred. Doing so surfaced and fixed two data-loss bugs (100-doc
> pagination, chunk-boundary month overwrite) and one gate-domain bug (ADR-006).
> `make backfill` fills all four `data/raw/entsoe_*` trees (2019→2024-01, the real
> data horizon) and `make validate-ingest` exits 0 — ALL GATES PASSED.

## Current Test

number: 1
name: Live ENTSO-E backfill produces raw parquet under data/raw/
expected: |
  After `make backfill` with a valid ENTSOE_API_TOKEN in .env, data/raw/entsoe_prices_at/,
  entsoe_prices_delu/, entsoe_load_at/, and entsoe_gen_at/ each contain YYYY/*.parquet files
  spanning 2019-01 through the latest complete month.
awaiting: user response

## Tests

### 1. Live backfill produces four dataset trees under data/raw/
expected: `make backfill` (with a real ENTSOE_API_TOKEN in .env) writes YYYY/*.parquet under data/raw/entsoe_prices_at, entsoe_prices_delu, entsoe_load_at, entsoe_gen_at for 2019-01 → latest complete month.
result: [pending]

### 2. make validate-ingest reports ING-080..085 PASS on real data
expected: after a successful backfill, `make validate-ingest` writes reports/ingestion/validation_YYYY-MM-DD.md with ING-080 through ING-085 all PASS and exits 0.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

None — automated scope is fully verified (177 tests green, ING-070 contract tests, DST fixtures, lint/mypy clean; code review clean after 5/5 fixes). The two pending items are the deliberately-deferred live-data checkpoint from plan 02-07 Task 2, which requires the operator's own `ENTSOE_API_TOKEN` and network access to transparency.entsoe.eu.

**How to run (operator):**
1. Copy `.env.example` to `.env` and set `ENTSOE_API_TOKEN` (ING-020/021).
2. `make lint && make test` — confirm green (already green in CI-equivalent offline run).
3. `make backfill` — verify the four `data/raw/entsoe_*` trees fill with `YYYY/*.parquet`.
4. `make validate-ingest` — expect ING-080..085 all PASS in `reports/ingestion/validation_*.md`.
5. If any gate fails: do NOT widen bands (A-2) — investigate parser/timezone/units and file an ADR if a spec deviation is genuinely needed.

Resume with `/gsd-verify-work 2` after running the above.
