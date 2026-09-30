-- Implements: SPEC-02 §6 DM-064 reconciliation
--
-- fct_price_monthly.price_base_eur_mwh for 2022-08 (the crisis-peak month,
-- chosen in the spec text) must equal the mean of fct_price_hourly's
-- price_at_eur_mwh for that same month within a 0.01 tolerance -- guards
-- aggregation drift between the hourly and monthly marts. The month is
-- HARDCODED (2022, 8), deliberately not parametrized/derived, so the CI
-- fixture window (ADR-016, contiguous 2022-2024) runs this test
-- byte-identically to the real local build.
--
-- NULL-safe: a missing 2022-08 row in fct_price_monthly, or a NULL on either
-- side (no hourly prices), FAILS -- `abs(NULL - x) > 0.01` would otherwise
-- evaluate to NULL and pass silently.

with hourly_mean as (
    select avg(price_at_eur_mwh) as mean_price
    from {{ ref('fct_price_hourly') }}
    where year_local = 2022 and month_local = 8
),

monthly as (
    select price_base_eur_mwh
    from {{ ref('fct_price_monthly') }}
    where year_local = 2022 and month_local = 8
),

checked as (
    select
        (select max(price_base_eur_mwh) from monthly) as price_base_eur_mwh,
        (select max(mean_price) from hourly_mean) as mean_price,
        (select count(*) from monthly) as n_monthly_rows
)

select *
from checked
where n_monthly_rows != 1
    or price_base_eur_mwh is null
    or mean_price is null
    or abs(price_base_eur_mwh - mean_price) > 0.01
