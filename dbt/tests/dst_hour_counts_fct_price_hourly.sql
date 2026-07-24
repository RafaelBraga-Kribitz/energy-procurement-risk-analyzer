-- Implements: SPEC-02 §6 DM-065 DST adjacency
--
-- fct_price_hourly must resolve the 2024 spring-forward/fall-back local
-- days via ts_utc + the dim_calendar-derived date_local -- never via a
-- model-layer timezone call (DM-011). 2024-03-31 (spring-forward) must have
-- exactly 23 local hours; 2024-10-27 (fall-back) must have exactly 25.
-- Both dates are HARDCODED per the spec text, deliberately not
-- parametrized/derived (D-03), so CI fixtures run this byte-identically to
-- the real local build.

with expected(date_local, expected_hours) as (
    values (date '2024-03-31', 23), (date '2024-10-27', 25)
),

actual as (
    select date_local, count(*) as n_hours
    from {{ ref('fct_price_hourly') }}
    where date_local in (date '2024-03-31', date '2024-10-27')
    group by date_local
)

select
    expected.date_local,
    expected.expected_hours,
    actual.n_hours
from expected
join actual using (date_local)
where actual.n_hours != expected.expected_hours
