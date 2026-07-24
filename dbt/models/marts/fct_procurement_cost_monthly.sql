-- Implements: SPEC-02 §5 fct_procurement_cost_monthly, DM-063, SG-06
--
-- Local month x strategy_id procurement-cost mart: year_local, month_local,
-- strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh. A thin loader over
-- the SPEC-05 (M6) strategy-simulator output, re-exposed to the warehouse
-- via source('raw_processed', 'procurement_cost_monthly'). Until M6 lands,
-- that source is fed by this phase's D-04/D-05 stand-in generator
-- (scripts/bootstrap_fixture_warehouse.py) -- ADR-010. This model is NEVER
-- disabled or forked by build-order (SG-06). Every strategy_id emitted here
-- must exist in dim_strategy (DM-063, tested in facts_future.yml).

select
    year_local,
    month_local,
    strategy_id,
    volume_mwh,
    cost_eur,
    unit_cost_eur_mwh
from {{ source('raw_processed', 'procurement_cost_monthly') }}
