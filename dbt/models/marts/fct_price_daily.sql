-- Implements: SPEC-02 §5 fct_price_daily, SG-14/ADR-011, DM-050
--
-- Local day-grain aggregation of fct_price_hourly. price_peak_eur_mwh is
-- the mean of AT price over hours where the ONE holiday-aware
-- `is_peak_hour` (from dim_calendar, ADR-011) is true; on a local day with
-- no peak hours (a public holiday), the FILTER predicate leaves zero rows
-- for the aggregate, so `avg(...) filter (where is_peak_hour)` returns
-- NULL rather than 0 or a wrong mean — the empty-input edge SG-14/ADR-011
-- requires. No timezone-conversion call (DM-011); date_local comes only
-- from the dim_calendar-spined fct_price_hourly.

with hourly as (
    select
        date_local,
        price_at_eur_mwh,
        is_peak_hour,
        is_negative_price,
        hdd_18,
        cdd_22
    from {{ ref('fct_price_hourly') }}
),

weather as (
    select date_local, tavg_c
    from {{ ref('stg_weather_graz_daily') }}
),

daily as (
    select
        date_local,
        avg(price_at_eur_mwh) as price_base_eur_mwh,
        avg(price_at_eur_mwh) filter (where is_peak_hour) as price_peak_eur_mwh,
        min(price_at_eur_mwh) as price_min,
        max(price_at_eur_mwh) as price_max,
        stddev_samp(price_at_eur_mwh) as price_std,
        sum(case when is_negative_price then 1 else 0 end) as n_negative_hours,
        max(hdd_18) as hdd_18,
        max(cdd_22) as cdd_22
    from hourly
    group by date_local
)

select
    daily.date_local,
    daily.price_base_eur_mwh,
    daily.price_peak_eur_mwh,
    daily.price_min,
    daily.price_max,
    daily.price_std,
    daily.n_negative_hours,
    weather.tavg_c,
    daily.hdd_18,
    daily.cdd_22
from daily
left join weather on daily.date_local = weather.date_local
