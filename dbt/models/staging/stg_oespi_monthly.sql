-- Implements: DM-005
-- SPEC-02 §3 stg_oespi_monthly: monthly manually-transcribed OESPI price
-- index. Source `month` column is a "YYYY-MM" string (ING-101); parsed to
-- the first-of-month DATE grain key. No timezone-conversion call (DM-011).
select
    strptime(month, '%Y-%m')::date as month_local,
    oespi_base,
    oespi_peak
from {{ source('raw_manual', 'oespi_monthly') }}
