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
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import epra.ingest.geosphere as geosphere_module
from epra.common.config import Settings, load_settings
from epra.ingest.exceptions import ContractError, DiscoveryError
from epra.ingest.geosphere import (
    StationInfo,
    _fetch_geosphere,
    discover_station,
    ingest,
    parse_geojson,
)

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


# ---------------------------------------------------------------------------
# _fetch_geosphere (ING-093) — ING-009 cache + ING-007 politeness sleep
# ---------------------------------------------------------------------------


@pytest.fixture
def _sleep_calls(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    calls: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: calls.append(s))
    return calls


def test_fetch_geosphere_live_writes_cache_file(tmp_settings: Settings) -> None:
    payload = _fixture_geojson()
    calls: list[int] = []

    def stub_transport(settings: Settings, station_id: str, month: date) -> Any:
        calls.append(1)
        return payload

    result = _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=stub_transport)

    assert result == payload
    assert len(calls) == 1
    cache_dir = tmp_settings.paths.data_cache / "geosphere"
    assert len(list(cache_dir.glob("*.json"))) == 1


def test_fetch_geosphere_uses_cache_on_second_call(tmp_settings: Settings) -> None:
    payload = _fixture_geojson()
    calls: list[int] = []

    def stub_transport(settings: Settings, station_id: str, month: date) -> Any:
        calls.append(1)
        return payload

    first = _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=stub_transport)
    second = _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=stub_transport)

    assert first == second == payload
    assert len(calls) == 1  # second call served from cache, no network


def test_fetch_geosphere_sleeps_after_live_call_not_cache_hit(
    tmp_settings: Settings, _sleep_calls: list[float]
) -> None:
    payload = _fixture_geojson()

    def stub_transport(settings: Settings, station_id: str, month: date) -> Any:
        return payload

    _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=stub_transport)
    assert _sleep_calls, "expected a politeness sleep after the live call"
    assert all(s >= 0.2 for s in _sleep_calls)

    _sleep_calls.clear()
    _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=stub_transport)  # cache hit
    assert _sleep_calls == []


# ---------------------------------------------------------------------------
# ingest (ING-093)
# ---------------------------------------------------------------------------


def test_ingest_writes_geosphere_graz_daily_monthly_parquet(tmp_settings: Settings) -> None:
    payload = _fixture_geojson()

    def stub_transport(settings: Settings, station_id: str, month: date) -> Any:
        return payload

    ingest(tmp_settings, date(2019, 1, 1), date(2019, 1, 31), transport=stub_transport)

    path = (
        tmp_settings.paths.data_raw
        / "geosphere_graz_daily"
        / "2019"
        / "geosphere_graz_daily_2019-01.parquet"
    )
    assert path.exists()
    frame = pd.read_parquet(path)
    assert list(frame.columns) == [
        "date",
        "station_id",
        "tl_mittel_c",
        "parameter_raw",
        "ingested_at_utc",
        "source",
        "request_hash",
    ]
    assert len(frame) == 31
    assert (frame["source"] == "geosphere").all()


def test_ingest_fails_fast_when_station_id_unset(tmp_settings: Settings) -> None:
    settings = tmp_settings.model_copy(
        update={"geosphere": tmp_settings.geosphere.model_copy(update={"station_id": None})}
    )

    with pytest.raises(DiscoveryError):
        ingest(settings, date(2019, 1, 1), date(2019, 1, 31))


# ---------------------------------------------------------------------------
# main (ING-002)
# ---------------------------------------------------------------------------


def test_main_rejects_malformed_date() -> None:
    with pytest.raises(SystemExit):
        geosphere_module.main(["--start", "not-a-date"])


def test_main_invokes_ingest_with_explicit_window(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geosphere_module, "load_settings", lambda: tmp_settings)
    captured: dict[str, object] = {}

    def fake_ingest(settings: Settings, start: date, end: date, transport: Any = None) -> None:
        captured["settings"] = settings
        captured["start"] = start
        captured["end"] = end

    monkeypatch.setattr(geosphere_module, "ingest", fake_ingest)

    code = geosphere_module.main(["--start", "2019-01-01", "--end", "2019-02-01"])

    assert code == 0
    assert captured == {
        "settings": tmp_settings,
        "start": date(2019, 1, 1),
        "end": date(2019, 2, 1),
    }


def test_main_defaults_start_and_end(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geosphere_module, "load_settings", lambda: tmp_settings)
    captured: dict[str, object] = {}

    def fake_ingest(settings: Settings, start: date, end: date, transport: Any = None) -> None:
        captured["start"] = start
        captured["end"] = end

    monkeypatch.setattr(geosphere_module, "ingest", fake_ingest)

    code = geosphere_module.main([])

    assert code == 0
    assert captured["start"] == tmp_settings.window.start_date
    assert captured["end"] == date.today()


def test_main_rejects_inverted_window(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geosphere_module, "load_settings", lambda: tmp_settings)

    def fake_ingest(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("ingest should not be called on an inverted window")

    monkeypatch.setattr(geosphere_module, "ingest", fake_ingest)

    code = geosphere_module.main(["--start", "2020-02-01", "--end", "2020-01-01"])

    assert code == 1


def test_main_returns_1_when_station_id_unset(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geosphere_module, "load_settings", lambda: tmp_settings)

    def fake_ingest(settings: Settings, start: date, end: date, transport: Any = None) -> None:
        raise DiscoveryError("geosphere", "station_id unset")

    monkeypatch.setattr(geosphere_module, "ingest", fake_ingest)

    code = geosphere_module.main(["--start", "2019-01-01", "--end", "2019-02-01"])

    assert code == 1
