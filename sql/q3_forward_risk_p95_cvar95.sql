-- Q3: distribution of the next-12-month cost per strategy (SIMULATED).
-- One row per bootstrap path in forward_paths.parquet (ST-401..406 output).
-- P-quantiles are linear interpolation (= numpy default); CVaR95 is the mean of
-- the worst ceil(5% × N) paths, i.e. the highest costs (ST-403).
with paths as (
    select
        variant,
        strategy_id,
        cost_eur
    from read_parquet('{processed}/forward_paths.parquet')
),

ranked as (
    select
        variant,
        strategy_id,
        cost_eur,
        row_number() over (partition by variant, strategy_id order by cost_eur desc) as worst_rank,
        count(*) over (partition by variant, strategy_id) as n_paths
    from paths
)

select
    variant,
    strategy_id,
    avg(cost_eur) as mean,
    quantile_cont(cost_eur, 0.05) as p5,
    quantile_cont(cost_eur, 0.50) as p50,
    quantile_cont(cost_eur, 0.95) as p95,
    avg(cost_eur) filter (where worst_rank <= ceil(0.05 * n_paths)) as cvar95
from ranked
group by variant, strategy_id
order by variant, strategy_id
