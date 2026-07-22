"""Unit tests for `epra.ingest.geosphere` — station discovery (ING-090..092).

Every non-`live`-marked test injects a `transport` stub returning the
committed `tests/fixtures/geosphere/metadata.json` fixture (or a small inline
payload), so CI never depends on the real GeoSphere endpoint (D-06/D-07,
EN-070). `tests/fixtures/geosphere/metadata.json` is crafted in the real
GeoSphere metadata shape (a top-level ``stations`` list) and deliberately
puts a same-`valid_from` decoy ("Graz Nord Decoy") BEFORE "Graz Universität"
in list order, so `test_discover_station_prefers_graz_universitaet` only
passes if the name tie-break is actually applied — not merely "first Graz
station wins by list order".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from epra.common.config import Settings, load_settings
from epra.ingest.exceptions import ContractError, DiscoveryError
from epra.ingest.geosphere import StationInfo, discover_station

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "geosphere" / "metadata.json"


def _fixture_metadata() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _settings() -> Settings:
    return load_settings()


def test_discover_station_prefers_graz_universitaet() -> None:
    payload = _fixture_metadata()

    station = discover_station(_settings(), transport=lambda settings: payload)

    assert isinstance(station, StationInfo)
    assert station.name == "Graz Universität"
    expected = next(s for s in payload["stations"] if s["name"] == "Graz Universität")
    assert station.id == str(expected["id"])
    assert station.lat == expected["lat"]
    assert station.lon == expected["lon"]
    assert station.record_start.isoformat() == "1894-01-01"


def test_discover_station_filters_out_non_graz_and_shorter_records() -> None:
    payload = _fixture_metadata()

    station = discover_station(_settings(), transport=lambda settings: payload)

    assert station.name not in {"Wien Hohe Warte", "Graz Straßgang", "Graz Nord Decoy"}


def test_discover_station_raises_when_no_graz_station() -> None:
    payload = {
        "stations": [
            {
                "id": 1,
                "name": "Wien Hohe Warte",
                "lat": 48.2486,
                "lon": 16.3564,
                "valid_from": "1872-01-01T00:00:00+00:00",
                "valid_to": "2100-12-31T00:00:00+00:00",
            }
        ]
    }

    with pytest.raises(DiscoveryError, match="Wien Hohe Warte"):
        discover_station(_settings(), transport=lambda settings: payload)


def test_discover_station_rejects_malformed_top_level_shape() -> None:
    with pytest.raises(ContractError):
        discover_station(_settings(), transport=lambda settings: ["not", "a", "dict"])


def test_discover_station_rejects_payload_missing_stations_and_features() -> None:
    with pytest.raises(ContractError):
        discover_station(_settings(), transport=lambda settings: {"unrelated": "shape"})


@pytest.mark.live
def test_discover_station_live_reaches_geosphere() -> None:
    """Real network call (EN-070) — excluded from `pytest -m "not live"`."""
    station = discover_station(_settings())

    assert "Graz" in station.name
