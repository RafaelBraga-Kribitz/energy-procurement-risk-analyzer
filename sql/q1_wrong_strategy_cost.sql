-- Q1 headline (ST-302): what did buying the wrong way cost, per year and in total?
-- wrong_strategy_cost(Y) = max over strategies − min over strategies. CALIBRATED.
with annual as (
    select
        cost.year_local as year,
        cost.strategy_id,
        sum(cost.cost_eur) as cost_eur
    from marts.fct_procurement_cost_monthly as cost
    group by cost.year_local, cost.strategy_id
),

per_year as (
    select
        year,
        max(cost_eur) - min(cost_eur) as wrong_strategy_cost_eur,
        arg_max(strategy_id, cost_eur) as worst_strategy,
        arg_min(strategy_id, cost_eur) as best_strategy
    from annual
    group by year
)

select
    year,
    wrong_strategy_cost_eur,
    worst_strategy,
    best_strategy,
    sum(wrong_strategy_cost_eur) over () as wrong_strategy_cost_total_eur
from per_year
order by year
