-- Implements: SPEC-02 §5 fct_consumer_load_hourly, SG-06
--
-- Hour-grain consumer-load mart: ts_utc, load_mwh. A thin loader over the
-- SPEC-03 (M4) module output, re-exposed to the warehouse via
-- source('raw_processed', 'consumer_load_hourly'). Until M4 lands, that
-- source is fed by this phase's D-04/D-05 stand-in generator
-- (scripts/bootstrap_fixture_warehouse.py) -- ADR-010. This model is NEVER
-- disabled or forked by build-order (SG-06): it always builds off whatever
-- currently populates data/processed/consumer_load_hourly/**.

select
    ts_utc,
    load_mwh
from {{ source('raw_processed', 'consumer_load_hourly') }}
