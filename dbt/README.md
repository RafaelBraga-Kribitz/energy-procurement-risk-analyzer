# dbt project — the M3 warehouse (SPEC-02)

DuckDB + `dbt-duckdb` project that turns `data/raw/`, `data/manual/` and
`data/processed/` into the analytical marts every later milestone reads.
Requires dbt-core >= 1.10 (`require-dbt-version` in `dbt_project.yml`;
generic tests use the `arguments:` syntax — ADR-012).

## Layout

| Path | What it holds |
|------|---------------|
| `dbt_project.yml` | layers → schemas/materializations (DM-003): `staging` views, `marts` tables |
| `profiles.yml` | committed DuckDB profile, no credentials (DM-002); session `TimeZone: UTC` pin (ADR-014) |
| `models/sources.yml` | every external file read exactly once (DM-004): raw ENTSO-E/GeoSphere parquet, the ING-110 calendar, `data/manual/oespi_monthly.csv`, and the two module outputs `data/processed/consumer_load_hourly.parquet` (SPEC-03 LP-003) and `data/processed/strategy_costs_monthly.parquet` (SPEC-05 ST-001) |
| `models/staging/` | the eight SPEC-02 §3 staging views (15-min → hourly MEAN, trap T-2; the single DM-020 dedup rule) |
| `models/marts/` | `dim_calendar` + the six SPEC-02 §5 fact marts; `dim_strategy` comes from `seeds/` |
| `contracts/marts_contract.yml` | column name/type contract for all 8 `marts` objects, enforced by `tests/unit/test_marts_contract.py` |
| `macros/` | `accepted_range`, `unique_combination_of_columns` (zero-package generic tests, ADR-001), `month_spine`, `generate_schema_name` (ADR-009) |
| `tests/` | singular tests: DM-050 no-gap months, DM-062 row counts, DM-064 2022-08 reconciliation, DM-065 DST days, DM-066 freshness, DM-020 pre-dedup warning, session-TimeZone pin |

Timezone doctrine (DM-010..012): `ts_utc` is the join key everywhere
(TIMESTAMPTZ in a UTC-pinned session, ADR-014); local attributes come ONLY
from `dim_calendar`; no model calls timezone conversion functions.

Monthly price marts cover only the months that hold actual AT price data;
the calendar (and therefore `fct_price_hourly` / `fct_price_daily`) runs on
into the forward-risk horizon with NULL prices.

## Build locally (real data)

After M1/M2 ingestion has populated `data/raw/` (and until M4/M6 write
their outputs, the processed stand-ins — ADR-016):

```bash
uv run python scripts/bootstrap_fixture_warehouse.py --processed-only   # stand-ins only; never touches data/raw or data/manual
cd dbt && uv run dbt build                                             # models + all tests
cd .. && uv run pytest tests/unit/test_marts_contract.py -m "not live" --no-cov
```

`EPRA_DUCKDB_PATH=/some/other.duckdb` points the profile at a different
warehouse file (default `../data/warehouse/epra.duckdb`, DM-001).

## Build on fixtures (CI, EN-080 job 3)

On a fresh checkout with an empty `data/raw/`:

```bash
uv run python scripts/bootstrap_fixture_warehouse.py --force   # synthesizes data/raw + data/processed (2022-2024); data/manual is never written
cd dbt && uv run dbt build
cd .. && uv run pytest tests/unit/test_marts_contract.py -m "not live" --no-cov
```

The committed, human-reconciled `data/manual/oespi_monthly.csv` is used as
is in both modes.

## Freshness gate (DM-066, scheduled runs only)

Disabled in a normal `dbt build`; enable it explicitly:

```bash
cd dbt && uv run dbt test --select freshness_stg_prices_at_hourly --vars '{check_freshness: true}'
```

It fails when the newest `stg_prices_at_hourly.ts_utc` is 40 days old or
more, or when there are no prices at all.
