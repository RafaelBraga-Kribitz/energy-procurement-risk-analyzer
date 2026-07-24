-- Implements: SPEC-02 §5 fct_price_hourly, SG-05, DM-050
--
-- Hour-grain price mart — the SG-05 frozen enumeration: AT/DE-LU hourly
-- prices, their spread, AT load, a negative-price flag, plus ALL
-- dim_calendar attributes (date_local, year_local, month_local,
-- hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour, season,
-- hdd_18, cdd_22).
--
-- dim_calendar is the SPINE: every calendar hour is present via a left
-- join of the staging price/load views onto dim_calendar, so ts_utc is
-- never NULL (DM-050) even on hours a source dataset happens to be
-- missing. No timezone-conversion call — every local attribute comes
-- only from the dim_calendar join (DM-011).

with spine as (
    select
        ts_utc,
        date_local,
        year_local,
        month_local,
        hour_local,
        dow_local,
        is_weekend,
        is_holiday_at,
        is_peak_hour,
        season,
        hdd_18,
        cdd_22
    from {{ ref('dim_calendar') }}
),

prices_at as (
    select ts_utc, price_eur_mwh as price_at_eur_mwh
    from {{ ref('stg_prices_at_hourly') }}
),

prices_delu as (
    select ts_utc, price_eur_mwh as price_delu_eur_mwh
    from {{ ref('stg_prices_delu_hourly') }}
),

load_at as (
    select ts_utc, load_mw as load_at_mw
    from {{ ref('stg_load_at_hourly') }}
)

select
    spine.ts_utc,
    prices_at.price_at_eur_mwh,
    prices_delu.price_delu_eur_mwh,
    prices_at.price_at_eur_mwh - prices_delu.price_delu_eur_mwh as spread_at_delu_eur_mwh,
    load_at.load_at_mw,
    prices_at.price_at_eur_mwh < 0 as is_negative_price,
    spine.date_local,
    spine.year_local,
    spine.month_local,
    spine.hour_local,
    spine.dow_local,
    spine.is_weekend,
    spine.is_holiday_at,
    spine.is_peak_hour,
    spine.season,
    spine.hdd_18,
    spine.cdd_22
from spine
left join prices_at on spine.ts_utc = prices_at.ts_utc
left join prices_delu on spine.ts_utc = prices_delu.ts_utc
left join load_at on spine.ts_utc = load_at.ts_utc
