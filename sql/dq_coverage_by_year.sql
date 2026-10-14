-- Data quality (ADR-020 §3): coverage and cleanliness of the inputs per year.
select
    dq.year_local as year,
    sum(dq.priced_hours_at) as priced_hours,
    sum(dq.expected_hours) as calendar_hours,
    round(100.0 * sum(dq.priced_hours_at) / sum(dq.expected_hours), 2) as coverage_pct,
    sum(dq.n_dst_days) as dst_days,
    sum(dq.n_hours_from_pt15m) as hours_from_15min_quarters,
    sum(dq.n_negative_hours) as negative_price_hours
from marts.fct_data_quality_monthly as dq
group by dq.year_local
order by dq.year_local
