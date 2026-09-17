"""Consumer load profile construction — "StyriaMetal GmbH" (M4).

Binding contract: SPEC-03 §2 (algorithm — implement the five steps EXACTLY
in order), §3 (parameters, YAML wins), §7 (golden + property tests).
Epistemic tag of all outputs: CALIBRATED.

Non-negotiables:

- Zero randomness (LP-001); zero hardcoded YAML numerics (LP-002) — everything
  from ``config/consumer_profile.yaml`` via ``load_consumer_profile()``.
- day_type precedence (Step 2): shutdown window > holiday→weekend > Sat/Sun →
  weekend > weekday. Maintenance days KEEP their day_type (factor applies on
  top); Christmas shutdown OVERRIDES day_type with no double dampening (§3.3).
- Per-LOCAL-year normalization to exactly annual_consumption_mwh ± 0.01
  (LP-004); partial years normalize against the full hypothetical-year shape
  sum (LP-034).

Implements: LP-001, LP-002, SPEC-03 §2 steps 1-4, ADR-012.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

import numpy as np
import pandas as pd

from epra.common.config import REPO_ROOT, ConsumerProfileCfg, Settings, load_settings
from epra.ingest.calendar import build_calendar

_ALLOWED_PROFILES = frozenset({"styriametal_v1", "flat_baseload"})
_DayType = Literal["shutdown", "weekend", "weekday"]
_DAY_TYPE_INDEX: dict[str, int] = {"shutdown": 0, "weekend": 1, "weekday": 2}


def _as_date(value: object) -> date:
    """Coerce calendar ``date_local`` cells to ``datetime.date``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, pd.Timestamp):
        return value.date()
    return pd.Timestamp(cast(Any, value)).date()


def _field(row: object, key: str) -> object:
    if isinstance(row, pd.Series):
        return row[key]
    if isinstance(row, Mapping):
        return row[key]
    return getattr(row, key)


def _parse_mmdd(token: str) -> tuple[int, int]:
    month_s, day_s = token.split("-", maxsplit=1)
    return int(month_s), int(day_s)


def _is_christmas_shutdown(day: date, cfg: ConsumerProfileCfg) -> bool:
    """Dec 24-31 or Jan 1 (inclusive wrap) per cfg ``MM-DD`` bounds."""
    start = _parse_mmdd(cfg.christmas_shutdown.start)
    end = _parse_mmdd(cfg.christmas_shutdown.end)
    mmdd = (day.month, day.day)
    return mmdd >= start or mmdd <= end


def first_monday_on_or_after(day: date) -> date:
    """First Monday with ``m >= day`` (Monday = weekday 0).

    Implements: ADR-012.
    """
    return day + timedelta(days=(0 - day.weekday()) % 7)


def maintenance_dates_for_year(year: int, cfg: ConsumerProfileCfg) -> set[date]:
    """SG-04 / ADR-012 window: first Monday ≥ 1 Aug through the following Sunday.

    Implements: ADR-012, SPEC-03 §3.3.
    """
    if cfg.maintenance.rule != "first_full_week_august":
        raise ValueError(
            f"unsupported maintenance.rule {cfg.maintenance.rule!r}; "
            "expected 'first_full_week_august'"
        )
    start = first_monday_on_or_after(date(year, 8, 1))
    return {start + timedelta(days=offset) for offset in range(7)}


def _require_profile_name(cfg: ConsumerProfileCfg) -> None:
    if cfg.profile_name not in _ALLOWED_PROFILES:
        allowed = ", ".join(sorted(_ALLOWED_PROFILES))
        raise ValueError(f"unknown profile_name {cfg.profile_name!r}; expected one of: {allowed}")


def day_type(row: object, cfg: ConsumerProfileCfg) -> _DayType:
    """SPEC-03 §2 Step 2 precedence (first match wins).

    Implements: LP-001, SPEC-03 §2 step 2.
    """
    day = _as_date(_field(row, "date_local"))
    if _is_christmas_shutdown(day, cfg):
        return "shutdown"
    if bool(_field(row, "is_holiday_at")):
        return "weekend"
    dow_raw = _field(row, "dow_local")
    if not isinstance(dow_raw, (int, np.integer)):
        raise TypeError(f"dow_local must be int, got {type(dow_raw).__name__}")
    if int(dow_raw) in (5, 6):
        return "weekend"
    return "weekday"


def special_factor(date_local: date, cfg: ConsumerProfileCfg) -> float:
    """Maintenance factor vs identity 1.0 (shutdown is not double-dampened).

    Implements: LP-002, SPEC-03 §2 step 3, ADR-012.
    """
    day = _as_date(date_local)
    if _is_christmas_shutdown(day, cfg):
        return 1.0
    if day in maintenance_dates_for_year(day.year, cfg):
        return cfg.maintenance.factor
    return 1.0


def _christmas_mask(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> np.ndarray:
    """Vectorized Dec 24-Jan 1 wrap using month_local + day-of-month."""
    start_m, start_d = _parse_mmdd(cfg.christmas_shutdown.start)
    end_m, end_d = _parse_mmdd(cfg.christmas_shutdown.end)
    months = calendar_df["month_local"].to_numpy(dtype=int)
    days = pd.to_datetime(calendar_df["date_local"]).dt.day.to_numpy()
    ge_start = (months > start_m) | ((months == start_m) & (days >= start_d))
    le_end = (months < end_m) | ((months == end_m) & (days <= end_d))
    return np.asarray(ge_start | le_end, dtype=bool)


def _maintenance_mask(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> np.ndarray:
    years = {int(y) for y in calendar_df["year_local"].to_numpy()}
    maint: set[date] = set()
    for year in years:
        maint |= maintenance_dates_for_year(year, cfg)
    date_local = pd.Series(
        pd.to_datetime(calendar_df["date_local"]).dt.date, index=calendar_df.index
    )
    return date_local.isin(maint).to_numpy()


def _styriametal_weights(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> np.ndarray:
    shutdown = _christmas_mask(calendar_df, cfg)
    holiday = calendar_df["is_holiday_at"].to_numpy(dtype=bool)
    weekend = calendar_df["dow_local"].to_numpy() >= 5
    day_code = np.select(
        [shutdown, holiday | weekend],
        [_DAY_TYPE_INDEX["shutdown"], _DAY_TYPE_INDEX["weekend"]],
        default=_DAY_TYPE_INDEX["weekday"],
    )
    shape_table = np.vstack(
        [
            np.asarray(cfg.day_shapes["shutdown"], dtype="float64"),
            np.asarray(cfg.day_shapes["weekend"], dtype="float64"),
            np.asarray(cfg.day_shapes["weekday"], dtype="float64"),
        ]
    )
    hours = calendar_df["hour_local"].to_numpy(dtype=int)
    seasonal = np.array([cfg.seasonal_factors[month] for month in range(1, 13)], dtype="float64")
    months = calendar_df["month_local"].to_numpy(dtype=int)
    special = np.where(_maintenance_mask(calendar_df, cfg) & ~shutdown, cfg.maintenance.factor, 1.0)
    return np.asarray(
        shape_table[day_code, hours] * seasonal[months - 1] * special, dtype="float64"
    )


def hourly_weights(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> pd.Series:
    """Raw per-hour weights (SPEC-03 §2 steps 1-4), not yet year-normalized.

    Implements: LP-001, LP-002, SPEC-03 §2 steps 1-4, ADR-012.
    """
    _require_profile_name(cfg)
    n = len(calendar_df)
    index = calendar_df.index
    if cfg.profile_name == "flat_baseload":
        return pd.Series(np.ones(n, dtype="float64"), index=index, name="weight")
    return pd.Series(_styriametal_weights(calendar_df, cfg), index=index, name="weight")


_REQUIRED_CALENDAR_COLS = (
    "ts_utc",
    "date_local",
    "hour_local",
    "dow_local",
    "is_holiday_at",
    "year_local",
    "month_local",
)


@cache
def _full_year_calendar(year: int) -> pd.DataFrame:
    """ING-110 hours whose ``year_local`` equals ``year`` (LP-034 denominator)."""
    frame = build_calendar(load_settings(), end=date(year, 12, 31))
    masked = frame.loc[frame["year_local"].to_numpy() == year]
    return pd.DataFrame(masked).reset_index(drop=True)


def _year_is_complete(year_rows: pd.DataFrame, year: int) -> bool:
    full = _full_year_calendar(year)
    if len(year_rows) != len(full):
        return False
    return bool(year_rows["ts_utc"].isin(full["ts_utc"]).all())


def normalize_by_local_year(
    weights: pd.Series, calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg
) -> pd.Series:
    """Scale weights so each full local year sums to ``annual_consumption_mwh``.

    Partial years use hypothetical full-year Σw (LP-034).

    Implements: LP-004, LP-034, SPEC-03 §2 step 5.
    """
    years = calendar_df["year_local"].to_numpy()
    w = weights.to_numpy(dtype="float64")
    out = np.empty(len(w), dtype="float64")
    annual = cfg.annual_consumption_mwh
    for year in np.unique(years):
        year_i = int(year)
        mask = years == year
        year_rows = calendar_df.loc[mask]
        if _year_is_complete(year_rows, year_i):
            denom = float(w[mask].sum())
        else:
            denom = float(hourly_weights(_full_year_calendar(year_i), cfg).sum())
        if denom == 0.0:
            raise ValueError(f"zero weight sum for local year {year_i}")
        out[mask] = annual * w[mask] / denom
    return pd.Series(out, index=weights.index, name="load_mwh")


def _validate_calendar(calendar_df: pd.DataFrame) -> None:
    if calendar_df.empty:
        raise ValueError("calendar_df is empty — cannot build a load profile")
    missing = [c for c in _REQUIRED_CALENDAR_COLS if c not in calendar_df.columns]
    if missing:
        raise ValueError(f"calendar_df missing required columns: {missing}")
    if calendar_df["ts_utc"].duplicated().any():
        raise ValueError("calendar_df has duplicate ts_utc values")


def build_profile(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> pd.DataFrame:
    """SPEC-03 §2 entrypoint: hourly ``ts_utc, load_mwh`` frame, deterministic.

    Implements: LP-001, LP-004, LP-034, SPEC-03 §2.
    """
    _validate_calendar(calendar_df)
    weights = hourly_weights(calendar_df, cfg)
    load = normalize_by_local_year(weights, calendar_df, cfg)
    return pd.DataFrame({"ts_utc": calendar_df["ts_utc"].to_numpy(), "load_mwh": load.to_numpy()})


_REFERENCE_YEAR = 2019  # ADR-013 / SG-03; not a YAML load-shape numeric


def monthly_volumes(profile_df: pd.DataFrame, calendar_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to ``year_local, month_local, volume_mwh`` (LP-021).

    Implements: LP-021.
    """
    if profile_df.empty:
        raise ValueError("profile_df is empty - cannot aggregate monthly volumes")
    cols = calendar_df[["ts_utc", "year_local", "month_local"]]
    merged = profile_df.merge(cols, on="ts_utc", how="inner")
    if len(merged) != len(profile_df):
        raise ValueError("profile ts_utc must all be present on the calendar")
    grouped = merged.groupby(["year_local", "month_local"], as_index=False, sort=True).agg(
        volume_mwh=("load_mwh", "sum")
    )
    return pd.DataFrame(grouped)


def peak_share_by_year(profile_df: pd.DataFrame, calendar_df: pd.DataFrame) -> pd.Series:
    """Peak-hour volume fraction by local year (LP-020, ADR-013).

    Implements: LP-020, ADR-013.
    """
    cols = calendar_df[["ts_utc", "year_local", "is_peak_hour"]]
    merged = profile_df.merge(cols, on="ts_utc", how="inner")
    if len(merged) != len(profile_df):
        raise ValueError("profile ts_utc must all be present on the calendar")
    peak_mwh = np.where(merged["is_peak_hour"].to_numpy(dtype=bool), merged["load_mwh"], 0.0)
    merged = merged.assign(peak_mwh=peak_mwh)
    agg = merged.groupby("year_local", sort=True).agg(
        peak_mwh=("peak_mwh", "sum"), total_mwh=("load_mwh", "sum")
    )
    return (agg["peak_mwh"] / agg["total_mwh"]).rename("peak_share")


def reference_peak_share(
    profile_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    *,
    reference_year: int = _REFERENCE_YEAR,
) -> float:
    """2019 local-year peak share published to SSOT (ADR-013).

    Implements: LP-020, ADR-013.
    """
    shares = peak_share_by_year(profile_df, calendar_df)
    if reference_year not in shares.index:
        raise ValueError(f"no profile rows for reference year {reference_year}")
    return float(shares.loc[reference_year])


def _processed_root(settings: Settings) -> Path:
    path = settings.paths.data_processed
    return path if path.is_absolute() else REPO_ROOT / path


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    """Temp-file + ``os.replace`` (same pattern as bootstrap calendar writer)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    frame.to_parquet(tmp_path, index=False, engine="pyarrow")
    os.replace(tmp_path, path)


def write_profile_outputs(
    profile_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    cfg: ConsumerProfileCfg,
    settings: Settings,
) -> None:
    """Persist hourly, monthly, and SSOT-input parquet under ``data/processed``.

    Implements: LP-003, LP-020, LP-021, ADR-013.
    """
    _require_profile_name(cfg)
    root = _processed_root(settings)
    hourly = profile_df[["ts_utc", "load_mwh"]].copy()
    _atomic_write_parquet(hourly, root / "consumer_load_hourly.parquet")
    _atomic_write_parquet(
        monthly_volumes(profile_df, calendar_df), root / "consumer_load_monthly.parquet"
    )
    share = reference_peak_share(profile_df, calendar_df)
    ssot = pd.DataFrame(
        [
            {
                "key": "consumer_peak_share",
                "value": share,
                "unit": "fraction",
                "tag": "CALIBRATED",
                "produced_by": "epra.consumer.profile",
            }
        ]
    )
    _atomic_write_parquet(ssot, root / "ssot_inputs_profile.parquet")


def year_slice_checksum(
    profile_df: pd.DataFrame, calendar_df: pd.DataFrame, *, year: int = 2023
) -> str:
    """SHA-256 of sorted ``load_mwh`` float64 bytes for one local year (LP-040).

    Implements: LP-040, LP-042.
    """
    years = calendar_df[["ts_utc", "year_local"]]
    merged = profile_df.merge(years, on="ts_utc", how="inner")
    sl = merged.loc[merged["year_local"] == year, ["ts_utc", "load_mwh"]].sort_values("ts_utc")
    if sl.empty:
        raise ValueError(f"no profile rows for local year {year}")
    payload = sl["load_mwh"].to_numpy(dtype="float64", copy=False)
    return hashlib.sha256(payload.tobytes()).hexdigest()
