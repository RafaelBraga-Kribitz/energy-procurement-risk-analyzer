-- Implements: SPEC-02 §5 fct_price_monthly, SG-14/ADR-011, DM-050
--
-- Local month-grain aggregation of fct_price_hourly. price_peak_eur_mwh /
-- price_offpeak_eur_mwh are means filtered by the ONE holiday-aware
-- `is_peak_hour` (dim_calendar, ADR-011) — never a separate Mon-Fri-08-20
-- rule that ignores holidays. oespi_base/oespi_peak are left-joined from
-- stg_oespi_monthly by matching year/month (ÖSPI's own peak convention may
-- differ from `is_peak_hour` — see LIMITATIONS.md §2 / ADR-011). No
-- timezone-conversion call (DM-011).

with hourly as (
    select
        year_local,
        month_local,
        price_at_eur_mwh,
        is_peak_hour,
        is_negative_price
    from {{ ref('fct_price_hourly') }}
),

oespi as (
    select
        extract(year from month_local)::integer as year_local,
        extract(month from month_local)::integer as month_local,
        oespi_base,
        oespi_peak
    from {{ ref('stg_oespi_monthly') }}
),

monthly as (
    select
        year_local,
        month_local,
        avg(price_at_eur_mwh) as price_base_eur_mwh,
        avg(price_at_eur_mwh) filter (where is_peak_hour) as price_peak_eur_mwh,
        avg(price_at_eur_mwh) filter (where not is_peak_hour) as price_offpeak_eur_mwh,
        sum(case when is_negative_price then 1 else 0 end) as n_negative_hours
    from hourly
    group by year_local, month_local
)

select
    monthly.year_local,
    monthly.month_local,
    monthly.price_base_eur_mwh,
    monthly.price_peak_eur_mwh,
    monthly.price_offpeak_eur_mwh,
    monthly.n_negative_hours,
    oespi.oespi_base,
    oespi.oespi_peak
from monthly
left join oespi
    on monthly.year_local = oespi.year_local
    and monthly.month_local = oespi.month_local
