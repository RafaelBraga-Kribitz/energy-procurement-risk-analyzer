-- Implements: DM-005, DM-020
-- SPEC-02 §3 stg_prices_delu_native: native MTU passthrough of DE-LU day-ahead
-- prices, deduped by the single sanctioned rule (DM-020) — the ONLY place
-- duplicate ts_utc rows are resolved anywhere in this warehouse. ts_utc stays
-- UTC; no timezone-conversion call belongs here (DM-011).
select
    ts_utc,
    price_eur_mwh,
    resolution,
    zone
from {{ source('raw', 'entsoe_prices_delu') }}
-- ingested_at_utc is persisted as an ISO-8601 string (ING-004); cast it so
-- "latest ingestion wins" orders chronologically, never lexicographically.
-- A malformed value fails the cast loudly instead of mis-ordering silently.
qualify row_number() over (
    partition by ts_utc order by cast(ingested_at_utc as timestamptz) desc
) = 1
