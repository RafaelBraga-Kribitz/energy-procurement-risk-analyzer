"""Consumer load profile construction — "StyriaMetal GmbH" (M4, SPEC-03).

Deterministic hourly load of the reference consumer, built from
``config/consumer_profile.yaml`` and the ING-110 calendar spine, following the
five steps of SPEC-03 §2 in order:

1. raw weight ``w(h) = day_shape[day_type][hour_local] × seasonal × special``;
2. ``day_type``: shutdown window > holiday → weekend > Sat/Sun → weekend > weekday;
3. ``special_factor``: maintenance factor on maintenance days, else 1.0
   (shutdown days use the flat shutdown shape — no double dampening, §3.3);
4. seasonal factor by ``month_local``;
5. normalization per LOCAL year to ``annual_consumption_mwh``; a partial year
   is normalized against the weight sum of the full hypothetical year (LP-034).

No randomness (LP-001) and no hardcoded numerics (LP-002). Epistemic tag of
every output: CALIBRATED — the profile is constructed, not measured (LP-050).

Implements: LP-001..004, LP-020..021, LP-030, LP-034.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from epra.common import logging as common_logging
from epra.common.config import (
    ConsumerProfileCfg,
    Settings,
    load_consumer_profile,
    load_settings,
    resolve_repo_path,
)
from epra.common.ssot import SsotRow, write_ssot_rows
from epra.common.timeutil import VIENNA, local_hours_in_day
from epra.ingest.calendar import calendar_frame

logger = logging.getLogger(__name__)

#: LP-050 caption — one sentence, verbatim on every load-derived artifact.
CALIBRATED_CAPTION = (
    "Reference load profile is constructed (CALIBRATED), not measured; "
    "construction rules in SPEC-03."
)
FLAT_PROFILE_NAME = "flat_baseload"
MONTHLY_COLUMNS = ["year_local", "month_local", "volume_mwh"]
_SUPPORTED_MAINTENANCE_RULE = "first_full_week_august"
_SATURDAY = 5  # dow_local convention of the calendar spine: 0 = Monday


def flat_baseload_config(cfg: ConsumerProfileCfg) -> ConsumerProfileCfg:
    """The LP-030 sensitivity variant: same volume and calendar, all weights 1.0.

    Derived from the one YAML file (Charter §2) rather than a second copy of
    the parameters, so the two profiles can never disagree on volume.

    Implements: LP-030.
    """
    ones = [1.0] * 24
    return cfg.model_copy(
        update={
            "profile_name": FLAT_PROFILE_NAME,
            "day_shapes": dict.fromkeys(cfg.day_shapes, ones),
            "seasonal_factors": dict.fromkeys(cfg.seasonal_factors, 1.0),
            "maintenance": cfg.maintenance.model_copy(update={"factor": 1.0}),
        }
    )


def _month_day(text: str) -> int:
    """``"MM-DD"`` → ``MMDD`` as an int, for wrap-around window comparisons."""
    month, day = (int(part) for part in text.split("-"))
    return month * 100 + day


def _shutdown_mask(dates: pd.DatetimeIndex, cfg: ConsumerProfileCfg) -> np.ndarray:
    """True on dates inside the Christmas shutdown window (may span New Year)."""
    start = _month_day(cfg.christmas_shutdown.start)
    end = _month_day(cfg.christmas_shutdown.end)
    month_day = np.asarray(dates.month * 100 + dates.day)
    if start <= end:
        return np.asarray((month_day >= start) & (month_day <= end))
    return np.asarray((month_day >= start) | (month_day <= end))


def maintenance_dates(years: Sequence[int], cfg: ConsumerProfileCfg) -> set[date]:
    """First Monday of August through the following Sunday, per year (§3.3).

    Implements: LP-002 (rule name read from YAML, validated here).
    """
    if cfg.maintenance.rule != _SUPPORTED_MAINTENANCE_RULE:
        raise ValueError(f"unsupported maintenance rule {cfg.maintenance.rule!r}")
    days: set[date] = set()
    for year in years:
        first = date(year, 8, 1)
        monday = first + timedelta(days=(-first.weekday()) % 7)
        days.update(monday + timedelta(days=offset) for offset in range(7))
    return days


def raw_weights(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> np.ndarray:
    """SPEC-03 §2 steps 1-4: un-normalized hourly weight per calendar row.

    Implements: LP-001, LP-002.
    """
    dates = pd.DatetimeIndex(pd.to_datetime(calendar_df["date_local"]))
    hour = calendar_df["hour_local"].to_numpy(dtype=int)
    shutdown = _shutdown_mask(dates, cfg)
    weekend = calendar_df["is_holiday_at"].to_numpy(dtype=bool) | (
        calendar_df["dow_local"].to_numpy(dtype=int) >= _SATURDAY
    )
    shapes = {name: np.asarray(values) for name, values in cfg.day_shapes.items()}
    shape_value = np.where(
        shutdown,
        shapes["shutdown"][hour],
        np.where(weekend, shapes["weekend"][hour], shapes["weekday"][hour]),
    )
    seasonal = calendar_df["month_local"].map(cfg.seasonal_factors).to_numpy(dtype=float)
    maint_days = maintenance_dates(sorted(set(dates.year)), cfg)
    is_maintenance = np.asarray([d in maint_days for d in dates.date])
    special = np.where(is_maintenance & ~shutdown, cfg.maintenance.factor, 1.0)
    return np.asarray(shape_value * seasonal * special, dtype=float)


def _full_year_weight_sum(year: int, cfg: ConsumerProfileCfg) -> float:
    """Σ w over the full hypothetical local ``year`` (LP-034)."""
    full = calendar_frame(date(year, 1, 1), date(year, 12, 31))
    return float(raw_weights(full, cfg).sum())


def local_year_hours(year: int) -> int:
    """Hours in local ``year`` (8760/8784; DST days net out to zero).

    Implements: LP-004 (complete-year detection), LP-041.
    """
    return sum(
        local_hours_in_day(date(year, 1, 1) + timedelta(days=i))
        for i in range((date(year + 1, 1, 1) - date(year, 1, 1)).days)
    )


def build_profile(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> pd.DataFrame:
    """SPEC-03 §2 entrypoint: hourly ``ts_utc, load_mwh`` frame, deterministic.

    Complete local years are normalized over their own hours; a partial year
    over the full hypothetical year's weight sum, so its monthly volumes match
    those of a full-year 50 GWh consumer.

    Implements: LP-001, LP-003, LP-004, LP-034.
    """
    weights = raw_weights(calendar_df, cfg)
    years = calendar_df["year_local"].to_numpy(dtype=int)
    load = np.empty_like(weights)
    for year in np.unique(years):
        in_year = years == year
        complete = in_year.sum() == local_year_hours(int(year))
        denom = weights[in_year].sum() if complete else _full_year_weight_sum(int(year), cfg)
        load[in_year] = cfg.annual_consumption_mwh * weights[in_year] / denom
    ts_utc = pd.to_datetime(calendar_df["ts_utc"], utc=True).reset_index(drop=True)
    return pd.DataFrame({"ts_utc": ts_utc, "load_mwh": load})


def _local(profile_df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(profile_df["ts_utc"], utc=True).dt.tz_convert(VIENNA)


def monthly_volumes(profile_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to ``year_local, month_local, volume_mwh`` (LP-021).

    Implements: LP-021.
    """
    local = _local(profile_df)
    keys = [local.dt.year.rename("year_local"), local.dt.month.rename("month_local")]
    out = profile_df.groupby(keys, sort=True)["load_mwh"].sum().rename("volume_mwh").reset_index()
    return out.astype({"year_local": int, "month_local": int, "volume_mwh": float})


def peak_share(profile_df: pd.DataFrame, calendar_df: pd.DataFrame) -> float:
    """Share of volume in peak hours over all COMPLETE local years (LP-020).

    Peak = the calendar's ``is_peak_hour`` (Mon-Fri 08-20 local, non-holiday).
    Partial years are excluded so the share is not biased by which months a
    truncated window happens to contain.

    Implements: LP-020.
    """
    merged = profile_df.assign(
        is_peak=calendar_df["is_peak_hour"].to_numpy(dtype=bool),
        year=calendar_df["year_local"].to_numpy(dtype=int),
    )
    counts = merged.groupby("year")["load_mwh"].size()
    complete = [y for y, n in zip(counts.index, counts, strict=True) if n == local_year_hours(y)]
    in_complete = merged["year"].isin(complete)
    peak = merged.loc[in_complete & merged["is_peak"], "load_mwh"].sum()
    return float(peak / merged.loc[in_complete, "load_mwh"].sum())


def year_checksum(profile_df: pd.DataFrame, year: int) -> str:
    """sha256 of one local year's ``ts_utc,load_mwh`` rows at 6 decimals (LP-040).

    Rounding to 6 decimals (1 kWh resolution of a MWh value is 3 decimals) keeps
    the checksum platform-stable against last-bit floating-point summation
    differences while any real parameter change still alters it (LP-042).

    Implements: LP-040, LP-042.
    """
    rows = profile_df.loc[_local(profile_df).dt.year == year]
    text = "\n".join(
        f"{ts.isoformat()},{value:.6f}"
        for ts, value in zip(rows["ts_utc"], rows["load_mwh"], strict=True)
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def output_paths(settings: Settings, profile_name: str) -> tuple[Path, Path]:
    """(hourly, monthly) parquet paths; the main profile keeps the LP-003 names.

    Implements: LP-003, LP-021.
    """
    root = resolve_repo_path(settings.paths.data_processed)
    suffix = "" if profile_name == load_consumer_profile().profile_name else f"_{profile_name}"
    return (
        root / f"consumer_load_hourly{suffix}.parquet",
        root / f"consumer_load_monthly{suffix}.parquet",
    )


def read_calendar(settings: Settings) -> pd.DataFrame:
    """The ING-110 calendar spine, i.e. the source of ``dim_calendar``.

    Implements: LP-003 (profile covers the full spine incl. forward window).
    """
    path = resolve_repo_path(settings.paths.data_raw) / "calendar" / "calendar.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `make calendar` first")
    return pd.read_parquet(path).sort_values("ts_utc").reset_index(drop=True)


def run(settings: Settings) -> dict[str, pd.DataFrame]:
    """Build both profiles, write their parquet outputs and the SSOT input row.

    Implements: LP-003, LP-020, LP-021, LP-030.
    """
    calendar_df = read_calendar(settings)
    main_cfg = load_consumer_profile()
    profiles: dict[str, pd.DataFrame] = {}
    for cfg in (main_cfg, flat_baseload_config(main_cfg)):
        profile_df = build_profile(calendar_df, cfg)
        hourly_path, monthly_path = output_paths(settings, cfg.profile_name)
        hourly_path.parent.mkdir(parents=True, exist_ok=True)
        profile_df.to_parquet(hourly_path, index=False, engine="pyarrow")
        monthly_volumes(profile_df).to_parquet(monthly_path, index=False, engine="pyarrow")
        logger.info(
            "profile %s: %d hourly rows -> %s", cfg.profile_name, len(profile_df), hourly_path
        )
        profiles[cfg.profile_name] = profile_df
    share = peak_share(profiles[main_cfg.profile_name], calendar_df)
    write_ssot_rows(
        [SsotRow("consumer_peak_share", round(share, 6), "share", "CALIBRATED", "profile.py")],
        "consumer_profile",
        settings,
    )
    logger.info("consumer_peak_share = %.6f (CALIBRATED)", share)
    return profiles


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.consumer.profile`` (``make profile``).

    Implements: LP-003.
    """
    argparse.ArgumentParser(
        prog="python -m epra.consumer.profile",
        description="Build the StyriaMetal + flat_baseload hourly load profiles (SPEC-03).",
    ).parse_args(argv)
    common_logging.setup()
    run(load_settings())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
