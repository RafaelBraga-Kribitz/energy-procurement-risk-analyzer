{{ config(enabled=var('check_freshness', false)) }}

-- Implements: SPEC-02 §6 DM-066 freshness (refresh-only)
--
-- Newest ts_utc in stg_prices_at_hourly must be less than 40 days old. This
-- test is wired now but exercised only at M7's `make refresh`, which passes
-- `--vars '{check_freshness: true}'` -- the `enabled=var('check_freshness',
-- false)` gate means a normal `dbt build`/`make transform` never runs it
-- (default false).

select max(ts_utc) as newest_ts_utc
from {{ ref('stg_prices_at_hourly') }}
having max(ts_utc) < current_timestamp - interval '40 days'
