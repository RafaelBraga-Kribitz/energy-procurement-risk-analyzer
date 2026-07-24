-- Implements: SPEC-02 §5 fct_generation_monthly, DM-050
--
-- Local month x psr_type generation mart. year_local/month_local come only
-- from the dim_calendar join on ts_utc (DM-011 — no timezone-conversion
-- call). gen_gwh = sum(gen_mw)/1000 aggregated across the month's hours
-- (per SPEC-02 §5, "sum(gen_mw)/1000 per hour count"); share_of_total is
-- each psr_type's share of that month's total generation (window function
-- over year_local, month_local).

with gen as (
    select
        stg_gen_at_hourly.psr_type,
        stg_gen_at_hourly.psr_name,
        stg_gen_at_hourly.gen_mw,
        dim_calendar.year_local,
        dim_calendar.month_local
    from {{ ref('stg_gen_at_hourly') }}
    inner join {{ ref('dim_calendar') }}
        on stg_gen_at_hourly.ts_utc = dim_calendar.ts_utc
),

monthly as (
    select
        year_local,
        month_local,
        psr_type,
        max(psr_name) as psr_name,
        sum(gen_mw) / 1000.0 as gen_gwh
    from gen
    group by year_local, month_local, psr_type
)

select
    year_local,
    month_local,
    psr_type,
    psr_name,
    gen_gwh,
    gen_gwh / sum(gen_gwh) over (partition by year_local, month_local) as share_of_total
from monthly
