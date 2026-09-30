-- Implements: SPEC-02 §5 fct_procurement_cost_monthly, ST-001, DM-063, SG-06
--
-- Local month x strategy_id procurement-cost mart: year_local, month_local,
-- strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh. A thin loader over
-- the SPEC-05 ST-001 output data/processed/strategy_costs_monthly.parquet,
-- re-exposed via source('raw_processed', 'strategy_costs_monthly') -- dbt
-- never computes strategy costs (ST-001). Until M6 lands, that file is a
-- stand-in written by scripts/bootstrap_fixture_warehouse.py with the
-- identical contract (ADR-016). This model is NEVER disabled or forked by
-- build-order (SG-06). Every strategy_id emitted here must exist in
-- dim_strategy (DM-063, tested in facts_future.yml).
--
-- Casts only pin types so year_local/month_local are INTEGER like every
-- dim_calendar-derived year/month elsewhere (marts_contract.yml).

select
    cast(year_local as integer) as year_local,
    cast(month_local as integer) as month_local,
    cast(strategy_id as varchar) as strategy_id,
    cast(volume_mwh as double) as volume_mwh,
    cast(cost_eur as double) as cost_eur,
    cast(unit_cost_eur_mwh as double) as unit_cost_eur_mwh
from {{ source('raw_processed', 'strategy_costs_monthly') }}
