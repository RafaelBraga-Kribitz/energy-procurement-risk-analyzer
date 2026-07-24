-- Implements: SPEC-02 §6 DM-062 row-count boundary
--
-- fct_price_hourly must have 8760 hours per local year (8784 in a leap
-- year), tolerant to +/-24 either side (one full day). Group by year_local
-- (dim_calendar-derived, DM-011 -- no timezone-conversion call here) and
-- flag any COMPLETE local year outside that boundary.
--
-- "Complete" excludes only the two calendar-horizon edges -- dim_calendar's
-- forward-risk horizon (SPEC-05) intentionally extends the spine past the
-- real ingested price window (and the real ingestion start may itself not
-- land exactly on a local Jan-1 00:00 boundary), so on the real local
-- build the very first/last year_local group can be a partial slice of
-- the calendar rather than a genuine missing-hours anomaly (same
-- complete-year-within-the-window convention as ADR-006's ingestion
-- gates). A year only counts as "complete" here if the mart itself
-- contains a row for both its local Jan-1 and its local Dec-31 -- this is
-- computed purely from the mart's own min/max date_local, not from any
-- external ingestion-window constant, so the CI fixture window (D-03,
-- fully bounded 2022-2024) is unaffected and every year in that window
-- still runs this check unmodified.

with counts as (
    select
        year_local,
        count(*) as n_hours,
        case
            when year_local % 4 = 0 and (year_local % 100 != 0 or year_local % 400 = 0)
            then 8784
            else 8760
        end as expected_hours,
        min(date_local) as min_date_local,
        max(date_local) as max_date_local
    from {{ ref('fct_price_hourly') }}
    group by year_local
),

complete_years as (
    select *
    from counts
    where min_date_local = make_date(year_local, 1, 1)
      and max_date_local = make_date(year_local, 12, 31)
)

select *
from complete_years
where abs(n_hours - expected_hours) > 24
