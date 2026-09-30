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
from typing import Any, cast

import pandas as pd
import pytest

import epra.ingest.geosphere as geosphere_module
from epra.common import logging as common_logging
from epra.common.config import REPO_ROOT, Settings, load_settings
from epra.common.timeutil import iter_month_starts, today_local
from epra.ingest.exceptions import ContractError, DiscoveryError, IngestTransportError
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
    return cast(dict[str, Any], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


def _fixture_geojson() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(GEOJSON_FIXTURE_PATH.read_text(encoding="utf-8")))


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
    assert captured["end"] == today_local()


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


# ---------------------------------------------------------------------------
# Audit 2026-09-30 §5: the GeoSphere pull ended at 2023-12 although ING-093
# says 2019 -> latest. These pin down the code paths that could truncate a
# pull: year-boundary chunking, empty months, transient HTTP errors, and
# stale-cache replay.
# ---------------------------------------------------------------------------


def _month_payload(month: date, value: float = 5.0) -> dict[str, Any]:
    """Synthetic GeoSphere-shaped payload: one `tl_mittel` value per day of `month`."""
    days = pd.date_range(month, periods=geosphere_module._month_end(month).day, freq="D")
    return {
        "type": "FeatureCollection",
        "timestamps": [f"{d:%Y-%m-%d}T00:00+00:00" for d in days],
        "features": [{"properties": {"parameters": {"tl_mittel": {"data": [value] * len(days)}}}}],
    }


class _HTTPError(Exception):
    """`requests.HTTPError`-shaped stand-in carrying ``.response.status_code``/``.text``."""

    def __init__(self, status: int, text: str = "boom") -> None:
        super().__init__(f"HTTP {status}")
        self.response = type("R", (), {"status_code": status, "text": text})()


def test_ingest_crosses_year_boundary_without_truncating(tmp_settings: Settings) -> None:
    """Nothing in the month loop stops at a year end: 2023-11 -> 2024-02 writes all four."""

    def stub_transport(settings: Settings, station_id: str, month: date) -> Any:
        return _month_payload(month)

    written = ingest(tmp_settings, date(2023, 11, 1), date(2024, 2, 15), transport=stub_transport)

    assert written == [date(2023, 11, 1), date(2023, 12, 1), date(2024, 1, 1), date(2024, 2, 1)]
    root = tmp_settings.paths.data_raw / "geosphere_graz_daily"
    assert sorted(p.name for p in root.glob("*/*.parquet")) == [
        "geosphere_graz_daily_2023-11.parquet",
        "geosphere_graz_daily_2023-12.parquet",
        "geosphere_graz_daily_2024-01.parquet",
        "geosphere_graz_daily_2024-02.parquet",
    ]


def test_ingest_warns_and_summarises_empty_months(
    tmp_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """An empty response is never skipped silently: WARNING per month + summary line."""

    def stub_transport(settings: Settings, station_id: str, month: date) -> Any:
        if month >= date(2024, 1, 1):
            return {"timestamps": [], "features": []}
        return _month_payload(month)

    with caplog.at_level("INFO", logger="epra.ingest.geosphere"):
        written = ingest(
            tmp_settings, date(2023, 12, 1), date(2024, 2, 1), transport=stub_transport
        )

    assert written == [date(2023, 12, 1)]
    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert any("2024-01" in m for m in warnings)
    assert any("2024-02" in m for m in warnings)
    summary = [r.getMessage() for r in caplog.records if "months_written=" in r.getMessage()]
    assert summary == [
        "dataset=geosphere_graz_daily requested=2023-12-01..2024-02-01 months_written=1 "
        "last_written=2023-12 empty_months=['2024-01', '2024-02']"
    ]


def test_fetch_geosphere_does_not_cache_a_not_yet_eligible_month(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ING-009: a response for a month that ended < 7 days ago may be incomplete; it must not
    be persisted and later replayed once the month becomes cache-eligible."""
    month = date(2024, 1, 1)
    now = {"value": pd.Timestamp("2024-02-03T12:00", tz="UTC").to_pydatetime()}
    monkeypatch.setattr(geosphere_module, "_now_utc", lambda: now["value"])
    calls: list[int] = []

    def stub_transport(settings: Settings, station_id: str, m: date) -> Any:
        calls.append(1)
        return _month_payload(m, value=float(len(calls)))

    first = _fetch_geosphere(tmp_settings, "30", month, transport=stub_transport)
    assert not list((tmp_settings.paths.data_cache / "geosphere").glob("*.json"))

    now["value"] = pd.Timestamp("2024-03-01T12:00", tz="UTC").to_pydatetime()  # now eligible
    second = _fetch_geosphere(tmp_settings, "30", month, transport=stub_transport)
    third = _fetch_geosphere(tmp_settings, "30", month, transport=stub_transport)

    assert len(calls) == 2  # re-fetched once eligible, then served from cache
    assert first != second == third


def test_fetch_geosphere_retries_transient_errors(
    tmp_settings: Settings, _sleep_calls: list[float]
) -> None:
    """ING-006: 503/429 are retried, so one transient error cannot cut a pull short."""
    failures = [_HTTPError(503), _HTTPError(429)]

    def flaky_transport(settings: Settings, station_id: str, month: date) -> Any:
        if failures:
            raise failures.pop(0)
        return _month_payload(month)

    payload = _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=flaky_transport)

    assert payload == _month_payload(date(2019, 1, 1))
    assert failures == []


def test_fetch_geosphere_does_not_retry_400_and_raises_ingest_error(
    tmp_settings: Settings, _sleep_calls: list[float]
) -> None:
    calls: list[int] = []

    def bad_request(settings: Settings, station_id: str, month: date) -> Any:
        calls.append(1)
        raise _HTTPError(400, "end date out of range")

    with pytest.raises(IngestTransportError) as excinfo:
        _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=bad_request)

    assert calls == [1]
    assert excinfo.value.status_code == 400
    assert "end date out of range" in str(excinfo.value)
    assert "month=2019-01" in str(excinfo.value)


def test_fetch_geosphere_raises_ingest_error_after_exhausted_retries(
    tmp_settings: Settings, _sleep_calls: list[float]
) -> None:
    calls: list[int] = []

    def always_503(settings: Settings, station_id: str, month: date) -> Any:
        calls.append(1)
        raise _HTTPError(503)

    with pytest.raises(IngestTransportError):
        _fetch_geosphere(tmp_settings, "30", date(2019, 1, 1), transport=always_503)
    assert len(calls) == 6  # stop_after_attempt(6), ING-006


def test_main_returns_1_on_transport_failure(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geosphere_module, "load_settings", lambda: tmp_settings)

    def failing_ingest(settings: Settings, start: date, end: date, transport: Any = None) -> None:
        raise IngestTransportError("geosphere", "month=2024-01 status=503: boom", 503)

    monkeypatch.setattr(geosphere_module, "ingest", failing_ingest)

    assert geosphere_module.main(["--start", "2019-01-01", "--end", "2024-02-01"]) == 1


def test_main_anchors_relative_reports_path_at_repo_root(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The logfile path never depends on the caller's cwd (audit 2026-09-30 §2)."""
    relative = tmp_settings.model_copy(
        update={"paths": tmp_settings.paths.model_copy(update={"reports": Path("reports")})}
    )
    monkeypatch.setattr(geosphere_module, "load_settings", lambda: relative)
    monkeypatch.setattr(geosphere_module, "ingest", lambda *a, **k: [])
    captured: dict[str, Path | None] = {}
    monkeypatch.setattr(
        common_logging,
        "setup",
        lambda logfile=None, **_: captured.update(logfile=logfile),
    )

    assert geosphere_module.main(["--start", "2019-01-01", "--end", "2019-02-01"]) == 0
    assert captured["logfile"] == (
        REPO_ROOT / "reports" / "ingestion" / f"geosphere_{today_local():%Y-%m-%d}.log"
    )


def test_month_loop_covers_every_month_to_the_requested_end() -> None:
    """ING-093 chunking: 2019-01-01 -> 2026-09-30 is 93 consecutive months, no cap."""
    months = list(iter_month_starts(date(2019, 1, 1), date(2026, 9, 30)))
    assert len(months) == 93
    assert months[0] == date(2019, 1, 1)
    assert months[-1] == date(2026, 9, 1)
