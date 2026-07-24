"""Config loading + drift guards.

The committed YAML files are authoritative copies of spec sections (SPEC-03 §6,
SPEC-05 §8, SPEC-01 App. A EIC codes). These tests pin the values the rest of
the project relies on, so accidental config edits fail loudly here instead of
silently shifting results downstream.
"""

import pytest
from pydantic import ValidationError

from epra.common.config import (
    ConsumerProfileCfg,
    entsoe_token,
    load_consumer_profile,
    load_settings,
    load_strategy_config,
)


def test_settings_zones_match_spec01_appendix_a() -> None:
    s = load_settings()
    assert s.zones["at"].eic == "10YAT-APG------L"
    assert s.zones["at"].code == "AT"
    assert s.zones["delu"].eic == "10Y1001A1001A82H"
    assert s.zones["delu"].code == "DE_LU"


def test_settings_window_and_ingest_params() -> None:
    s = load_settings()
    assert s.timezone_local == "Europe/Vienna"
    assert s.window.start_date.isoformat() == "2019-01-01"  # Charter §4.3
    assert s.ingest.chunk_days == 90  # ING-030
    assert s.ingest.entsoe_sleep_s == 0.5  # ING-007
    assert s.ingest.cache_min_age_days == 7  # ING-009
    assert s.ingest.incremental_lookback_days == 45  # ING-041


def test_settings_geosphere_station_discovered() -> None:
    # ING-091: station is discovered, not hardcoded (docs/ADR/ADR-007) — this
    # test asserts the ADR'd station id, not a hardcoded value.
    s = load_settings()
    assert s.geosphere.dataset_id == "klima-v2-1d"
    assert s.geosphere.parameter == "tl_mittel"
    assert s.geosphere.station_id == "30"
    assert s.geosphere.station_name == "Graz Universität/Heinrichstraße"


def test_consumer_profile_matches_spec03() -> None:
    cfg = load_consumer_profile()
    assert cfg.profile_name == "styriametal_v1"
    assert cfg.annual_consumption_mwh == 50000.0
    assert cfg.timezone == "Europe/Vienna"
    assert len(cfg.day_shapes["weekday"]) == 24
    assert cfg.day_shapes["weekday"][7] == 1.00
    assert cfg.day_shapes["weekday"][0] == 0.65
    assert cfg.day_shapes["weekend"][7] == 0.35
    assert set(cfg.day_shapes["shutdown"]) == {0.18}
    assert cfg.seasonal_factors[1] == 1.06
    assert cfg.seasonal_factors[7] == 0.95
    assert cfg.maintenance.rule == "first_full_week_august"
    assert cfg.maintenance.factor == 0.60
    assert cfg.christmas_shutdown.start == "12-24"
    assert cfg.christmas_shutdown.end == "01-01"


def test_strategy_config_matches_spec05() -> None:
    cfg = load_strategy_config()
    assert cfg.retrospective_years == [2021, 2022, 2023, 2024, 2025]
    assert cfg.reference_year == 2019
    assert cfg.lock_window_months == [7, 8, 9, 10, 11, 12]  # ST-105 H2 lock
    assert cfg.fixed_premium_eur_mwh == 5.0
    assert cfg.hybrid_ratios == [0.30, 0.50, 0.70]
    assert cfg.forward.n_paths == 2000
    assert cfg.forward.seed == 42  # ST-401 determinism
    assert cfg.forward.horizon_months == 12
    assert cfg.peak_available is True


def _profile_dict() -> dict[str, object]:
    return load_consumer_profile().model_dump()


def test_day_shape_validator_rejects_wrong_length() -> None:
    bad = _profile_dict()
    bad["day_shapes"] = {**bad["day_shapes"], "weekday": [1.0] * 23}  # type: ignore[dict-item]
    with pytest.raises(ValidationError, match="24 values"):
        ConsumerProfileCfg.model_validate(bad)


def test_day_shape_validator_rejects_missing_shape() -> None:
    bad = _profile_dict()
    shapes = dict(bad["day_shapes"])  # type: ignore[arg-type]
    del shapes["shutdown"]
    bad["day_shapes"] = shapes
    with pytest.raises(ValidationError, match="shutdown"):
        ConsumerProfileCfg.model_validate(bad)


def test_seasonal_validator_requires_all_12_months() -> None:
    bad = _profile_dict()
    factors = dict(bad["seasonal_factors"])  # type: ignore[arg-type]
    del factors[12]
    bad["seasonal_factors"] = factors
    with pytest.raises(ValidationError, match=r"1\.\.12"):
        ConsumerProfileCfg.model_validate(bad)


def test_entsoe_token_fails_fast_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    # ING-021: fail fast with a clear message.
    # Isolate from any real `.env` on the developer/CI machine: entsoe_token()
    # calls load_dotenv(), which would otherwise repopulate the deleted env var
    # from a committed-locally .env and defeat the fail-fast assertion.
    monkeypatch.setattr("epra.common.config.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("ENTSOE_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="ENTSOE_API_TOKEN"):
        entsoe_token()
    monkeypatch.setenv("ENTSOE_API_TOKEN", "your-token-here")  # placeholder is not a token
    with pytest.raises(RuntimeError):
        entsoe_token()
    monkeypatch.setenv("ENTSOE_API_TOKEN", "real-looking-token-123")
    assert entsoe_token() == "real-looking-token-123"
