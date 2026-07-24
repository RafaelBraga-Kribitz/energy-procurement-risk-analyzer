-- Implements: DM-005
-- SPEC-02 §3 stg_load_at_hourly: hour-grain mean of sub-hourly Austrian load
-- MW (ING-051 — MW stays MW here; MWh conversion is dbt mart work). ts_utc
-- stays UTC; no timezone-conversion call (DM-011).
select
    date_trunc('hour', ts_utc) as ts_utc,
    avg(load_mw) as load_mw
from {{ source('raw', 'entsoe_load_at') }}
group by 1
