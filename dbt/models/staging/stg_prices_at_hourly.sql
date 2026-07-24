-- Implements: DM-005, DM-020
-- SPEC-02 §3 stg_prices_at_hourly: hour-grain mean of the (already deduped,
-- DM-020) native Austrian price view. n_subhours is ALWAYS emitted alongside
-- the mean (1 for a PT60M source hour, 4 for PT15M; mixed-resolution months
-- handled per-row by the group-by-truncated-hour) — never a bare avg that
-- drops it (Pitfall 4). ts_utc stays UTC; no timezone-conversion call (DM-011).
select
    date_trunc('hour', ts_utc) as ts_utc,
    avg(price_eur_mwh) as price_eur_mwh,
    count(*) as n_subhours
from {{ ref('stg_prices_at_native') }}
group by 1
