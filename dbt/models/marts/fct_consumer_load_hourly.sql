-- Implements: SPEC-02 §5 fct_consumer_load_hourly, DM-010, LP-003, SG-06
--
-- Hour-grain consumer-load mart: ts_utc, load_mwh. A thin loader over the
-- SPEC-03 LP-003 module output data/processed/consumer_load_hourly.parquet,
-- re-exposed via source('raw_processed', 'consumer_load_hourly'). Until M4
-- lands, that file is a stand-in written by
-- scripts/bootstrap_fixture_warehouse.py with the identical contract
-- (ADR-016). This model is NEVER disabled or forked by build-order (SG-06).
--
-- The casts only pin types (ADR-014): LP-003 says "TIMESTAMP UTC", so a
-- naive-UTC parquet timestamp is read as UTC by the UTC-pinned session and
-- a tz-aware UTC one passes through unchanged -- either way the mart column
-- is TIMESTAMPTZ like every other ts_utc join key (DM-010).

select
    cast(ts_utc as timestamptz) as ts_utc,
    cast(load_mwh as double) as load_mwh
from {{ source('raw_processed', 'consumer_load_hourly') }}
