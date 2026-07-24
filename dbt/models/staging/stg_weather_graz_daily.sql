-- Implements: DM-005
-- SPEC-02 §3 stg_weather_graz_daily: daily rename of GeoSphere Graz mean
-- temperature. GeoSphere's `date` column is already the LOCAL civil date
-- (not a UTC-derived date — see staging.yml description), so no timezone
-- conversion is performed or needed here (DM-011).
select
    date as date_local,
    tl_mittel_c as tavg_c
from {{ source('raw', 'geosphere_graz_daily') }}
