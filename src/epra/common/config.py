"""Configuration loading — the only place YAML is read.

`load_settings()` loads ``config/settings.yaml`` once into a pydantic model;
modules receive the object and never re-read YAML ad hoc. The consumer-profile
and strategy configs get the same treatment so their schemas are validated at
load time, not at first use deep inside a pipeline.

Implements: EN-040, EN-041, ING-021, LP-002, ST-003
"""

from __future__ import annotations

import os
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, field_validator

#: Repo root = three levels above this file (src/epra/common/config.py).
REPO_ROOT = Path(__file__).resolve().parents[3]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ZoneCfg(_Frozen):
    code: str
    eic: str


class WindowCfg(_Frozen):
    start_date: date
    # The window end is always the computed "latest complete month" (ING-042),
    # deliberately absent here so it can never be configured stale.


class GeosphereCfg(_Frozen):
    base_url: str
    dataset_id: str
    station_id: str | None
    station_name: str | None
    parameter: str


class PathsCfg(_Frozen):
    data_raw: Path
    data_cache: Path
    data_manual: Path
    data_processed: Path
    warehouse: Path
    reports: Path
    exports: Path


class IngestCfg(_Frozen):
    chunk_days: int
    entsoe_sleep_s: float
    geosphere_sleep_s: float
    cache_min_age_days: int
    incremental_lookback_days: int


class Settings(_Frozen):
    timezone_local: str
    zones: dict[str, ZoneCfg]
    window: WindowCfg
    geosphere: GeosphereCfg
    paths: PathsCfg
    ingest: IngestCfg


class MaintenanceCfg(_Frozen):
    rule: str
    factor: float


class ChristmasShutdownCfg(_Frozen):
    start: str  # "MM-DD"
    end: str  # "MM-DD" (spans year boundary)


class ConsumerProfileCfg(_Frozen):
    """SPEC-03 §6 schema. YAML wins over spec prose if they diverge."""

    profile_name: str
    annual_consumption_mwh: float
    timezone: str
    day_shapes: dict[str, list[float]]
    seasonal_factors: dict[int, float]
    maintenance: MaintenanceCfg
    christmas_shutdown: ChristmasShutdownCfg

    @field_validator("day_shapes")
    @classmethod
    def _24_hours_each(cls, v: dict[str, list[float]]) -> dict[str, list[float]]:
        for name in ("weekday", "weekend", "shutdown"):
            if name not in v:
                raise ValueError(f"day_shapes missing required shape '{name}'")
            if len(v[name]) != 24:
                raise ValueError(f"day_shapes[{name}] must have 24 values, got {len(v[name])}")
        return v

    @field_validator("seasonal_factors")
    @classmethod
    def _all_12_months(cls, v: dict[int, float]) -> dict[int, float]:
        if sorted(v) != list(range(1, 13)):
            raise ValueError(f"seasonal_factors must cover months 1..12, got {sorted(v)}")
        return v


class ForwardCfg(_Frozen):
    n_paths: int
    seed: int
    horizon_months: int


class StrategyCfg(_Frozen):
    """SPEC-05 §8 schema — all simulator tunables (ST-003)."""

    retrospective_years: list[int]
    reference_year: int
    lock_window_months: list[int]
    fixed_premium_eur_mwh: float
    hybrid_ratios: list[float]
    forward: ForwardCfg
    peak_available: bool


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return loaded


@cache
def load_settings(path: Path | None = None) -> Settings:
    """Load and validate ``config/settings.yaml`` (EN-040). Cached per path."""
    return Settings.model_validate(_read_yaml(path or REPO_ROOT / "config" / "settings.yaml"))


@cache
def load_consumer_profile(path: Path | None = None) -> ConsumerProfileCfg:
    """Load and validate ``config/consumer_profile.yaml`` (LP-002)."""
    return ConsumerProfileCfg.model_validate(
        _read_yaml(path or REPO_ROOT / "config" / "consumer_profile.yaml")
    )


@cache
def load_strategy_config(path: Path | None = None) -> StrategyCfg:
    """Load and validate ``config/strategies.yaml`` (ST-003)."""
    return StrategyCfg.model_validate(_read_yaml(path or REPO_ROOT / "config" / "strategies.yaml"))


def entsoe_token() -> str:
    """Return the ENTSO-E API token from the environment, failing fast (ING-021).

    Reads ``.env`` if present (never overrides an existing env var). The token
    must never be logged, printed, or committed (A-7).
    """
    load_dotenv(REPO_ROOT / ".env")
    token = os.environ.get("ENTSOE_API_TOKEN", "").strip()
    if not token or token == "your-token-here":
        raise RuntimeError(
            "ENTSOE_API_TOKEN is not set. Copy .env.example to .env and fill in the "
            "token obtained per SPEC-01 §2 (ING-020), or export the variable."
        )
    return token
