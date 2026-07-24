-- Implements: SPEC-02 §6 DM-064 reconciliation
--
-- fct_price_monthly.price_base_eur_mwh for 2022-08 (the crisis-peak month,
-- chosen in the spec text) must equal the mean of fct_price_hourly's
-- price_at_eur_mwh for that same month within a 0.01 tolerance -- guards
-- aggregation drift between the hourly and monthly marts. The month is
-- HARDCODED (2022, 8), deliberately not parametrized/derived, so CI
-- fixtures (D-03, contiguous 2022-2024 synthetic window) run this test
-- byte-identically to the real local build.

with hourly_mean as (
    select avg(price_at_eur_mwh) as mean_price
    from {{ ref('fct_price_hourly') }}
    where year_local = 2022 and month_local = 8
),

monthly as (
    select price_base_eur_mwh
    from {{ ref('fct_price_monthly') }}
    where year_local = 2022 and month_local = 8
)

select
    monthly.price_base_eur_mwh,
    hourly_mean.mean_price
from monthly, hourly_mean
where abs(monthly.price_base_eur_mwh - hourly_mean.mean_price) > 0.01
