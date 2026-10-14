-- Q1: what did each procurement strategy cost per calendar year?
-- Grain: delivery year × strategy. Source: fct_procurement_cost_monthly
-- (SPEC-05 ST-001 output re-exposed by dbt) + dim_strategy. CALIBRATED.
with annual as (
    select
        cost.year_local as year,
        cost.strategy_id,
        sum(cost.volume_mwh) as volume_mwh,
        sum(cost.cost_eur) as cost_eur
    from marts.fct_procurement_cost_monthly as cost
    group by cost.year_local, cost.strategy_id
)

select
    annual.year,
    annual.strategy_id,
    strategy.strategy_name,
    annual.volume_mwh,
    annual.cost_eur,
    annual.cost_eur / annual.volume_mwh as unit_cost_eur_mwh,
    annual.cost_eur - min(annual.cost_eur) over (partition by annual.year) as delta_vs_min_eur,
    rank() over (partition by annual.year order by annual.cost_eur) as rank
from annual
inner join marts.dim_strategy as strategy
    on annual.strategy_id = strategy.strategy_id
order by annual.year, annual.strategy_id
