{{ config(enabled=var('check_freshness', false)) }}

-- Implements: SPEC-02 §6 DM-066 freshness (refresh-only)
--
-- Newest ts_utc in stg_prices_at_hourly must be less than 40 days old, else
-- error. Scheduled runs only (`make refresh`), so it is disabled by default
-- and enabled with:
--   cd dbt && dbt test --select freshness_stg_prices_at_hourly --vars '{check_freshness: true}'
-- An EMPTY price view (max(ts_utc) is NULL) also fails -- no data is never
-- "fresh".

select max(ts_utc) as newest_ts_utc
from {{ ref('stg_prices_at_hourly') }}
having max(ts_utc) is null
    or max(ts_utc) < current_timestamp - interval '40 days'
