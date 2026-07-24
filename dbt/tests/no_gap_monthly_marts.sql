-- Implements: SPEC-02 §5 DM-050 no-gap month spine
--
-- Every monthly mart must cover a contiguous run of local months between
-- its own min and max, with no gaps -- each mart is checked independently
-- (D-05/D-06 aligns the consumer-load/procurement-cost stand-in window to
-- the surrounding real/synthetic ingestion window, but this test does not
-- assume all three marts share an identical range). Uses the hand-rolled
-- month_spine macro (04-01) over DuckDB's native generate_series -- zero
-- dbt_utils dependency (ADR-001).

with price_monthly as (
    select make_date(year_local, month_local, 1) as month_local
    from {{ ref('fct_price_monthly') }}
    group by 1
),

price_monthly_spine as (
    {{ month_spine(
        "(select min(month_local) from price_monthly)",
        "(select max(month_local) from price_monthly)"
    ) }}
),

price_monthly_gaps as (
    select 'fct_price_monthly' as mart_name, spine.month_local
    from price_monthly_spine as spine
    left join price_monthly as actual using (month_local)
    where actual.month_local is null
),

generation_monthly as (
    select make_date(year_local, month_local, 1) as month_local
    from {{ ref('fct_generation_monthly') }}
    group by 1
),

generation_monthly_spine as (
    {{ month_spine(
        "(select min(month_local) from generation_monthly)",
        "(select max(month_local) from generation_monthly)"
    ) }}
),

generation_monthly_gaps as (
    select 'fct_generation_monthly' as mart_name, spine.month_local
    from generation_monthly_spine as spine
    left join generation_monthly as actual using (month_local)
    where actual.month_local is null
),

procurement_cost_monthly as (
    select make_date(year_local, month_local, 1) as month_local
    from {{ ref('fct_procurement_cost_monthly') }}
    group by 1
),

procurement_cost_monthly_spine as (
    {{ month_spine(
        "(select min(month_local) from procurement_cost_monthly)",
        "(select max(month_local) from procurement_cost_monthly)"
    ) }}
),

procurement_cost_monthly_gaps as (
    select 'fct_procurement_cost_monthly' as mart_name, spine.month_local
    from procurement_cost_monthly_spine as spine
    left join procurement_cost_monthly as actual using (month_local)
    where actual.month_local is null
)

select * from price_monthly_gaps
union all
select * from generation_monthly_gaps
union all
select * from procurement_cost_monthly_gaps
