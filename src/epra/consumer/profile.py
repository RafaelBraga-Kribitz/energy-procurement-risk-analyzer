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

from collections.abc import Mapping
from datetime import date, datetime, timedelta
from typing import Any, Literal, cast

import numpy as np
import pandas as pd

from epra.common.config import ConsumerProfileCfg

_MSG = "M4 not implemented yet — build per SPEC-03 §2 (see module docstring)"

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


def build_profile(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> pd.DataFrame:
    """SPEC-03 §2 entrypoint: hourly ``ts_utc, load_mwh`` frame, deterministic."""
    raise NotImplementedError(_MSG)


def monthly_volumes(profile_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to ``year_local, month_local, volume_mwh`` (LP-021)."""
    raise NotImplementedError(_MSG)
