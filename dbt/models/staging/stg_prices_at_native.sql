-- Implements: DM-005, DM-020
-- SPEC-02 §3 stg_prices_at_native: native MTU passthrough of Austrian day-ahead
-- prices, deduped by the single sanctioned rule (DM-020) — the ONLY place
-- duplicate ts_utc rows are resolved anywhere in this warehouse. ts_utc stays
-- UTC; no timezone-conversion call belongs here (DM-011).
select
    ts_utc,
    price_eur_mwh,
    resolution,
    zone
from {{ source('raw', 'entsoe_prices_at') }}
qualify row_number() over (partition by ts_utc order by ingested_at_utc desc) = 1
