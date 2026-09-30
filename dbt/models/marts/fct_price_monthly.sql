-- Implements: SPEC-02 §5 fct_price_monthly, SG-14/ADR-011, DM-050
--
-- Local month-grain aggregation of fct_price_hourly. price_peak_eur_mwh /
-- price_offpeak_eur_mwh are means filtered by the ONE holiday-aware
-- `is_peak_hour` (dim_calendar, ADR-011) — never a separate Mon-Fri-08-20
-- rule that ignores holidays. oespi_base/oespi_peak are left-joined from
-- stg_oespi_monthly by matching year/month (ÖSPI's own peak convention may
-- differ from `is_peak_hour` — see LIMITATIONS.md §2 / ADR-011). No
-- timezone-conversion call (DM-011).
--
-- Window (DM-050 "every month in the analysis window"): fct_price_hourly is
-- spined on dim_calendar, which runs past the data into the forward-risk
-- horizon (ING-110). Months outside [first, last] local month holding at
-- least one non-NULL AT price are therefore dropped here — a monthly price
-- mart must not carry forward months of NULL prices that look like data.
-- Months INSIDE that window are kept even if prices are sparse (gaps stay
-- visible as NULL/partial means, never filled — A-2).

with hourly as (
    select
        year_local,
        month_local,
        price_at_eur_mwh,
        is_peak_hour,
        is_negative_price
    from {{ ref('fct_price_hourly') }}
),

price_window as (
    select
        min(make_date(year_local, month_local, 1)) as first_month,
        max(make_date(year_local, month_local, 1)) as last_month
    from hourly
    where price_at_eur_mwh is not null
),

oespi as (
    select
        cast(extract(year from month_local) as integer) as year_local,
        cast(extract(month from month_local) as integer) as month_local,
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
        cast(count(*) filter (where is_negative_price) as bigint) as n_negative_hours
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
cross join price_window
left join oespi
    on monthly.year_local = oespi.year_local
    and monthly.month_local = oespi.month_local
where make_date(monthly.year_local, monthly.month_local, 1)
    between price_window.first_month and price_window.last_month
