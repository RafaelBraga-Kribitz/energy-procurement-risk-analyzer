"""Unit tests for `epra.ingest._fetch` — cache, retry, politeness, and
secret-safe logging (ING-006, ING-007, ING-008, ING-009, ING-021, ING-030).

No test in this module hits the real ENTSO-E API (EN-070): every test
injects a stub `transport` per ADR-003's "test doubles stub
`EntsoeRawClient.query_*`" note, and a fake token via an autouse fixture so
these tests never depend on a real `ENTSOE_API_TOKEN` being present in the
environment (A-7).

"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from epra.common.config import Settings
from epra.ingest import _fetch
from epra.ingest._fetch import EntsoeQuery, fetch_entsoe
from epra.ingest._io import request_hash
from epra.ingest.exceptions import IngestAuthError, IngestTransportError

FAKE_TOKEN = "test-token-do-not-log"


@pytest.fixture(autouse=True)
def _fake_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test uses a deterministic fake token — never a real one (A-7)."""
    monkeypatch.setattr(_fetch, "entsoe_token", lambda: FAKE_TOKEN)


@pytest.fixture(autouse=True)
def _sleep_calls(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Patch the process-wide `time.sleep` (also what tenacity's `nap`
    strategy calls) so tests never actually wait, and record durations for
    the politeness-sleep assertion."""
    calls: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: calls.append(s))
    return calls


def _query(**overrides: Any) -> EntsoeQuery:
    defaults: dict[str, Any] = {
        "document_type": "day_ahead_prices",
        "domain": "10YAT-APG------L",
        "period_start": datetime(2024, 1, 1, tzinfo=UTC),
        "period_end": datetime(2024, 1, 31, tzinfo=UTC),
    }
    defaults.update(overrides)
    return EntsoeQuery(**defaults)


def _old_window(**overrides: Any) -> EntsoeQuery:
    """A window that ends well over 7 days ago — always cache-eligible."""
    defaults: dict[str, Any] = {
        "period_start": datetime.now(UTC) - timedelta(days=20),
        "period_end": datetime.now(UTC) - timedelta(days=10),
    }
    defaults.update(overrides)
    return _query(**defaults)


def _http_error(status: int, text: str = "error") -> requests.exceptions.HTTPError:
    response = Mock(status_code=status, text=text)
    return requests.exceptions.HTTPError(f"{status} error", response=response)


# --------------------------------------------------------------------------
# Task 1: EntsoeQuery
# --------------------------------------------------------------------------


def test_entsoe_query_accepts_valid_window() -> None:
    q = _query()
    assert q.period_end > q.period_start


def test_entsoe_query_accepts_exactly_90_day_window() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    q = _query(period_start=start, period_end=start + timedelta(days=90))
    assert q.period_end - q.period_start == timedelta(days=90)


def test_entsoe_query_is_frozen() -> None:
    q = _query()
    with pytest.raises(AttributeError):
        q.domain = "10Y1001A1001A82H"  # type: ignore[misc]


def test_entsoe_query_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="must be after"):
        _query(
            period_start=datetime(2024, 2, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 1, tzinfo=UTC),
        )


def test_entsoe_query_rejects_equal_start_and_end() -> None:
    same = datetime(2024, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="must be after"):
        _query(period_start=same, period_end=same)


def test_entsoe_query_rejects_window_over_90_days() -> None:
    with pytest.raises(ValueError, match="90-day"):
        _query(
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 5, 1, tzinfo=UTC),
        )


def test_entsoe_query_rejects_naive_start() -> None:
    with pytest.raises(ValueError, match="tz-aware"):
        _query(period_start=datetime(2024, 1, 1))


def test_entsoe_query_rejects_naive_end() -> None:
    with pytest.raises(ValueError, match="tz-aware"):
        _query(period_end=datetime(2024, 1, 31))


# --------------------------------------------------------------------------
# Task 2: fetch_entsoe — cache, retry, politeness, logging
# --------------------------------------------------------------------------


def test_fetch_entsoe_live_writes_cache_file(tmp_settings: Settings) -> None:
    calls: list[tuple[EntsoeQuery, str]] = []

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        calls.append((query, api_key))
        return "<xml>ok</xml>"

    q = _old_window()
    xml = fetch_entsoe(q, tmp_settings, transport=stub_transport)

    assert xml == "<xml>ok</xml>"
    assert len(calls) == 1
    assert calls[0][1] == FAKE_TOKEN

    cache_dir = tmp_settings.paths.data_cache / "entsoe"
    cache_files = list(cache_dir.glob("*.bin"))
    assert len(cache_files) == 1
    assert cache_files[0].read_text(encoding="utf-8") == "<xml>ok</xml>"


def test_fetch_entsoe_uses_cache_when_window_old_enough(tmp_settings: Settings) -> None:
    calls: list[int] = []

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        calls.append(1)
        return "<xml>first</xml>"

    q = _old_window()
    first = fetch_entsoe(q, tmp_settings, transport=stub_transport)
    second = fetch_entsoe(q, tmp_settings, transport=stub_transport)

    assert first == second == "<xml>first</xml>"
    assert len(calls) == 1  # second call served from cache, no network


def test_fetch_entsoe_use_cache_false_always_hits_network(tmp_settings: Settings) -> None:
    calls: list[int] = []

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        calls.append(1)
        return f"<xml>{len(calls)}</xml>"

    q = _old_window()
    fetch_entsoe(q, tmp_settings, transport=stub_transport)
    second = fetch_entsoe(q, tmp_settings, use_cache=False, transport=stub_transport)

    assert len(calls) == 2
    assert second == "<xml>2</xml>"


def test_fetch_entsoe_ignores_cache_for_recent_window(tmp_settings: Settings) -> None:
    # Window ends within the last 7 days -> ING-009's cache rule does not
    # apply even though a (stale) cache file already exists for this key.
    q = _query(
        period_start=datetime.now(UTC) - timedelta(days=3),
        period_end=datetime.now(UTC) - timedelta(days=1),
    )
    req_hash = request_hash(_fetch._cache_request_url(q, FAKE_TOKEN))
    cache_file = _fetch._cache_path(tmp_settings, req_hash)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("<xml>stale-should-not-be-used</xml>", encoding="utf-8")

    calls: list[int] = []

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        calls.append(1)
        return "<xml>live</xml>"

    result = fetch_entsoe(q, tmp_settings, transport=stub_transport)

    assert result == "<xml>live</xml>"
    assert len(calls) == 1


def test_fetch_entsoe_retries_429_then_succeeds(tmp_settings: Settings) -> None:
    attempts = {"n": 0}

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _http_error(429, text="rate limited")
        return "<xml>ok</xml>"

    xml = fetch_entsoe(_old_window(), tmp_settings, transport=stub_transport)

    assert xml == "<xml>ok</xml>"
    assert attempts["n"] == 3


def test_fetch_entsoe_retries_connection_error_then_succeeds(tmp_settings: Settings) -> None:
    attempts = {"n": 0}

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise requests.exceptions.ConnectionError("connection reset")
        return "<xml>ok</xml>"

    xml = fetch_entsoe(_old_window(), tmp_settings, transport=stub_transport)

    assert xml == "<xml>ok</xml>"
    assert attempts["n"] == 2


def test_fetch_entsoe_5xx_exhausts_retries_raises_transport_error(tmp_settings: Settings) -> None:
    attempts = {"n": 0}

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        attempts["n"] += 1
        raise _http_error(503, text="unavailable")

    with pytest.raises(IngestTransportError, match="503"):
        fetch_entsoe(_old_window(), tmp_settings, transport=stub_transport)

    assert attempts["n"] == 6  # tenacity stop_after_attempt(6), ING-006


def test_fetch_entsoe_401_raises_auth_error_without_retry(tmp_settings: Settings) -> None:
    attempts = {"n": 0}

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        attempts["n"] += 1
        raise _http_error(401, text="invalid token")

    with pytest.raises(IngestAuthError, match="401"):
        fetch_entsoe(_old_window(), tmp_settings, transport=stub_transport)

    assert attempts["n"] == 1  # never retried


def test_fetch_entsoe_403_raises_auth_error_without_retry(tmp_settings: Settings) -> None:
    attempts = {"n": 0}

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        attempts["n"] += 1
        raise _http_error(403, text="forbidden")

    with pytest.raises(IngestAuthError, match="403"):
        fetch_entsoe(_old_window(), tmp_settings, transport=stub_transport)

    assert attempts["n"] == 1


def test_fetch_entsoe_400_raises_transport_error_without_retry(tmp_settings: Settings) -> None:
    attempts = {"n": 0}

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        attempts["n"] += 1
        raise _http_error(400, text="malformed request")

    with pytest.raises(IngestTransportError, match="400"):
        fetch_entsoe(_old_window(), tmp_settings, transport=stub_transport)

    assert attempts["n"] == 1


def test_fetch_entsoe_sleeps_between_live_calls(
    tmp_settings: Settings, _sleep_calls: list[float]
) -> None:
    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return "<xml>ok</xml>"

    q1 = _old_window()
    q2 = _old_window(domain="10Y1001A1001A82H")  # distinct cache key -> also live

    fetch_entsoe(q1, tmp_settings, transport=stub_transport)
    fetch_entsoe(q2, tmp_settings, transport=stub_transport)

    assert _sleep_calls, "expected a politeness sleep after each live call"
    assert all(s >= 0.5 for s in _sleep_calls)


def test_fetch_entsoe_cache_hit_does_not_sleep(
    tmp_settings: Settings, _sleep_calls: list[float]
) -> None:
    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return "<xml>ok</xml>"

    q = _old_window()
    fetch_entsoe(q, tmp_settings, transport=stub_transport)
    _sleep_calls.clear()  # discard the sleep from the live fetch above

    fetch_entsoe(q, tmp_settings, transport=stub_transport)  # served from cache

    assert _sleep_calls == []


def test_fetch_entsoe_logs_no_token(
    tmp_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="epra.ingest._fetch")

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return "<xml>ok</xml>"

    fetch_entsoe(_old_window(), tmp_settings, transport=stub_transport)

    messages = [r.getMessage() for r in caplog.records]
    assert any("source=entsoe" in m and "status=200" in m for m in messages)
    assert all(FAKE_TOKEN not in m for m in messages)


# --------------------------------------------------------------------------
# Task 3: token fail-fast (ING-021)
# --------------------------------------------------------------------------


def test_fetch_entsoe_fails_without_token(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_unset() -> str:
        raise RuntimeError("ENTSOE_API_TOKEN is not set. Copy .env.example to .env ...")

    monkeypatch.setattr(_fetch, "entsoe_token", _raise_unset)

    calls: list[int] = []

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        calls.append(1)
        return "<xml>should not be reached</xml>"

    with pytest.raises(RuntimeError, match="ENTSOE_API_TOKEN"):
        fetch_entsoe(_query(), tmp_settings, transport=stub_transport)

    assert calls == []  # fails before any network call (ING-021)
