"""Strategy mart loaders and ST-101 volume alignment (M6).

Join consumer load to hourly AT prices, drop NULL-priced hours from volume
for every strategy (fair comparison). ``w_peak`` is read from the profile
SSOT producer file and never retyped.

Implements: ST-001, ST-101, ST-501, D-01, D-02.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from epra.common.config import REPO_ROOT, Settings
from epra.common.db import connect

logger = logging.getLogger(__name__)

SQL_PRICE_HOURLY = "select * from marts.fct_price_hourly"
SQL_PRICE_DAILY = "select * from marts.fct_price_daily"
SQL_PRICE_MONTHLY = "select * from marts.fct_price_monthly"
SQL_CONSUMER_LOAD = "select * from marts.fct_consumer_load_hourly"
SQL_CALENDAR = (
    "select ts_utc, date_local, hour_local, dow_local, is_holiday_at, "
    "year_local, month_local from marts.dim_calendar"
)

LOAD_COLS = ("ts_utc", "load_mwh")
PRICE_COLS = ("ts_utc", "price_at_eur_mwh", "year_local", "month_local")
CALENDAR_COLS = (
    "ts_utc",
    "date_local",
    "hour_local",
    "dow_local",
    "is_holiday_at",
    "year_local",
    "month_local",
)
STRATEGY_IDS: tuple[str, ...] = ("S1", "S2", "S3", "S4_30", "S4_50", "S4_70")
W_PEAK_KEY = "consumer_peak_share"


@dataclass(frozen=True)
class AlignedVolumes:
    """Hourly load+price with NULLs dropped; monthly volumes shared by all strategies.

    Implements: ST-101, ST-501.
    """

    hourly: pd.DataFrame
    monthly: pd.DataFrame
    dropped_hours: int


def processed_dir(settings: Settings) -> Path:
    path = settings.paths.data_processed
    return path if path.is_absolute() else REPO_ROOT / path


def _fetch(settings: Settings, sql: str) -> pd.DataFrame:
    """Run ``sql`` read-only; empty result raises with the SQL text.

    Implements: D-01.
    """
    con = connect(settings, read_only=True)
    try:
        frame = con.execute(sql).fetchdf()
    finally:
        con.close()
    if frame.empty:
        raise RuntimeError(f"SQL returned empty: {sql}")
    return frame


def load_price_hourly(settings: Settings) -> pd.DataFrame:
    """Load ``marts.fct_price_hourly``.

    Implements: ST-001, D-01.
    """
    return _fetch(settings, SQL_PRICE_HOURLY)


def load_price_daily(settings: Settings) -> pd.DataFrame:
    """Load ``marts.fct_price_daily``.

    Implements: ST-001, D-01.
    """
    return _fetch(settings, SQL_PRICE_DAILY)


def load_price_monthly(settings: Settings) -> pd.DataFrame:
    """Load ``marts.fct_price_monthly`` (includes ÖSPI columns).

    Implements: ST-001, D-01.
    """
    return _fetch(settings, SQL_PRICE_MONTHLY)


def load_consumer_load(settings: Settings) -> pd.DataFrame:
    """Load ``marts.fct_consumer_load_hourly``.

    Implements: ST-001, D-01.
    """
    return _fetch(settings, SQL_CONSUMER_LOAD)


def load_calendar(settings: Settings) -> pd.DataFrame:
    """Load ``marts.dim_calendar`` columns needed by ``build_profile``.

    Implements: ST-303, D-01.
    """
    return _fetch(settings, SQL_CALENDAR)


def _require_columns(frame: pd.DataFrame, cols: tuple[str, ...], name: str) -> None:
    missing = [col for col in cols if col not in frame.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


def _monthly_volume(hourly: pd.DataFrame) -> pd.DataFrame:
    if hourly.empty:
        return pd.DataFrame(columns=["year_local", "month_local", "volume_mwh"])
    return hourly.groupby(["year_local", "month_local"], as_index=False, sort=True).agg(
        volume_mwh=("load_mwh", "sum")
    )


def align_hourly(load: pd.DataFrame, prices: pd.DataFrame) -> AlignedVolumes:
    """Inner-join load to prices; drop NULL ``price_at_eur_mwh`` hours.

    Monthly ``volume_mwh`` is the sum of remaining ``load_mwh`` so every
    strategy prices the same volume (ST-101, ST-501).

    Implements: ST-101, ST-501, D-01.
    """
    _require_columns(load, LOAD_COLS, "load")
    _require_columns(prices, PRICE_COLS, "prices")
    merged = load.merge(prices, on="ts_utc", how="inner")
    n_null = int(merged["price_at_eur_mwh"].isna().sum())
    if n_null:
        logger.info("ST-101 dropped %s NULL price_at_eur_mwh hours", n_null)
    clean = merged.dropna(subset=["price_at_eur_mwh"]).copy()
    return AlignedVolumes(hourly=clean, monthly=_monthly_volume(clean), dropped_hours=n_null)


def volumes_for_strategies(
    monthly: pd.DataFrame, strategy_ids: tuple[str, ...] = STRATEGY_IDS
) -> pd.DataFrame:
    """Copy monthly volumes onto each ``strategy_id`` (identical by construction).

    Implements: ST-501.
    """
    parts = [monthly.assign(strategy_id=sid) for sid in strategy_ids]
    if not parts:
        return pd.DataFrame(columns=["year_local", "month_local", "volume_mwh", "strategy_id"])
    return pd.concat(parts, ignore_index=True)


def load_w_peak(settings: Settings) -> float:
    """Read ``consumer_peak_share`` from ``ssot_inputs_profile.parquet``.

    Implements: ST-102, D-02.
    """
    path = processed_dir(settings) / "ssot_inputs_profile.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"missing {path} (key {W_PEAK_KEY}; run `make profile` first)")
    frame = pd.read_parquet(path)
    rows = frame.loc[frame["key"] == W_PEAK_KEY]
    if rows.empty:
        raise KeyError(f"{W_PEAK_KEY} not in {path}")
    return float(rows.iloc[0]["value"])
