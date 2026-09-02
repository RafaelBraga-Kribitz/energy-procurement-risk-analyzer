"""Consumer load-profile weight engine (SPEC-03 §2 steps 1-4, ADR-012).

Uses a module-scoped ING-110 calendar so DST/holiday flags are real, not
invented (A-2). Numerics under test are read from ``load_consumer_profile()``.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from epra.common.config import ConsumerProfileCfg, Settings, load_consumer_profile, load_settings
from epra.consumer import profile as prof
from epra.ingest.calendar import build_calendar

_FIXED_END = date(2027, 12, 31)


@pytest.fixture(scope="module")
def cfg() -> ConsumerProfileCfg:
    return load_consumer_profile()


@pytest.fixture(scope="module")
def calendar_frame() -> pd.DataFrame:
    return build_calendar(load_settings(), end=_FIXED_END)


def _rows_on(calendar_frame: pd.DataFrame, day: date) -> pd.DataFrame:
    mask = [_as_date(v) == day for v in calendar_frame["date_local"]]
    out = calendar_frame.loc[mask]
    assert not out.empty, f"no calendar rows for {day}"
    return out


def _as_date(value: object) -> date:
    return prof._as_date(value)


def test_adr012_2022_aug1_monday_window_is_aug_1_through_7(cfg: ConsumerProfileCfg) -> None:
    """1 Aug 2022 was Monday → maintenance [2022-08-01, 2022-08-07] (ADR-012)."""
    assert date(2022, 8, 1).weekday() == 0
    window = prof.maintenance_dates_for_year(2022, cfg)
    assert window == {date(2022, 8, d) for d in range(1, 8)}


def test_day_type_holiday_monday_is_weekend(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    # 2023-05-01 is Staatsfeiertag and a Monday.
    rows = _rows_on(calendar_frame, date(2023, 5, 1))
    assert bool(rows["is_holiday_at"].iloc[0])
    assert int(rows["dow_local"].iloc[0]) == 0
    assert prof.day_type(rows.iloc[0], cfg) == "weekend"


def test_day_type_plain_saturday_is_weekend(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    rows = _rows_on(calendar_frame, date(2023, 3, 4))  # Saturday
    assert not bool(rows["is_holiday_at"].iloc[0])
    assert prof.day_type(rows.iloc[0], cfg) == "weekend"


def test_day_type_plain_wednesday_is_weekday(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    rows = _rows_on(calendar_frame, date(2023, 3, 1))  # Wednesday
    assert prof.day_type(rows.iloc[0], cfg) == "weekday"


def test_christmas_overrides_day_type_to_shutdown(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    for day in (date(2023, 12, 25), date(2023, 12, 26), date(2024, 1, 1)):
        row = _rows_on(calendar_frame, day).iloc[0]
        assert prof.day_type(row, cfg) == "shutdown"
        assert prof.special_factor(_as_date(row["date_local"]), cfg) == 1.0


def test_jan1_belongs_to_new_local_year(calendar_frame: pd.DataFrame) -> None:
    rows = _rows_on(calendar_frame, date(2024, 1, 1))
    assert int(rows["year_local"].iloc[0]) == 2024


def test_maintenance_keeps_weekday_type_and_applies_factor(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    maint = _rows_on(calendar_frame, date(2022, 8, 1))  # Monday
    row = maint.iloc[0]
    assert prof.day_type(row, cfg) == "weekday"
    assert prof.special_factor(date(2022, 8, 1), cfg) == cfg.maintenance.factor
    after = _rows_on(calendar_frame, date(2022, 8, 8)).iloc[0]
    assert prof.special_factor(date(2022, 8, 8), cfg) == 1.0
    assert prof.day_type(after, cfg) == "weekday"


def test_dec25_and_dec26_weights_equal(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    weights = prof.hourly_weights(calendar_frame, cfg)
    w25 = weights.loc[_rows_on(calendar_frame, date(2023, 12, 25)).index]
    w26 = weights.loc[_rows_on(calendar_frame, date(2023, 12, 26)).index]
    pd.testing.assert_series_equal(
        pd.Series(w25.to_numpy()),
        pd.Series(w26.to_numpy()),
        check_names=False,
    )


def test_march_weekday_hour14_matches_cfg_product(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    """Guide 5.4: weekday 14:00 in March, no special window."""
    day = _rows_on(calendar_frame, date(2023, 3, 1))
    hour14 = day.loc[day["hour_local"] == 14].iloc[0]
    weights = prof.hourly_weights(calendar_frame, cfg)
    expected = cfg.day_shapes["weekday"][14] * cfg.seasonal_factors[3] * 1.0
    assert weights.loc[hour14.name] == pytest.approx(expected)


def test_maintenance_hour_is_shape_times_seasonal_times_factor(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    day = _rows_on(calendar_frame, date(2022, 8, 1))
    hour14 = day.loc[day["hour_local"] == 14].iloc[0]
    weights = prof.hourly_weights(calendar_frame, cfg)
    expected = cfg.day_shapes["weekday"][14] * cfg.seasonal_factors[8] * cfg.maintenance.factor
    assert weights.loc[hour14.name] == pytest.approx(expected)


def test_unknown_profile_name_raises(calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg) -> None:
    bad = cfg.model_copy(update={"profile_name": "not_a_real_profile"})
    with pytest.raises(ValueError, match="unknown profile_name"):
        prof.hourly_weights(calendar_frame.iloc[:24], bad)


def test_hourly_weights_length_matches_calendar(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    weights = prof.hourly_weights(calendar_frame, cfg)
    assert len(weights) == len(calendar_frame)
    assert not weights.isna().any()
    assert (weights > 0).all()


def _monthly_volumes(profile: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    merged = profile.merge(calendar[["ts_utc", "year_local", "month_local"]], on="ts_utc")
    grouped = merged.groupby(["year_local", "month_local"], as_index=False)["load_mwh"].sum()
    return grouped.rename(columns={"load_mwh": "volume_mwh"})


@pytest.mark.parametrize("year", [2019, 2020, 2023, 2024])
def test_full_local_year_sums_to_annual(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg, year: int
) -> None:
    year_cal = calendar_frame.loc[calendar_frame["year_local"] == year]
    profile = prof.build_profile(year_cal, cfg)
    total = float(profile["load_mwh"].sum())
    assert total == pytest.approx(cfg.annual_consumption_mwh, abs=0.01)


def test_lp034_partial_h1_2023_matches_full_year_months(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    cal_2023 = calendar_frame.loc[calendar_frame["year_local"] == 2023]
    full = prof.build_profile(cal_2023, cfg)
    h1_cal = cal_2023.loc[cal_2023["month_local"] <= 6]
    partial = prof.build_profile(h1_cal, cfg)
    full_m = _monthly_volumes(full, cal_2023)
    part_m = _monthly_volumes(partial, h1_cal)
    for month in range(1, 7):
        f = float(full_m.loc[full_m["month_local"] == month, "volume_mwh"].iloc[0])
        p = float(part_m.loc[part_m["month_local"] == month, "volume_mwh"].iloc[0])
        assert p == pytest.approx(f, abs=0.01)


def test_build_profile_no_nan_or_negative(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    slice_2023 = calendar_frame.loc[calendar_frame["year_local"] == 2023]
    profile = prof.build_profile(slice_2023, cfg)
    assert list(profile.columns) == ["ts_utc", "load_mwh"]
    assert profile["load_mwh"].notna().all()
    assert (profile["load_mwh"] >= 0).all()
    assert len(profile) == len(slice_2023)
    assert profile["ts_utc"].nunique() == len(profile)


def test_dst_days_match_calendar_row_counts(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    cal_2024 = calendar_frame.loc[calendar_frame["year_local"] == 2024]
    profile = prof.build_profile(cal_2024, cfg)
    merged = profile.merge(cal_2024[["ts_utc", "date_local"]], on="ts_utc")
    spring = merged.loc[[_as_date(v) == date(2024, 3, 31) for v in merged["date_local"]]]
    fall = merged.loc[[_as_date(v) == date(2024, 10, 27) for v in merged["date_local"]]]
    assert len(spring) == 23
    assert len(fall) == 25


def test_build_profile_rejects_empty_and_duplicate_ts(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    with pytest.raises(ValueError, match="empty"):
        prof.build_profile(calendar_frame.iloc[0:0], cfg)
    dup = pd.concat([calendar_frame.iloc[:2], calendar_frame.iloc[:1]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate ts_utc"):
        prof.build_profile(dup, cfg)


def test_peak_share_2019_in_band_and_yearly_deviation_under_1pp(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    cal = calendar_frame.loc[calendar_frame["year_local"].isin(range(2019, 2025))]
    built = prof.build_profile(cal, cfg)
    share_2019 = prof.reference_peak_share(built, cal)
    assert 0.42 <= share_2019 <= 0.48
    by_year = prof.peak_share_by_year(built, cal)
    for year, value in by_year.items():
        if int(year) == 2019:
            continue
        assert abs(float(value) - share_2019) < 0.01, (year, value, share_2019)


def test_monthly_volumes_2023_grain_and_annual_sum(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg
) -> None:
    cal = calendar_frame.loc[calendar_frame["year_local"] == 2023]
    built = prof.build_profile(cal, cfg)
    monthly = prof.monthly_volumes(built, cal)
    assert list(monthly.columns) == ["year_local", "month_local", "volume_mwh"]
    assert set(monthly["month_local"].tolist()) == set(range(1, 13))
    assert float(monthly["volume_mwh"].sum()) == pytest.approx(cfg.annual_consumption_mwh, abs=0.01)


def test_write_profile_outputs_roundtrip(
    calendar_frame: pd.DataFrame, cfg: ConsumerProfileCfg, tmp_settings: Settings
) -> None:
    cal = calendar_frame.loc[calendar_frame["year_local"].isin(range(2019, 2024))]
    built = prof.build_profile(cal, cfg)
    prof.write_profile_outputs(built, cal, cfg, tmp_settings)
    root = tmp_settings.paths.data_processed
    hourly = pd.read_parquet(root / "consumer_load_hourly.parquet")
    assert list(hourly.columns) == ["ts_utc", "load_mwh"]
    pd.testing.assert_frame_equal(
        hourly.reset_index(drop=True), built.reset_index(drop=True), check_dtype=False
    )
    monthly = pd.read_parquet(root / "consumer_load_monthly.parquet")
    assert list(monthly.columns) == ["year_local", "month_local", "volume_mwh"]
    ssot = pd.read_parquet(root / "ssot_inputs_profile.parquet")
    assert list(ssot.columns) == ["key", "value", "unit", "tag", "produced_by"]
    row = ssot.iloc[0]
    assert row["key"] == "consumer_peak_share"
    assert row["unit"] == "fraction"
    assert row["tag"] == "CALIBRATED"
    assert row["produced_by"] == "epra.consumer.profile"
    assert 0.42 <= float(row["value"]) <= 0.48
