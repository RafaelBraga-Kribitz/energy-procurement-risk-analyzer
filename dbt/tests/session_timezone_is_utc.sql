-- Implements: DM-010 (ts_utc is UTC), ADR-014
--
-- dbt/profiles.yml pins the DuckDB session `TimeZone: UTC`. That pin is
-- load-bearing: staging's date_trunc('hour', ts_utc) on TIMESTAMPTZ
-- truncates in the SESSION zone, and ADR-014's reading of DM-010
-- ("TIMESTAMP (UTC)" satisfied by TIMESTAMPTZ) relies on it. If the pin is
-- ever dropped (DuckDB then defaults to the host zone), this test fails.

select current_setting('TimeZone') as session_timezone
where current_setting('TimeZone') != 'UTC'
