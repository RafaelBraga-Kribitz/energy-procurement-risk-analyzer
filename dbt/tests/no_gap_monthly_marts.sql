-- Implements: SPEC-02 §5 DM-050 no-gap month spine
--
-- "Monthly marts cover every month in the analysis window with no gaps."
-- Checked against a COMMON window, not each mart's own min/max, so a mart
-- that is truncated (or runs off past the data) relative to the others is
-- caught:
--
--   1. fct_price_monthly and fct_generation_monthly come from the same
--      ENTSO-E ingestion window, so BOTH must contain every month of the
--      common window [earliest first month, latest last month] across the
--      two marts. A gap or truncation in either is a failure.
--   2. fct_procurement_cost_monthly (SPEC-05 ST-001 output) covers the
--      retrospective window (ST-301), which is a sub-window of the price
--      data: it must be contiguous within its own min/max AND every one of
--      its months must lie inside the price window (a cost month without a
--      spot-price month is impossible -- catches spine run-off).
--   3. None of the three marts may be empty.
--
-- Uses the hand-rolled month_spine macro over DuckDB's native
-- generate_series -- zero dbt_utils dependency (ADR-001).

with price_months as (
    select distinct make_date(year_local, month_local, 1) as month_local
    from {{ ref('fct_price_monthly') }}
),

generation_months as (
    select distinct make_date(year_local, month_local, 1) as month_local
    from {{ ref('fct_generation_monthly') }}
),

cost_months as (
    select distinct make_date(year_local, month_local, 1) as month_local
    from {{ ref('fct_procurement_cost_monthly') }}
),

entsoe_months as (
    select month_local from price_months
    union all
    select month_local from generation_months
),

common_spine as (
    {{ month_spine(
        "(select min(month_local) from entsoe_months)",
        "(select max(month_local) from entsoe_months)"
    ) }}
),

cost_spine as (
    {{ month_spine(
        "(select min(month_local) from cost_months)",
        "(select max(month_local) from cost_months)"
    ) }}
),

failures as (
    select 'fct_price_monthly' as mart_name, 'missing_month' as failure, spine.month_local
    from common_spine as spine
    left join price_months as actual using (month_local)
    where actual.month_local is null

    union all

    select 'fct_generation_monthly', 'missing_month', spine.month_local
    from common_spine as spine
    left join generation_months as actual using (month_local)
    where actual.month_local is null

    union all

    select 'fct_procurement_cost_monthly', 'missing_month', spine.month_local
    from cost_spine as spine
    left join cost_months as actual using (month_local)
    where actual.month_local is null

    union all

    select 'fct_procurement_cost_monthly', 'outside_price_window', month_local
    from cost_months
    where month_local < (select min(month_local) from price_months)
        or month_local > (select max(month_local) from price_months)

    union all

    select mart_name, 'empty_mart', cast(null as date)
    from (
        select 'fct_price_monthly' as mart_name, (select count(*) from price_months) as n
        union all
        select 'fct_generation_monthly', (select count(*) from generation_months)
        union all
        select 'fct_procurement_cost_monthly', (select count(*) from cost_months)
    ) as sizes
    where n = 0
)

select * from failures
