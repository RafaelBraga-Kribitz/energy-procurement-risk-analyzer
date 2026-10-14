"""Simulator inputs pulled from the DuckDB marts as readable SQL (ST-001).

Strategy costs are computed in Python (ST-001: dbt never computes them), but
everything they are computed FROM is selected here in plain SQL with explicit
joins and columns, so a reviewer can read the inputs without the Python:

- monthly spot cost + priced volume of the consumer (S1 leg, ST-101 drop rule);
- 2019 reference statistics for the calibration anchors (ST-201..203);
- the monthly ÖSPI series (S2/S3);
- hourly prices and target-month load by (day, hour_local) for the forward
  bootstrap (ST-401 step 3).

Implements: ST-001, ST-101 (NULL-price hours dropped from cost AND volume).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from epra.common.config import Settings
from epra.common.db import read_sql as run_sql
from epra.consumer.profile import output_paths

MAIN_PROFILE = "styriametal_v1"
FLAT_PROFILE = "flat_baseload"

MONTHLY_SPOT_SQL = """
-- ST-101: hours without an AT price are dropped from BOTH volume and cost, so
-- every strategy prices exactly the same volume (ST-501).
with consumer_hours as (
    select
        load.ts_utc,
        load.load_mwh
    from {load_source} as load
),

priced_hours as (
    select
        cal.year_local,
        cal.month_local,
        consumer_hours.load_mwh,
        price.price_at_eur_mwh
    from consumer_hours
    inner join marts.dim_calendar as cal
        on consumer_hours.ts_utc = cal.ts_utc
    inner join marts.fct_price_hourly as price
        on consumer_hours.ts_utc = price.ts_utc
)

select
    year_local,
    month_local,
    sum(load_mwh) filter (where price_at_eur_mwh is not null) as volume_mwh,
    sum(load_mwh * price_at_eur_mwh) as spot_cost_eur,
    count(*) filter (where price_at_eur_mwh is null) as dropped_hours,
    count(*) filter (where price_at_eur_mwh is not null) as priced_hours
from priced_hours
group by year_local, month_local
having count(*) filter (where price_at_eur_mwh is not null) > 0
order by year_local, month_local
"""

REFERENCE_YEAR_SQL = """
-- ST-201/202 inputs for the reference year: the consumer's realized spot cost
-- and volume, and the market's all-hours and peak-hours mean price.
select
    sum(load.load_mwh * price.price_at_eur_mwh) as consumer_cost_eur,
    sum(load.load_mwh) as consumer_volume_mwh,
    avg(price.price_at_eur_mwh) as mean_price_all_hours_eur_mwh,
    avg(price.price_at_eur_mwh) filter (where cal.is_peak_hour) as mean_price_peak_eur_mwh
from {load_source} as load
inner join marts.dim_calendar as cal
    on load.ts_utc = cal.ts_utc
inner join marts.fct_price_hourly as price
    on load.ts_utc = price.ts_utc
where cal.year_local = {year}
  and price.price_at_eur_mwh is not null
"""

OESPI_SQL = """
-- ÖSPI per priced month. Reading it from the monthly price mart makes the
-- data horizon one horizon: an index month counts as "observed" (ST-402) only
-- when its spot month is in the warehouse too.
select
    fpm.year_local,
    fpm.month_local,
    fpm.oespi_base,
    fpm.oespi_peak
from marts.fct_price_monthly as fpm
where fpm.oespi_base is not null
order by fpm.year_local, fpm.month_local
"""

HOURLY_PRICE_SQL = """
-- ST-401 pool: every priced hour keyed by local (year, month, day, hour).
select
    cal.year_local,
    cal.month_local,
    day(cal.date_local) as day_local,
    cal.hour_local,
    cal.is_weekend or cal.is_holiday_at as is_weekend_or_holiday,
    price.price_at_eur_mwh
from marts.fct_price_hourly as price
inner join marts.dim_calendar as cal
    on price.ts_utc = cal.ts_utc
where price.price_at_eur_mwh is not null
order by price.ts_utc
"""

TARGET_LOAD_SQL = """
-- ST-402: consumer volume of the forward months from the SPEC-03 profile.
select
    cal.year_local,
    cal.month_local,
    day(cal.date_local) as day_local,
    cal.hour_local,
    cal.is_weekend or cal.is_holiday_at as is_weekend_or_holiday,
    load.load_mwh
from {load_source} as load
inner join marts.dim_calendar as cal
    on load.ts_utc = cal.ts_utc
where make_date(cal.year_local, cal.month_local, 1)
      between date '{first}' and date '{last}'
order by load.ts_utc
"""


def load_source(settings: Settings, profile_name: str) -> str:
    """SQL relation holding ``ts_utc, load_mwh`` for ``profile_name``.

    The main profile is read through its mart; the sensitivity profile has no
    mart (SPEC-02 §5 lists one), so it is read from its LP-030 parquet.
    """
    if profile_name == MAIN_PROFILE:
        return "marts.fct_consumer_load_hourly"
    path: Path = output_paths(settings, profile_name)[0]
    return f"read_parquet('{path.as_posix()}')"


@dataclass(frozen=True)
class ReferenceStats:
    """Reference-year (2019) aggregates for the ST-201/202 anchors."""

    consumer_cost_eur: float
    consumer_volume_mwh: float
    mean_price_all_hours_eur_mwh: float
    mean_price_peak_eur_mwh: float


def monthly_spot(settings: Settings, profile_name: str) -> pd.DataFrame:
    """Per local month: priced ``volume_mwh``, ``spot_cost_eur``, dropped hours."""
    sql = MONTHLY_SPOT_SQL.format(load_source=load_source(settings, profile_name))
    return run_sql(settings, sql)


def reference_stats(settings: Settings, profile_name: str, year: int) -> ReferenceStats:
    """ST-201/202 inputs for ``year`` (raises if the year has no priced hours)."""
    sql = REFERENCE_YEAR_SQL.format(load_source=load_source(settings, profile_name), year=year)
    row = run_sql(settings, sql).iloc[0]
    if pd.isna(row["consumer_volume_mwh"]):
        raise ValueError(f"reference year {year} has no priced hours — anchors undefined")
    return ReferenceStats(**{k: float(row[k]) for k in ReferenceStats.__dataclass_fields__})


def oespi_monthly(settings: Settings) -> pd.DataFrame:
    """``year_local, month_local, oespi_base, oespi_peak`` (index points, T-5)."""
    return run_sql(settings, OESPI_SQL)


def hourly_prices(settings: Settings) -> pd.DataFrame:
    """All priced hours keyed by local year/month/day/hour (ST-401 pool)."""
    return run_sql(settings, HOURLY_PRICE_SQL)


def target_load(settings: Settings, profile_name: str, first: str, last: str) -> pd.DataFrame:
    """Hourly consumer load for months ``first``..``last`` (ISO first-of-month dates)."""
    sql = TARGET_LOAD_SQL.format(
        load_source=load_source(settings, profile_name), first=first, last=last
    )
    return run_sql(settings, sql)


LAST_PRICED_MONTH_SQL = """
select
    fpm.year_local,
    fpm.month_local
from marts.fct_price_monthly as fpm
where fpm.price_base_eur_mwh is not null
order by fpm.year_local desc, fpm.month_local desc
limit 1
"""


def last_priced_month(settings: Settings) -> tuple[int, int]:
    """Latest complete data month (Charter §4.3 anchor of the forward window)."""
    row = run_sql(settings, LAST_PRICED_MONTH_SQL).iloc[0]
    return int(row["year_local"]), int(row["month_local"])
