"""Unit tests for `epra.ingest._fetch` — cache, retry, politeness, and
secret-safe logging (ING-006, ING-007, ING-008, ING-009, ING-021, ING-030).

No test in this module hits the real ENTSO-E API (EN-070): every test
injects a stub `transport` per ADR-003's "test doubles stub
`EntsoeRawClient.query_*`" note, and a fake token via an autouse fixture so
these tests never depend on a real `ENTSOE_API_TOKEN` being present in the
environment (A-7).

This first slice covers `EntsoeQuery`'s window validation (ING-030) only;
`fetch_entsoe` tests land in a following commit.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from epra.ingest._fetch import EntsoeQuery


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
