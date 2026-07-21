# Synthesized Constraints (SPECs)

## SPEC-01: General ingestion rules
- source: docs/SPEC-01_data_ingestion.md
- type: protocol
- content: |
  ING-001..010: All ingestion in `src/epra/ingest/`; CLI entrypoints; idempotent monthly parquet with atomic overwrite; raw means raw (UTC `ts_utc`, `ingested_at_utc`, `source`, `request_hash` only additions); tenacity retry; politeness sleeps; response caching under `data/cache/` with 7-day rule; `data/raw/` and `data/cache/` gitignored.

## SPEC-01: ENTSO-E client and fetch
- source: docs/SPEC-01_data_ingestion.md
- type: api-contract
- content: |
  ING-020..022: Token via `ENTSOE_API_TOKEN` env var only. Client library: use `entsoe-py` (`EntsoePandasClient`), version pinned in SPEC-07 §3. Wrap it — never call from analytics. If entsoe-py cannot serve a need, fall back to raw REST per Appendix A and write an ADR.
  ING-030..032: Fetch AT/DE-LU prices, AT load, AT generation; ≤90-day chunks; convert returned index to UTC before persisting; generation in LONG format with PSR code and name.

## SPEC-01: Window management
- source: docs/SPEC-01_data_ingestion.md
- type: protocol
- content: |
  ING-040..042: `make backfill` 2019-01-01 → end of last complete month; `make ingest` 45-day lookback. "Latest complete month" = last calendar month for which ALL days have price data present after ingestion; computed by `epra.ingest.entsoe:latest_complete_month()`.

## SPEC-01: Resolution handling
- source: docs/SPEC-01_data_ingestion.md
- type: protocol
- content: |
  ING-060..063: Every raw price row carries `resolution` ('PT60M' or 'PT15M'). Canonical analytical resolution is HOURLY; 15-min prices aggregated by arithmetic mean in staging (SPEC-02). Dedicated pytest fixture for 15-min→hourly mean aggregation.

## SPEC-01: Raw output contracts
- source: docs/SPEC-01_data_ingestion.md
- type: schema
- content: |
  ING-070: Path pattern `data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet`. Exact column contracts for entsoe_prices_at, entsoe_prices_delu, entsoe_load_at, entsoe_gen_at, geosphere_graz_daily. Contract tests in `tests/test_raw_contracts.py` against fixtures.

## SPEC-01: Validation gates
- source: docs/SPEC-01_data_ingestion.md
- type: nfr
- content: |
  ING-080..085: ENTSO-E validation gates run after every ingest via `make validate-ingest`; results in validation report. GeoSphere ING-094; ÖSPI ING-101/103 double-entry validation.

## SPEC-01: Calendar generation
- source: docs/SPEC-01_data_ingestion.md
- type: schema
- content: |
  ING-110..111: `calendar.py` generates `data/raw/calendar/calendar.parquet` hourly UTC 2019-01-01 → end of forward-risk window. Columns include `is_holiday_at` (holidays package, subdiv='6' for Styria), `is_peak_hour` (Mon–Fri and 8 ≤ hour_local < 20 and not holiday).

## SPEC-02: Stack and schema layers
- source: docs/SPEC-02_data_model.md
- type: schema
- content: |
  DM-001..005: DuckDB file `data/warehouse/epra.duckdb`; dbt with dbt-duckdb at `dbt/`. Layers: raw (external parquet), staging (view), marts (table). Schemas literally `staging` and `marts`. Staging `stg_*`, marts `fct_*`/`dim_*`; snake_case with unit suffixes.

## SPEC-02: Timezone doctrine
- source: docs/SPEC-02_data_model.md
- type: protocol
- content: |
  DM-010..012: `ts_utc` is join key everywhere. Local calendar attributes ONLY from joining `dim_calendar` (ING-110). Calendar year = local Europe/Vienna year via `year_local`.

## SPEC-02: Staging model contracts
- source: docs/SPEC-02_data_model.md
- type: schema
- content: |
  DM-020: Staging models with exact grain/columns/logic for prices (native and hourly), load, generation, weather, ÖSPI. Dedup via `qualify row_number()` — ONLY place duplicates silently resolved; warn if month has >30 pre-dedup dupes.

## SPEC-02: Dimension contracts
- source: docs/SPEC-02_data_model.md
- type: schema
- content: |
  `dim_calendar`: ts_utc, date_local, year_local, month_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour, season, hdd_18, cdd_22.
  `dim_strategy`: seeded S1, S2, S3, S4_30/50/70 from CSV.

## SPEC-02: Mart contracts
- source: docs/SPEC-02_data_model.md
- type: schema
- content: |
  DM-050: Marts include `fct_price_hourly` (ts_utc, prices, spread, load, is_negative_price + all dim_calendar attributes), `fct_price_daily`, `fct_price_monthly`, `fct_generation_monthly`, `fct_consumer_load_hourly`, `fct_procurement_cost_monthly`. No NULL keys; monthly marts cover full analysis window.

## SPEC-02: dbt tests
- source: docs/SPEC-02_data_model.md
- type: nfr
- content: |
  DM-060..066: unique/not_null, accepted ranges, row counts (8760/8784 ±24 per year), relationship tests, reconciliation singular test (2022-08), DST edge tests, freshness for scheduled runs.

## SPEC-03: Load profile principles
- source: docs/SPEC-03_consumer_load_profile.md
- type: protocol
- content: |
  LP-001..004: Deterministic given YAML + calendar; all parameters in `config/consumer_profile.yaml`; output `consumer_load_hourly.parquet` with forward window; annual normalization 50,000 MWh per local year ±0.01 MWh.

## SPEC-03: Construction algorithm
- source: docs/SPEC-03_consumer_load_profile.md
- type: protocol
- content: |
  LP algorithm in `consumer/profile.py`: base weight = day_shape × seasonal × special; day_type priority shutdown → holiday-as-weekend → weekend → weekday; normalize per local year. Maintenance: FIRST full Mon–Sun week of August (first Monday through following Sunday), factor 0.60. Christmas shutdown Dec 24–Jan 1.

## SPEC-03: Derived facts and tests
- source: docs/SPEC-03_consumer_load_profile.md
- type: nfr
- content: |
  LP-020: Peak share = fraction of annual volume in peak hours (Mon–Fri 08–20 local, non-holiday); exact value to SSOT as `consumer_peak_share`. LP-030 flat_baseload sensitivity mandatory. LP-040..042 golden + property tests (M4 exit gates).

## SPEC-04: Analytics modules A1–A4
- source: docs/SPEC-04_analytics.md
- type: protocol
- content: |
  A1 descriptive market structure; A2 AT–DE-LU spread; A3 volatility regimes (HMM, GARCH); A4 weather/load sensitivity. Degree-day definitions hdd_18/cdd_22. M5 deliverables and AN-701..705 exit gates including crisis-regime sanity gate AN-304.

## SPEC-05: Strategy definitions S1–S4
- source: docs/SPEC-05_strategy_simulator.md
- type: protocol
- content: |
  S1 FULL_SPOT hourly join; S2 OESPI_INDEXED monthly with `w_peak = consumer_peak_share` from SSOT (ST-102); S3 FIXED_ANNUAL lock-window ÖSPI proxy; S4 HYBRID_h at 0.30/0.50/0.70. Calibration anchors ST-201..204. Fair-comparison ST-501..503.

## SPEC-05: Forward risk bootstrap
- source: docs/SPEC-05_strategy_simulator.md
- type: protocol
- content: |
  ST-401: Seasonal block bootstrap N=2000, seed=42; draw month with prices AND ÖSPI together; hour alignment by day-of-month index and hour_local with same-weekday-type fallback and DST forward fill; regime-conditioned variant excluding crisis years.
  ST-403: Outputs mean, std, P5, P50, P95, CVaR95 (mean of worst 5% = highest costs). ST-405 determinism; ST-406 vectorized implementation recommended.

## SPEC-05: M6 exit gates
- source: docs/SPEC-05_strategy_simulator.md
- type: nfr
- content: |
  ST-601..604: golden tests, sanity relations ST-602 (especially (a) calibration before debug), determinism, sensitivity outputs.

## SPEC-06: Reporting artifacts
- source: docs/SPEC-06_reporting_dashboard.md
- type: protocol
- content: |
  Four executive charts in `reports/executive_charts/`; Power BI dashboard manual build with exports; EXEC_SUMMARY ≤2 pages mandatory structure; README §6 order mandatory; chart standards §7; epistemic tags on captions; numbers only from SSOT.

## SPEC-07: Toolchain and layout
- source: docs/SPEC-07_engineering.md
- type: nfr
- content: |
  Python 3.12, uv, ruff, mypy --strict, pre-commit. Repository layout per §2. Pinned dependencies in pyproject.toml; upgrades require ADR. Makefile canonical interface. EN-xxx requirements for CI (ci.yml, refresh.yml), testing policy, git conventions.

## SPEC-07: CI/CD gates
- source: docs/SPEC-07_engineering.md
- type: nfr
- content: |
  ci.yml: lint → tests+coverage → dbt fixture build → SSOT consistency. refresh.yml cron for data refresh. EN-002 mypy --strict on `src/epra/` with ignore_missing_imports only for entsoe/hmmlearn/arch (extended to statsmodels per ADR-002).

## SPEC-08: Epistemic tags and ADRs
- source: docs/SPEC-08_governance_quality.md
- type: protocol
- content: |
  GV-101/102: VERIFIED/CALIBRATED/SIMULATED tags per Charter §5; SSOT rows and chart captions carry tags.
  GV-201..203: ADRs in `docs/ADR/`, append-only template, mandatory triggers for charter change, spec deviation, new dependency, gate widening, ÖSPI/GeoSphere choices.

## SPEC-08: SSOT mechanism
- source: docs/SPEC-08_governance_quality.md
- type: protocol
- content: |
  GV-301..303: `NUMERIC_SSOT.md` generated ONLY by `scripts/generate_ssot.py`; minimum key set defined; `check_ssot_consistency.py` CI-required parses README and EXEC_SUMMARY for numeric literals matching SSOT within rounding documented in script; whitelist in `ssot_whitelist.txt`.

## SPEC-08: Lightweight governance boundary
- source: docs/SPEC-08_governance_quality.md
- type: nfr
- content: |
  §7: No audit-finding registry, session handouts, re-verification matrix, or governance CI beyond §4. Governance weight ≈30% of decision-analytics-reconstruction repo (Charter §4.2 O-5). Reinforced by locked ADR-001.

## SPEC-08: LIMITATIONS.md sections
- source: docs/SPEC-08_governance_quality.md
- type: nfr
- content: |
  §6: Seven mandatory sections — constructed load profile, ÖSPI proxy limits, fixed premium assumption, bootstrap history limits, grid fees excluded, 2025 caveats, no forecast-skill claim.
