"""Shared pytest fixtures for ingest tests — tmp_path-backed Settings and the
committed ENTSO-E fixture directory.

Mirrors the `tmp_path` + `model_copy` pattern already used in
`tests/unit/test_logging_and_db.py`: ingest and validation tests never write
into the repo's real `data/raw/`, `data/cache/`, or `reports/` trees — every
fixture here redirects those paths under pytest's `tmp_path` so tests are
isolated and ING-003 idempotency (same input -> same output, no dupes) is
actually checkable against a throwaway directory instead of shared state.

No production ingest logic lives here — infrastructure only (Wave 0, 02-01).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from epra.common.config import REPO_ROOT, Settings, load_settings

#: Directory of committed ENTSO-E XML/parquet fixtures (ING-070, T1.03a).
_ENTSOE_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "entsoe"

_ENTSOE_FIXTURES_README = """# ENTSO-E test fixtures

Committed XML/parquet samples for `tests/test_raw_contracts.py` and the
ENTSO-E parser unit tests (ING-070, T1.03a). Expected coverage, each file
<= 200 rows and generated once from real ENTSO-E pulls so CI never needs
network access:

- PT60M day-ahead prices (AT and DE-LU)
- PT15M day-ahead prices (post SDAC 15-min switch)
- curveType A03 (forward-fill within period, ING-063)
- a DST transition day (last Sunday of March / October, ING-080)
- AT actual load (PT15M)
- AT generation per type, long format (ING-032)
- an `Acknowledgement_MarketDocument` (no-data) response

Populate this directory when implementing the fetch/parse plans; do not
commit synthetic data that isn't a fixture-worthy sample of a real response.
"""


def _ensure_entsoe_fixtures_dir() -> Path:
    """Create `tests/fixtures/entsoe/` with a placeholder README if it's empty.

    Runs at module import (collection) time so the directory exists on disk
    even before any fixture files are committed by later ingest plans.
    """
    _ENTSOE_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    readme = _ENTSOE_FIXTURES_DIR / "README.md"
    other_files = [p for p in _ENTSOE_FIXTURES_DIR.iterdir() if p.name != "README.md"]
    if not readme.exists() and not other_files:
        readme.write_text(_ENTSOE_FIXTURES_README, encoding="utf-8")
    return _ENTSOE_FIXTURES_DIR


_ensure_entsoe_fixtures_dir()


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    """`Settings` with `data_raw`, `data_cache`, `data_manual`, and `reports`
    redirected to `tmp_path`.

    Ingest and validation tests inject this instead of the real `Settings` so
    parquet writes, cache files, validation reports, and (03-06) the ÖSPI
    manual CSV never touch the repo's real `data/` or `reports/` trees
    (mirrors `test_db_connect_creates_warehouse` in
    `tests/unit/test_logging_and_db.py`). Redirecting `data_manual` too keeps
    `run_gates` aggregate tests deterministic regardless of whether the real
    `data/manual/oespi_monthly.csv` (the 03-06 human checkpoint) has been
    committed in the working tree yet -- a test must never pass or fail
    depending on that external, human-driven file's presence.
    """
    settings = load_settings()
    paths = settings.paths.model_copy(
        update={
            "data_raw": tmp_path / "data" / "raw",
            "data_cache": tmp_path / "data" / "cache",
            "data_manual": tmp_path / "data" / "manual",
            "reports": tmp_path / "reports",
        }
    )
    return settings.model_copy(update={"paths": paths})


@pytest.fixture
def entsoe_fixtures_dir() -> Path:
    """Path to the committed ENTSO-E fixture directory (ING-070, T1.03a)."""
    return _ENTSOE_FIXTURES_DIR


# ------------------------------------------------- synthetic warehouse (M5/M6)

#: Priced window of the synthetic warehouse; the calendar runs one year further
#: so the forward-risk window has calendar + profile rows (LP-003, SG-15).
SYNTH_DATA_END = date(2025, 12, 31)
SYNTH_CALENDAR_END = date(2026, 12, 31)


def _synthetic_hourly(seed: int = 7) -> pd.DataFrame:
    """Seeded hourly marts rows with three volatility tiers: calm 2019-2020,
    crisis 2021-09..2023-06, elevated otherwise; NULL prices after the data end."""
    from epra.ingest.calendar import calendar_frame

    rng = np.random.default_rng(seed)
    cal = calendar_frame(date(2019, 1, 1), SYNTH_CALENDAR_END)
    days = pd.to_datetime(pd.Series(cal["date_local"].unique()))
    crisis = (days >= pd.Timestamp("2021-09-01")) & (days <= pd.Timestamp("2023-06-30"))
    calm = days < pd.Timestamp("2021-01-01")
    noise = np.where(crisis, 45.0, np.where(calm, 2.0, 10.0))
    level = np.where(crisis, 220.0, np.where(calm, 45.0, 90.0))
    daily = pd.Series(level + rng.normal(0, 1.0, len(days)) * noise, index=days.dt.date)
    month, hour = cal["month_local"].to_numpy(), cal["hour_local"].to_numpy()
    solar = ((month >= 4) & (month <= 9) & (hour >= 11) & (hour <= 14)).astype(float) * 60.0
    at = daily.reindex(cal["date_local"]).to_numpy() - solar + rng.normal(0, 4.0, len(cal))
    delu = at - rng.normal(3.0, 2.0, len(cal))
    tavg = 10 - 10 * np.cos(2 * np.pi * (days.dt.dayofyear.to_numpy() - 15) / 365)
    hdd = pd.Series(np.clip(18 - tavg, 0, None), index=days.dt.date)
    load = 7000 + 60 * hdd.reindex(cal["date_local"]).to_numpy() + rng.normal(0, 100, len(cal))
    future = (pd.to_datetime(cal["date_local"]) > pd.Timestamp(SYNTH_DATA_END)).to_numpy()
    at = np.where(future, np.nan, at)
    delu = np.where(future, np.nan, delu)
    return cal.assign(
        price_at_eur_mwh=at,
        price_delu_eur_mwh=delu,
        spread_at_delu_eur_mwh=at - delu,
        load_at_mw=np.where(future, np.nan, load),
        is_negative_price=at < 0,
        hdd_18=hdd.reindex(cal["date_local"]).to_numpy(),
    )


def _monthly_mart(hourly: pd.DataFrame) -> pd.DataFrame:
    priced = hourly.dropna(subset=["price_at_eur_mwh"])
    monthly = (
        priced.groupby(["year_local", "month_local"])["price_at_eur_mwh"]
        .mean()
        .rename("price_base_eur_mwh")
        .reset_index()
    )
    oespi = pd.read_csv(REPO_ROOT / "data" / "manual" / "oespi_monthly.csv")
    month = pd.to_datetime(oespi["month"])
    oespi = oespi.assign(year_local=month.dt.year, month_local=month.dt.month)
    return monthly.merge(
        oespi[["year_local", "month_local", "oespi_base", "oespi_peak"]],
        on=["year_local", "month_local"],
        how="left",
    )


@pytest.fixture(scope="session")
def synthetic_warehouse(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    """Throwaway DuckDB with SPEC-02-shaped marts + the real SPEC-03 profile.

    Built directly from pandas (no dbt) so analytics/strategy tests run
    hermetically; the committed ÖSPI CSV supplies the index columns.
    """
    from epra.consumer import profile

    root = tmp_path_factory.mktemp("warehouse")
    base = load_settings()
    paths = base.paths.model_copy(
        update={
            "warehouse": root / "epra.duckdb",
            "reports": root / "reports",
            "data_processed": root / "processed",
            "data_raw": root / "raw",
        }
    )
    settings = base.model_copy(update={"paths": paths})
    hourly = _synthetic_hourly()
    cal_cols = [
        "ts_utc",
        "date_local",
        "year_local",
        "month_local",
        "hour_local",
        "dow_local",
        "is_weekend",
        "is_holiday_at",
        "is_peak_hour",
    ]
    (paths.data_raw / "calendar").mkdir(parents=True)
    hourly[cal_cols].to_parquet(paths.data_raw / "calendar" / "calendar.parquet", index=False)
    profile.run(settings)
    daily = (
        hourly.groupby("date_local")
        .agg(price_base_eur_mwh=("price_at_eur_mwh", "mean"), hdd_18=("hdd_18", "first"))
        .reset_index()
    )
    con = duckdb.connect(str(paths.warehouse))
    con.execute("set TimeZone = 'UTC'")
    con.execute("create schema marts")
    for name, frame in (
        ("fct_price_hourly", hourly),
        ("dim_calendar", hourly[cal_cols]),
        ("fct_price_daily", daily),
        ("fct_price_monthly", _monthly_mart(hourly)),
    ):
        con.register("frame", frame)
        con.execute(f"create table marts.{name} as select * from frame")
        con.unregister("frame")
    hourly_load = profile.output_paths(settings, "styriametal_v1")[0].as_posix()
    con.execute(
        "create table marts.fct_consumer_load_hourly as "
        f"select ts_utc, load_mwh from read_parquet('{hourly_load}')"
    )
    con.close()
    return settings


@pytest.fixture(scope="session")
def simulated_warehouse(synthetic_warehouse: Settings) -> Settings:
    """The synthetic warehouse after A1/A2/A3 analytics and the M6 simulator ran.

    The strategies entry point must exit 0, i.e. ST-602 holds on this market.
    """
    import epra.strategies.__main__ as entry
    from epra.analytics import descriptive, regimes, spread

    descriptive.run(synthetic_warehouse)
    spread.run(synthetic_warehouse)
    regimes.run(synthetic_warehouse)
    patch = pytest.MonkeyPatch()
    patch.setattr(entry, "load_settings", lambda: synthetic_warehouse)
    try:
        assert entry.main([]) == 0
    finally:
        patch.undo()
    return synthetic_warehouse
