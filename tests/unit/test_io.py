"""Tests for `epra.ingest._io` (ING-003/004/005/070) — the single raw parquet
writer shared by every ENTSO-E dataset: `request_hash`, `raw_month_path`,
`write_month` atomic persistence with contract enforcement at the write
boundary.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from epra.common.config import Settings
from epra.ingest import _io


def _prices_frame(month: date, *, n: int = 3) -> pd.DataFrame:
    """Minimal `entsoe_prices_at`-shaped frame for `month` (SPEC-01 §7)."""
    ts = pd.date_range(
        start=pd.Timestamp(year=month.year, month=month.month, day=1, tz="UTC"),
        periods=n,
        freq="h",
    )
    return pd.DataFrame(
        {
            "ts_utc": ts,
            "price_eur_mwh": [45.1, 46.2, 44.9][:n],
            "resolution": "PT60M",
            "zone": "AT",
        }
    )


# ---------------------------------------------------------------- request_hash


def test_request_hash_strips_securitytoken_case_insensitive() -> None:
    base = "https://web-api.tp.entsoe.eu/api?documentType=A44&securityToken=SECRET1"
    other_case_and_token = (
        "https://web-api.tp.entsoe.eu/api?documentType=A44&SecurityToken=SECRET2"
    )
    assert _io.request_hash(base) == _io.request_hash(other_case_and_token)


def test_request_hash_is_stable_64_hex_digest() -> None:
    h = _io.request_hash("https://example.test/api?a=1")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
    assert h == _io.request_hash("https://example.test/api?a=1")


def test_request_hash_differs_for_different_urls() -> None:
    a = _io.request_hash("https://example.test/api?documentType=A44")
    b = _io.request_hash("https://example.test/api?documentType=A65")
    assert a != b


def test_request_hash_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        _io.request_hash("")


# ------------------------------------------------------------- raw_month_path


def test_raw_month_path_matches_spec01_section7_layout(tmp_settings: Settings) -> None:
    month = date(2021, 3, 1)
    path = _io.raw_month_path("entsoe_prices_at", month, tmp_settings)
    expected = (
        tmp_settings.paths.data_raw
        / "entsoe_prices_at"
        / "2021"
        / "entsoe_prices_at_2021-03.parquet"
    )
    assert path == expected


def test_raw_month_path_rejects_path_traversal_dataset(tmp_settings: Settings) -> None:
    with pytest.raises(ValueError, match="safe filesystem identifier"):
        _io.raw_month_path("../../etc/passwd", date(2021, 1, 1), tmp_settings)
