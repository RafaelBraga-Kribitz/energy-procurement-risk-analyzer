"""Unit tests for `epra.ingest.geosphere` — station discovery (ING-090..092)
and the `parse_geojson` daily-response parser (ING-092).

Every non-`live`-marked test injects a `transport` stub returning a committed
fixture (or a small inline payload), so CI never depends on the real
GeoSphere endpoint (D-06/D-07, EN-070). `tests/fixtures/geosphere/
metadata.json` is crafted in the real GeoSphere metadata shape (a top-level
``stations`` list) and deliberately puts a same-`valid_from` decoy ("Graz
Nord Decoy") BEFORE "Graz Universität" in list order, so
`test_discover_station_prefers_graz_universitaet` only passes if the name
tie-break is actually applied — not merely "first Graz station wins by list
order". `tests/fixtures/geosphere/klima_2019-01.geojson` is a real GeoSphere
``klima-v2-1d`` daily-data response (one January of `tl_mittel` for the
pinned station) used to lock down `parse_geojson`'s exact field paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from epra.common.config import Settings, load_settings
from epra.ingest.exceptions import ContractError, DiscoveryError
from epra.ingest.geosphere import StationInfo, discover_station, parse_geojson

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "geosphere" / "metadata.json"
GEOJSON_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "geosphere" / "klima_2019-01.geojson"
)


def _fixture_metadata() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _fixture_geojson() -> dict[str, Any]:
    return json.loads(GEOJSON_FIXTURE_PATH.read_text(encoding="utf-8"))


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


# ---------------------------------------------------------------------------
# parse_geojson (ING-092) — committed fixture round-trip + shape guards
# ---------------------------------------------------------------------------


def test_parse_geojson_round_trips_the_committed_fixture() -> None:
    payload = _fixture_geojson()

    frame = parse_geojson(payload, station_id="30")

    assert list(frame.columns) == ["date", "station_id", "tl_mittel_c", "parameter_raw"]
    assert frame["tl_mittel_c"].dtype == "float64"
    assert len(frame) == 31
    assert all(d.year == 2019 and d.month == 1 for d in frame["date"])
    assert (frame["station_id"] == "30").all()
    # Plausible January-in-Graz winter values, not summer/absurd readings.
    assert frame["tl_mittel_c"].between(-20, 20).all()


def test_parse_geojson_rejects_non_dict_payload() -> None:
    with pytest.raises(ContractError):
        parse_geojson(["not", "a", "dict"], station_id="30")


def test_parse_geojson_rejects_payload_missing_timestamps_and_features() -> None:
    with pytest.raises(ContractError):
        parse_geojson({"unrelated": "shape"}, station_id="30")


def test_parse_geojson_rejects_mismatched_data_length() -> None:
    payload = _fixture_geojson()
    payload["features"][0]["properties"]["parameters"]["tl_mittel"]["data"] = [1.0, 2.0]

    with pytest.raises(ContractError):
        parse_geojson(payload, station_id="30")


def test_parse_geojson_rejects_missing_tl_mittel_parameter() -> None:
    payload = _fixture_geojson()
    del payload["features"][0]["properties"]["parameters"]["tl_mittel"]

    with pytest.raises(ContractError):
        parse_geojson(payload, station_id="30")


def test_parse_geojson_returns_empty_frame_for_genuinely_empty_window() -> None:
    """Both `timestamps` and `features` present but empty is a real empty
    window (e.g. a future range), not a mis-parse -- must NOT raise (A-2)."""
    frame = parse_geojson({"timestamps": [], "features": []}, station_id="30")

    assert list(frame.columns) == ["date", "station_id", "tl_mittel_c", "parameter_raw"]
    assert frame.empty


def test_parse_geojson_never_returns_empty_frame_on_shape_mismatch() -> None:
    """Distinguishes a mis-parse (raises) from a genuinely empty window
    (returns empty frame) -- timestamps present but features missing is a
    mismatch, not an empty window (RESEARCH Pitfall 5)."""
    with pytest.raises(ContractError):
        parse_geojson({"timestamps": ["2019-01-01T00:00+00:00"], "features": []}, station_id="30")
