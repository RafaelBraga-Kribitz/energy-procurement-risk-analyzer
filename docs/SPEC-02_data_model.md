# SPEC-02 — Data Model (DuckDB + dbt)

Governs everything between `data/raw/` and analytical consumption. Requirement IDs: `DM-xxx`.

---

## 1. Stack and layout

- DM-001: Warehouse: single DuckDB file `data/warehouse/epra.duckdb` (gitignored).
- DM-002: Transformation: dbt with the `dbt-duckdb` adapter, project at `dbt/`
  (`dbt_project.yml`, `profiles.yml` committed with a relative path to the DuckDB file;
  no credentials involved).
- DM-003: Layers and schemas:

  | Layer | dbt folder | DuckDB schema | Materialization |
  |-------|-----------|---------------|-----------------|
  | Sources (raw parquet) | `dbt/models/sources.yml` | `raw` (external via `read_parquet`) | view over files |
  | Staging | `dbt/models/staging/` | `staging` | view |
  | Marts | `dbt/models/marts/` | `marts` | table |

- DM-004: Raw parquet is read via DuckDB `read_parquet('data/raw/<dataset>/**/*.parquet')`
  defined once per source in a staging model — no other model touches files directly.
- DM-005: Naming: staging models `stg_<source>_<entity>`; marts `fct_*` (facts),
  `dim_*` (dimensions). Columns snake_case; units ALWAYS in the column name suffix
  (`_eur_mwh`, `_mw`, `_mwh`, `_c` for °C). A column without a unit suffix must be
  unitless (flags, ids, indices).

## 2. Timezone doctrine (repeat of the single most dangerous bug class)

- DM-010: `ts_utc` is the join key everywhere. It is stored as TIMESTAMP (UTC).
- DM-011: Local calendar attributes (`date_local`, `hour_local`, `is_peak_hour`, …) come
  ONLY from joining `dim_calendar` (built from the calendar parquet, ING-110). No model
  may call timezone conversion functions independently.
- DM-012: "Calendar year 2022" ALWAYS means local (Europe/Vienna) year via
  `dim_calendar.year_local`. Tests must include the two DST edge hours.

## 3. Staging models (exact contracts)

| Model | Grain | Columns | Logic |
|-------|-------|---------|-------|
| `stg_prices_at_native` | native MTU | `ts_utc, price_eur_mwh, resolution, zone` | passthrough + dedup (`qualify row_number() over (partition by ts_utc order by ingested_at_utc desc) = 1`) |
| `stg_prices_delu_native` | native MTU | same | same |
| `stg_prices_at_hourly` | hour | `ts_utc, price_eur_mwh, n_subhours` | if resolution PT60M: passthrough (`n_subhours=1`); if PT15M: mean of quarters per hour (`n_subhours=4`); mixed months handled per-row by truncating ts to hour and averaging |
| `stg_prices_delu_hourly` | hour | same | same |
| `stg_load_at_hourly` | hour | `ts_utc, load_mw` | mean of sub-hourly MW |
| `stg_gen_at_hourly` | hour × psr_type | `ts_utc, psr_type, psr_name, gen_mw` | filter `kind='aggregated'`; mean of sub-hourly MW |
| `stg_weather_graz_daily` | day | `date_local, tavg_c` | rename; `date` from GeoSphere is local civil date — document assumption in the model YAML |
| `stg_oespi_monthly` | month | `month_local (DATE, first of month), oespi_base, oespi_peak` | from `data/manual/oespi_monthly.csv` via `read_csv` |

- DM-020: Dedup rule above is the ONLY place duplicates may be silently resolved; a dbt
  test still counts pre-dedup duplicates and warns if a month has > 30.

## 4. Dimensions

### `dim_calendar` (grain: hour)

`ts_utc, date_local, year_local, month_local, hour_local, dow_local, is_weekend,
is_holiday_at, is_peak_hour` — direct load of the calendar parquet (ING-110), plus:
`season` ('winter' if month_local in (11,12,1,2,3) else 'summer' — Austrian energy
convention documented in model YAML), `hdd_18 = greatest(0, 18 − tavg_c)` and
`cdd_22 = greatest(0, tavg_c − 22)` joined from daily weather (same value repeated for
all 24 hours of the local day).

### `dim_strategy` (grain: strategy)

Seeded from `dbt/seeds/dim_strategy.csv`:

```csv
strategy_id,strategy_name,description
S1,FULL_SPOT,All volume at AT day-ahead hourly price
S2,OESPI_INDEXED,Monthly price indexed to OESPI (base/peak blended)
S3,FIXED_ANNUAL,Single annual price locked pre-year via OESPI proxy
S4_30,HYBRID_30,30% hedged at S3 price + 70% spot
S4_50,HYBRID_50,50% hedged + 50% spot
S4_70,HYBRID_70,70% hedged + 30% spot
```

## 5. Marts (exact contracts — the M3 exit gate diff-checks these)

| Model | Grain | Columns |
|-------|-------|---------|
| `fct_price_hourly` | hour | `ts_utc, price_at_eur_mwh, price_delu_eur_mwh, spread_at_delu_eur_mwh (= at − delu), load_at_mw, is_negative_price (at < 0)` + all `dim_calendar` attributes |
| `fct_price_daily` | local day | `date_local, price_base_eur_mwh (mean 24h), price_peak_eur_mwh (mean of peak hours; NULL on days without peak hours), price_min, price_max, price_std, n_negative_hours, tavg_c, hdd_18, cdd_22` |
| `fct_price_monthly` | local month | `year_local, month_local, price_base_eur_mwh, price_peak_eur_mwh, price_offpeak_eur_mwh, n_negative_hours, oespi_base, oespi_peak` |
| `fct_generation_monthly` | local month × psr_type | `year_local, month_local, psr_type, psr_name, gen_gwh (= sum(gen_mw)/1000 per hour count), share_of_total` |
| `fct_consumer_load_hourly` | hour | `ts_utc, load_mwh` — loaded from the SPEC-03 module output parquet `data/processed/consumer_load_hourly.parquet` |
| `fct_procurement_cost_monthly` | local month × strategy | `year_local, month_local, strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh` — loaded from SPEC-05 output parquet (dbt re-exposes it for BI; computation itself is Python, see SPEC-05 §2) |

- DM-050: Marts may not contain NULL `ts_utc`/date keys. Monthly marts cover every month
  in the analysis window with no gaps (dbt test with a generated month spine).

## 6. dbt tests (minimum set; all must pass in `dbt build`)

- DM-060: `unique` + `not_null` on each model's grain key(s) listed in §3–§5.
- DM-061: Accepted ranges: `price_at_eur_mwh` between −500 and 5000; `load_at_mw`
  between 3000 and 13000; `tavg_c` between −30 and 42; `oespi_base > 0`.
- DM-062: Row counts: `fct_price_hourly` per year_local = 8760/8784 ± 24 (custom test).
- DM-063: Relationship: every `fct_procurement_cost_monthly.strategy_id` exists in
  `dim_strategy`.
- DM-064: Reconciliation singular test: for one hardcoded month (2022-08, chosen for the
  crisis peak), `fct_price_monthly.price_base_eur_mwh` equals the mean of
  `fct_price_hourly` for that month within 0.01 (guards aggregation drift).
- DM-065: DST test: 2024-03-31 has 23 local hours, 2024-10-27 has 25 in `fct_price_hourly`.
- DM-066: Freshness (only for scheduled runs, `make refresh`): newest `ts_utc` in
  `stg_prices_at_hourly` is < 40 days old, else error.

## 7. Exports for BI (produced by `make export`, consumed by Power BI — SPEC-06)

`scripts/export_marts.py` writes CSVs (UTF-8, ISO dates, `.` decimal) to `exports/`:

| File | Source mart | Filter |
|------|-------------|--------|
| `exports/price_daily.csv` | `fct_price_daily` | full window |
| `exports/price_monthly.csv` | `fct_price_monthly` | full window |
| `exports/generation_monthly.csv` | `fct_generation_monthly` | full window |
| `exports/procurement_cost_monthly.csv` | `fct_procurement_cost_monthly` | full window |
| `exports/strategy_annual_summary.csv` | SPEC-05 output | 2021–2025 |
| `exports/forward_risk_summary.csv` | SPEC-05 output | forward window |

- DM-070: Export schemas are contract-tested like raw contracts (ING-070 pattern).
  Power BI reads ONLY from `exports/` — never from DuckDB directly (keeps the BI layer
  decoupled and the pbix rebuildable by anyone without the warehouse).
