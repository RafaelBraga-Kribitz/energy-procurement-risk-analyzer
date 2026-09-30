-- Implements: SPEC-02 §6 DM-062 row-count boundary, DM-012
--
-- fct_price_hourly must have 8760 hours per local year (8784 in a leap
-- year), tolerant to +/-24 either side (one full day). Grouped by year_local
-- (dim_calendar-derived, DM-011 -- no timezone-conversion call here).
--
-- COMPLETE years (the mart holds both the local Jan-1 and the local Dec-31)
-- get the DM-062 +/-24 check. EDGE years (the calendar horizon's first/last
-- partial local year -- e.g. the forward-risk spine end, ING-110) cannot be
-- held to a full-year count, but they are NOT skipped: an edge year must
-- still have 1..expected_hours rows (more than a full year, or an empty
-- group, is always a defect). Same complete-year-within-the-window
-- convention as ADR-006's ingestion gates.

with counts as (
    select
        year_local,
        count(*) as n_hours,
        case
            when year_local % 4 = 0 and (year_local % 100 != 0 or year_local % 400 = 0)
            then 8784
            else 8760
        end as expected_hours,
        min(date_local) = make_date(year_local, 1, 1)
            and max(date_local) = make_date(year_local, 12, 31) as is_complete_year
    from {{ ref('fct_price_hourly') }}
    group by year_local
)

select *
from counts
where (is_complete_year and abs(n_hours - expected_hours) > 24)
    or (not is_complete_year and (n_hours < 1 or n_hours > expected_hours))
