-- Implements: DM-005, SG-17
-- SPEC-02 §3 stg_gen_at_hourly: hour x psr_type grain, mean of sub-hourly MW
-- (ING-051 — MW stays MW). Filters kind='aggregated' only (SG-17 — raw
-- 'consumption' rows are persisted upstream but have no SSOT value derived
-- from them at this layer). ts_utc stays UTC; no timezone-conversion call
-- (DM-011).
select
    date_trunc('hour', ts_utc) as ts_utc,
    psr_type,
    psr_name,
    avg(value_mw) as gen_mw
from {{ source('raw', 'entsoe_gen_at') }}
where kind = 'aggregated'
group by 1, 2, 3
