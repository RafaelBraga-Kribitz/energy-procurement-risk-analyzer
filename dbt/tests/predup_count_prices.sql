{{ config(severity='warn') }}

-- DM-020 defense-in-depth: warns (never fails the build) when the RAW price
-- sources have more than 30 duplicate ts_utc rows in any single UTC
-- calendar month x zone, ahead of the native staging views' single-point
-- dedup (qualify row_number() over (partition by ts_utc order by
-- ingested_at_utc desc) = 1). Reads the RAW sources directly, not the
-- deduped native view, so a duplicate spike is surfaced independently of
-- whether the dedup rule masked it.

with raw_prices as (
    select ts_utc, zone from {{ source('raw', 'entsoe_prices_at') }}
    union all
    select ts_utc, zone from {{ source('raw', 'entsoe_prices_delu') }}
),

per_ts as (
    select
        date_trunc('month', ts_utc) as month_utc,
        zone,
        ts_utc,
        count(*) as n_rows
    from raw_prices
    group by 1, 2, 3
),

per_month as (
    select
        month_utc,
        zone,
        sum(n_rows - 1) as n_duplicates
    from per_ts
    where n_rows > 1
    group by 1, 2
)

select *
from per_month
where n_duplicates > 30
