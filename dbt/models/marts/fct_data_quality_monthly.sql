-- Implements: ADR-020 §3 (visible data-quality layer), DM-005, DM-011, DM-050
--
-- One row per local month of the priced window: how complete and how clean the
-- inputs behind every result are. Feeds reports/data_quality/ and the Power BI
-- "Data quality" page. Every flag is computed from marts/staging already under
-- dbt test, so this model adds visibility, not new logic:
--   coverage   — priced AT/DE-LU hours, load hours, weather days vs calendar
--   DST        — local days with 23 or 25 hours in the month (ING-080)
--   resolution — hours aggregated from PT15M quarters vs native PT60M (R-2)
--   prices     — negative-price hours (ING-083), ÖSPI present (ING-103)

with calendar_month as (
    select
        year_local,
        month_local,
        count(*) as expected_hours,
        count(distinct date_local) as days_in_month
    from {{ ref('dim_calendar') }}
    group by year_local, month_local
),

dst_days as (
    select
        year_local,
        month_local,
        count(*) as n_dst_days
    from (
        select year_local, month_local, date_local, count(*) as hours_in_day
        from {{ ref('dim_calendar') }}
        group by year_local, month_local, date_local
    ) as day_hours
    where hours_in_day <> 24
    group by year_local, month_local
),

hourly as (
    select
        fph.year_local,
        fph.month_local,
        count(fph.price_at_eur_mwh) as priced_hours_at,
        count(fph.price_delu_eur_mwh) as priced_hours_delu,
        count(fph.load_at_mw) as load_hours,
        count(*) filter (where fph.is_negative_price) as n_negative_hours,
        count(*) filter (where stg.n_subhours = 4) as n_hours_from_pt15m
    from {{ ref('fct_price_hourly') }} as fph
    left join {{ ref('stg_prices_at_hourly') }} as stg
        on fph.ts_utc = stg.ts_utc
    group by fph.year_local, fph.month_local
),

weather as (
    select
        year(date_local) as year_local,
        month(date_local) as month_local,
        count(tavg_c) as weather_days
    from {{ ref('stg_weather_graz_daily') }}
    group by 1, 2
),

priced_window as (
    select
        min(make_date(year_local, month_local, 1)) as first_month,
        max(make_date(year_local, month_local, 1)) as last_month
    from {{ ref('fct_price_monthly') }}
)

select
    cast(cm.year_local as integer) as year_local,
    cast(cm.month_local as integer) as month_local,
    cast(cm.expected_hours as bigint) as expected_hours,
    cast(coalesce(h.priced_hours_at, 0) as bigint) as priced_hours_at,
    cast(coalesce(h.priced_hours_delu, 0) as bigint) as priced_hours_delu,
    cast(coalesce(h.load_hours, 0) as bigint) as load_hours,
    cast(coalesce(w.weather_days, 0) as bigint) as weather_days,
    cast(cm.days_in_month as bigint) as days_in_month,
    round(100.0 * coalesce(h.priced_hours_at, 0) / cm.expected_hours, 3) as coverage_at_pct,
    cast(coalesce(d.n_dst_days, 0) as bigint) as n_dst_days,
    cast(coalesce(h.n_hours_from_pt15m, 0) as bigint) as n_hours_from_pt15m,
    case
        when coalesce(h.n_hours_from_pt15m, 0) = 0 then 'PT60M'
        when h.n_hours_from_pt15m = h.priced_hours_at then 'PT15M'
        else 'mixed'
    end as resolution,
    cast(coalesce(h.n_negative_hours, 0) as bigint) as n_negative_hours,
    fpm.oespi_base is not null as has_oespi
from calendar_month as cm
cross join priced_window as pw
left join hourly as h
    on cm.year_local = h.year_local and cm.month_local = h.month_local
left join dst_days as d
    on cm.year_local = d.year_local and cm.month_local = d.month_local
left join weather as w
    on cm.year_local = w.year_local and cm.month_local = w.month_local
left join {{ ref('fct_price_monthly') }} as fpm
    on cm.year_local = fpm.year_local and cm.month_local = fpm.month_local
where make_date(cm.year_local, cm.month_local, 1) between pw.first_month and pw.last_month
