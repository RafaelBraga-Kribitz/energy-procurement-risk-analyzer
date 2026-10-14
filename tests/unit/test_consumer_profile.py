"""SPEC-03 §7 golden + property tests for the consumer load profile (M4).

Implements tests for: LP-001..004, LP-020, LP-021, LP-030, LP-034, LP-040..042.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from epra.common.config import REPO_ROOT, ConsumerProfileCfg, Settings, load_consumer_profile
from epra.common.ssot import read_ssot_rows
from epra.common.timeutil import VIENNA
from epra.consumer import profile
from epra.ingest.calendar import calendar_frame

GOLDEN_SHA = REPO_ROOT / "tests" / "golden" / "consumer_load_2023.sha256"
TOL_MWH = 0.01


@pytest.fixture(scope="module")
def cfg() -> ConsumerProfileCfg:
    return load_consumer_profile()


@pytest.fixture(scope="module")
def cal_2022_2024() -> pd.DataFrame:
    return calendar_frame(date(2022, 1, 1), date(2024, 12, 31))


@pytest.fixture(scope="module")
def prof(cal_2022_2024: pd.DataFrame, cfg: ConsumerProfileCfg) -> pd.DataFrame:
    return profile.build_profile(cal_2022_2024, cfg)


def _local(df: pd.DataFrame) -> pd.Series:
    local: pd.Series = df["ts_utc"].dt.tz_convert(VIENNA)
    return local


def _year(df: pd.DataFrame, year: int) -> tuple[pd.DataFrame, pd.Series]:
    local = _local(df)
    mask = local.dt.year == year
    return df.loc[mask], local.loc[mask]


# ------------------------------------------------------------------ LP-040 golden


def test_lp040a_annual_sum_exact(prof: pd.DataFrame) -> None:
    for year in (2022, 2023, 2024):
        rows, _ = _year(prof, year)
        assert abs(rows["load_mwh"].sum() - 50_000.0) <= TOL_MWH


def test_lp040b_weekday_afternoon_vs_sunday_night_ratio(prof: pd.DataFrame) -> None:
    rows, local = _year(prof, 2023)
    weekday_14 = rows.loc[(local.dt.hour == 14) & (local.dt.dayofweek < 5), "load_mwh"].mean()
    sunday_03 = rows.loc[(local.dt.hour == 3) & (local.dt.dayofweek == 6), "load_mwh"].mean()
    assert 2.8 <= weekday_14 / sunday_03 <= 3.6


def test_lp040c_august_below_july(prof: pd.DataFrame) -> None:
    rows, local = _year(prof, 2023)
    by_month = rows.groupby(local.dt.month)["load_mwh"].sum()
    assert by_month[8] < by_month[7]


def test_lp040d_christmas_days_identical(prof: pd.DataFrame) -> None:
    rows, local = _year(prof, 2023)
    dec25 = rows.loc[(local.dt.month == 12) & (local.dt.day == 25), "load_mwh"].to_numpy()
    dec26 = rows.loc[(local.dt.month == 12) & (local.dt.day == 26), "load_mwh"].to_numpy()
    np.testing.assert_array_equal(dec25, dec26)


def test_lp040_golden_checksum_bit_stable(prof: pd.DataFrame) -> None:
    assert profile.year_checksum(prof, 2023) == GOLDEN_SHA.read_text(encoding="utf-8").strip()


def test_lp042_changing_yaml_breaks_checksum(
    cal_2022_2024: pd.DataFrame, cfg: ConsumerProfileCfg, prof: pd.DataFrame
) -> None:
    altered = profile.build_profile(
        cal_2022_2024, cfg.model_copy(update={"annual_consumption_mwh": 50_001.0})
    )
    assert profile.year_checksum(altered, 2023) != profile.year_checksum(prof, 2023)


def test_lp001_deterministic(cal_2022_2024: pd.DataFrame, cfg: ConsumerProfileCfg) -> None:
    first = profile.build_profile(cal_2022_2024, cfg)
    second = profile.build_profile(cal_2022_2024, cfg)
    pd.testing.assert_frame_equal(first, second)


# ------------------------------------------------------------- LP-041 properties


def test_lp041_no_negative_no_null_every_hour_once(
    prof: pd.DataFrame, cal_2022_2024: pd.DataFrame
) -> None:
    assert (prof["load_mwh"] >= 0).all()
    assert not prof.isna().any().any()
    assert len(prof) == len(cal_2022_2024)
    assert prof["ts_utc"].is_unique


@pytest.mark.parametrize(("day", "hours"), [("2024-03-31", 23), ("2024-10-27", 25)])
def test_lp041_dst_days(prof: pd.DataFrame, day: str, hours: int) -> None:
    assert (_local(prof).dt.date == date.fromisoformat(day)).sum() == hours


# ------------------------------------------------------------ calendar rules


def test_maintenance_week_is_first_full_week_of_august(cfg: ConsumerProfileCfg) -> None:
    days = profile.maintenance_dates([2023, 2024], cfg)
    assert min(d for d in days if d.year == 2023) == date(2023, 8, 7)  # 2023-08-01 is a Tue
    assert min(d for d in days if d.year == 2024) == date(2024, 8, 5)
    assert len(days) == 14


def test_unknown_maintenance_rule_rejected(cfg: ConsumerProfileCfg) -> None:
    bad = cfg.model_copy(update={"maintenance": cfg.maintenance.model_copy(update={"rule": "x"})})
    with pytest.raises(ValueError, match="maintenance rule"):
        profile.maintenance_dates([2023], bad)


def test_holiday_uses_weekend_shape(cfg: ConsumerProfileCfg) -> None:
    # 2023-05-01 (Mon, Staatsfeiertag) vs 2023-05-07 (Sun): same shape and month.
    cal = calendar_frame(date(2023, 5, 1), date(2023, 5, 7))
    w = profile.raw_weights(cal, cfg)
    dates = pd.to_datetime(cal["date_local"])
    np.testing.assert_allclose(w[dates == "2023-05-01"], w[dates == "2023-05-07"])


def test_shutdown_spans_new_year_without_double_dampening(cfg: ConsumerProfileCfg) -> None:
    cal = calendar_frame(date(2023, 12, 23), date(2024, 1, 2))
    w = profile.raw_weights(cal, cfg)
    dates = pd.to_datetime(cal["date_local"])
    flat = cfg.day_shapes["shutdown"][0]
    assert np.allclose(w[dates == "2024-01-01"], flat * cfg.seasonal_factors[1])
    assert np.allclose(w[dates == "2023-12-24"], flat * cfg.seasonal_factors[12])
    assert not np.allclose(w[dates == "2024-01-02"], flat * cfg.seasonal_factors[1])


# --------------------------------------------------- LP-034 / LP-021 / LP-030


def test_lp034_partial_year_matches_full_year_months(cfg: ConsumerProfileCfg) -> None:
    full = profile.monthly_volumes(
        profile.build_profile(calendar_frame(date(2026, 1, 1), date(2026, 12, 31)), cfg)
    )
    half = profile.monthly_volumes(
        profile.build_profile(calendar_frame(date(2026, 1, 1), date(2026, 6, 30)), cfg)
    )
    np.testing.assert_allclose(half["volume_mwh"], full["volume_mwh"].head(6), atol=1e-9)


def test_lp021_monthly_volumes_sum_to_annual(prof: pd.DataFrame) -> None:
    monthly = profile.monthly_volumes(prof)
    assert list(monthly.columns) == profile.MONTHLY_COLUMNS
    assert len(monthly) == 36
    annual = monthly.groupby("year_local")["volume_mwh"].sum()
    assert np.allclose(annual, 50_000.0, atol=TOL_MWH)


def test_lp030_flat_baseload_same_volume_flat_shape(
    cal_2022_2024: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    flat = profile.build_profile(cal_2022_2024, profile.flat_baseload_config(cfg))
    rows, _ = _year(flat, 2023)
    assert abs(rows["load_mwh"].sum() - 50_000.0) <= TOL_MWH
    assert np.allclose(rows["load_mwh"], 50_000.0 / 8760)


def test_lp020_peak_share_in_plausible_band(
    prof: pd.DataFrame, cal_2022_2024: pd.DataFrame
) -> None:
    assert 0.42 <= profile.peak_share(prof, cal_2022_2024) <= 0.50


# ----------------------------------------------------------------- run / CLI


def test_run_writes_outputs_and_ssot_row(tmp_settings: Settings, tmp_path: Path) -> None:
    settings = tmp_settings.model_copy(
        update={
            "paths": tmp_settings.paths.model_copy(
                update={"data_processed": tmp_path / "data" / "processed"}
            )
        }
    )
    cal_path = settings.paths.data_raw / "calendar" / "calendar.parquet"
    cal_path.parent.mkdir(parents=True)
    calendar_frame(date(2023, 1, 1), date(2024, 6, 30)).to_parquet(cal_path, index=False)

    profiles = profile.run(settings)

    assert set(profiles) == {"styriametal_v1", profile.FLAT_PROFILE_NAME}
    for name in profiles:
        hourly, monthly = profile.output_paths(settings, name)
        assert hourly.exists() and monthly.exists()
    assert profile.output_paths(settings, "styriametal_v1")[0].name == (
        "consumer_load_hourly.parquet"
    )
    rows = read_ssot_rows(settings)
    assert rows["key"].tolist() == ["consumer_peak_share", "consumer_peak_share_flat_baseload"]
    assert set(rows["tag"]) == {"CALIBRATED"}


def test_read_calendar_missing_raises(tmp_settings: Settings) -> None:
    with pytest.raises(FileNotFoundError, match="make calendar"):
        profile.read_calendar(tmp_settings)
