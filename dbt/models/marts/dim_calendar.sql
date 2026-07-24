-- Implements: DM-011, SPEC-02 §4 (dim_calendar, grain: hour)
--
-- Single source of local calendar truth every mart joins on. Local
-- attributes (date_local, year_local, month_local, hour_local, dow_local,
-- is_weekend, is_holiday_at, is_peak_hour) are loaded VERBATIM from the
-- ING-110 calendar parquet — they are pre-computed by
-- epra.ingest.calendar/epra.common.timeutil and never re-derived with a
-- timezone-conversion function here (DM-011 forbids it at this layer).
--
-- season: Austrian energy-market convention — 'winter' covers Nov-Mar
-- (heating season), 'summer' covers Apr-Oct (SPEC-02 §4).
--
-- hdd_18/cdd_22: heating/cooling degree-days, computed once per local day
-- from stg_weather_graz_daily.tavg_c and left-joined on date_local so the
-- SAME daily value repeats across all 24 local hours of that day (SPEC-02
-- §4). Left join (not inner) keeps every calendar hour even on days
-- lacking a weather observation — degree-days are NULL rather than the
-- hour being dropped.

with calendar as (
    select
        ts_utc,
        date_local,
        year_local,
        month_local,
        hour_local,
        dow_local,
        is_weekend,
        is_holiday_at,
        is_peak_hour
    from {{ source('raw_calendar', 'calendar') }}
),

weather as (
    select
        date_local,
        tavg_c
    from {{ ref('stg_weather_graz_daily') }}
)

select
    calendar.ts_utc,
    calendar.date_local,
    calendar.year_local,
    calendar.month_local,
    calendar.hour_local,
    calendar.dow_local,
    calendar.is_weekend,
    calendar.is_holiday_at,
    calendar.is_peak_hour,
    case
        when calendar.month_local in (11, 12, 1, 2, 3) then 'winter'
        else 'summer'
    end as season,
    greatest(0, 18 - weather.tavg_c) as hdd_18,
    greatest(0, weather.tavg_c - 22) as cdd_22
from calendar
left join weather on calendar.date_local = weather.date_local
