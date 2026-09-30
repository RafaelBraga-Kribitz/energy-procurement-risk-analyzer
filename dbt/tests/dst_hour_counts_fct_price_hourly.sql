-- Implements: SPEC-02 §6 DM-065 DST adjacency, DM-012
--
-- fct_price_hourly must resolve the spring-forward/fall-back local days via
-- ts_utc + the dim_calendar-derived date_local -- never via a model-layer
-- timezone call (DM-011). Expected days:
--   * the two spec-named 2024 days, HARDCODED per DM-065 (2024-03-31 = 23
--     local hours, 2024-10-27 = 25), so CI fixtures run this byte-identically
--     to the real local build;
--   * plus the EU transition days (last Sunday of March = 23 h, last Sunday
--     of October = 25 h) of every COMPLETE local year in the mart (a year is
--     complete when the mart holds both its local Jan-1 and Dec-31). Pure
--     date arithmetic, no timezone function.
-- An expected day that is ABSENT from the mart is a failure (left join from
-- the expected set) -- a missing DST day must never pass silently.

with years as (
    select year_local
    from {{ ref('fct_price_hourly') }}
    group by year_local
    having min(date_local) = make_date(year_local, 1, 1)
        and max(date_local) = make_date(year_local, 12, 31)
),

derived as (
    -- DuckDB dayofweek(): Sunday = 0, so d - dayofweek(d) is the last
    -- Sunday on or before d.
    select
        make_date(year_local, 3, 31) - cast(dayofweek(make_date(year_local, 3, 31)) as integer)
            as date_local,
        23 as expected_hours
    from years
    union all
    select
        make_date(year_local, 10, 31) - cast(dayofweek(make_date(year_local, 10, 31)) as integer),
        25
    from years
),

expected as (
    select date_local, expected_hours from derived
    union
    select * from (values (date '2024-03-31', 23), (date '2024-10-27', 25)) as t (date_local, expected_hours)
),

actual as (
    select date_local, count(*) as n_hours
    from {{ ref('fct_price_hourly') }}
    where date_local in (select date_local from expected)
    group by date_local
)

select
    expected.date_local,
    expected.expected_hours,
    actual.n_hours
from expected
left join actual using (date_local)
where actual.n_hours is null
    or actual.n_hours != expected.expected_hours
