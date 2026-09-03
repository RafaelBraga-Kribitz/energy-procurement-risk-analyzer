"""T6.01 ST-101 aligner tests — NULL drop, shared volume, w_peak loader.

Implements: ST-101, ST-501, D-01, D-02.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from epra.common.config import Settings
from epra.common.db import connect
from epra.strategies import align


def _hour(i: int) -> pd.Timestamp:
    return pd.Timestamp(f"2022-01-01 {i:02d}:00:00", tz="UTC")


def _load_prices(
    *, n_hours: int = 6, null_hours: tuple[int, ...] = ()
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ts = [_hour(i) for i in range(n_hours)]
    load = pd.DataFrame({"ts_utc": ts, "load_mwh": [1.0] * n_hours})
    prices = pd.DataFrame(
        {
            "ts_utc": ts,
            "price_at_eur_mwh": [None if i in null_hours else 10.0 + i for i in range(n_hours)],
            "year_local": [2022] * n_hours,
            "month_local": [1] * n_hours,
        }
    )
    return load, prices


def test_three_null_hours_drop_from_shared_monthly_volume(caplog: pytest.LogCaptureFixture) -> None:
    load, prices = _load_prices(null_hours=(1, 3, 5))
    caplog.set_level(logging.INFO)
    aligned = align.align_hourly(load, prices)
    assert aligned.dropped_hours == 3
    assert len(aligned.hourly) == 3
    assert float(aligned.monthly["volume_mwh"].iloc[0]) == 3.0
    broadcast = align.volumes_for_strategies(aligned.monthly)
    vols = broadcast.groupby("strategy_id")["volume_mwh"].sum()
    assert set(vols.index) == set(align.STRATEGY_IDS)
    assert vols.nunique() == 1
    assert float(vols.iloc[0]) == 3.0
    assert "ST-101 dropped 3" in caplog.text


def test_align_requires_columns() -> None:
    with pytest.raises(ValueError, match="load missing"):
        align.align_hourly(pd.DataFrame({"ts_utc": []}), pd.DataFrame())


def test_load_price_hourly_raises_on_empty(tmp_settings: Settings) -> None:
    con = connect(tmp_settings, read_only=False)
    try:
        con.execute("create schema marts")
        con.execute(
            "create table marts.fct_price_hourly (ts_utc timestamp, price_at_eur_mwh double)"
        )
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="SQL returned empty"):
        align.load_price_hourly(tmp_settings)


def test_load_w_peak_reads_profile_parquet(tmp_settings: Settings) -> None:
    root = align.processed_dir(tmp_settings)
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "key": "consumer_peak_share",
                "value": 0.486,
                "unit": "fraction",
                "tag": "CALIBRATED",
                "produced_by": "epra.consumer.profile",
            }
        ]
    ).to_parquet(root / "ssot_inputs_profile.parquet", index=False)
    assert align.load_w_peak(tmp_settings) == pytest.approx(0.486)


def test_load_w_peak_missing_file_names_path(tmp_settings: Settings) -> None:
    with pytest.raises(FileNotFoundError, match=r"ssot_inputs_profile\.parquet"):
        align.load_w_peak(tmp_settings)


def test_load_w_peak_missing_key(tmp_settings: Settings) -> None:
    root = align.processed_dir(tmp_settings)
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"key": "other", "value": 1.0, "unit": "1", "tag": "CALIBRATED", "produced_by": "t"}]
    ).to_parquet(root / "ssot_inputs_profile.parquet", index=False)
    with pytest.raises(KeyError, match="consumer_peak_share"):
        align.load_w_peak(tmp_settings)
