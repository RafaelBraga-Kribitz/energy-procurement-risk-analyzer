"""Tests for `epra.ingest._io` (ING-003/004/005/070) — the single raw parquet
writer shared by every ENTSO-E dataset: `request_hash`, `raw_month_path`,
`write_month` atomic persistence with contract enforcement at the write
boundary.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from epra.common.config import Settings
from epra.ingest import _io
from epra.ingest.exceptions import ContractError


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


def _geosphere_daily_frame(month: date, *, n: int = 3) -> pd.DataFrame:
    """Minimal `geosphere_graz_daily`-shaped frame for `month` (SPEC-01 §7,
    plain `date`-keyed — no `ts_utc` column)."""
    dates = pd.date_range(
        start=pd.Timestamp(year=month.year, month=month.month, day=1),
        periods=n,
        freq="D",
    )
    return pd.DataFrame(
        {
            "date": dates,
            "station_id": "11290",
            "tl_mittel_c": [4.1, 5.2, 3.9][:n],
            "parameter_raw": "tlmittel",
        }
    )


# ---------------------------------------------------------------- request_hash


def test_request_hash_strips_securitytoken_case_insensitive() -> None:
    base = "https://web-api.tp.entsoe.eu/api?documentType=A44&securityToken=SECRET1"
    other_case_and_token = "https://web-api.tp.entsoe.eu/api?documentType=A44&SecurityToken=SECRET2"
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


# ----------------------------------------------------------------- write_month


def test_write_month_atomic_write_with_contract_columns(tmp_settings: Settings) -> None:
    month = date(2021, 3, 1)
    frame = _prices_frame(month)
    req_hash = _io.request_hash("https://example.test/api?documentType=A44&securityToken=x")

    path = _io.write_month(frame, "entsoe_prices_at", month, req_hash, tmp_settings)

    assert path == _io.raw_month_path("entsoe_prices_at", month, tmp_settings)
    assert path.exists()
    assert not (path.parent / (path.name + ".tmp")).exists()

    out = pd.read_parquet(path)
    assert list(out.columns) == [
        "ts_utc",
        "price_eur_mwh",
        "resolution",
        "zone",
        "ingested_at_utc",
        "source",
        "request_hash",
    ]
    assert (out["source"] == "entsoe").all()
    assert (out["request_hash"] == req_hash).all()
    assert pd.api.types.is_datetime64_any_dtype(out["ts_utc"])
    assert out["price_eur_mwh"].dtype == frame["price_eur_mwh"].dtype
    assert len(out) == len(frame)


def test_write_month_rejects_naive_ts_utc(tmp_settings: Settings) -> None:
    month = date(2021, 3, 1)
    frame = _prices_frame(month)
    frame["ts_utc"] = frame["ts_utc"].dt.tz_localize(None)
    with pytest.raises(ValueError, match="tz-aware"):
        _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)


def test_write_month_rejects_out_of_month_rows(tmp_settings: Settings) -> None:
    month = date(2021, 3, 1)
    frame = _prices_frame(month)
    frame.loc[0, "ts_utc"] = pd.Timestamp("2021-04-01T00:00:00", tz="UTC")
    with pytest.raises(ValueError, match="2021-03"):
        _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)


def test_write_month_rejects_missing_ts_utc_column(tmp_settings: Settings) -> None:
    month = date(2021, 3, 1)
    frame = _prices_frame(month).drop(columns=["ts_utc"])
    with pytest.raises(ContractError, match="ts_utc"):
        _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)


def test_write_month_replaces_via_tmp_file_and_os_replace(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ING-003: writer goes through a `.tmp` file + `os.replace`, not a direct write."""
    month = date(2021, 3, 1)
    frame = _prices_frame(month)
    req_hash = "h" * 64

    replace_calls: list[tuple[str, str]] = []
    real_replace = _io.os.replace

    def _spy_replace(src: object, dst: object) -> None:
        replace_calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(_io.os, "replace", _spy_replace)

    path = _io.write_month(frame, "entsoe_prices_at", month, req_hash, tmp_settings)

    assert len(replace_calls) == 1
    src, dst = replace_calls[0]
    assert src.endswith(".tmp")
    assert dst == str(path)


def test_write_month_tmp_path_is_per_call_unique(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WR-02 regression: two concurrent writers targeting the same month file
    must never share a `.tmp` path -- a shared fixed name defeats the
    temp-file-then-`os.replace` atomicity guarantee if one process's
    partially-written temp file is clobbered/renamed out from under the
    other. Simulated here by capturing the `.tmp` source path from two
    separate `write_month` calls for the same month and asserting they
    differ."""
    month = date(2021, 3, 1)
    frame = _prices_frame(month)

    tmp_srcs: list[str] = []
    real_replace = _io.os.replace

    def _spy_replace(src: object, dst: object) -> None:
        tmp_srcs.append(str(src))
        real_replace(src, dst)

    monkeypatch.setattr(_io.os, "replace", _spy_replace)

    _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)
    _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)

    assert len(tmp_srcs) == 2
    assert tmp_srcs[0] != tmp_srcs[1]
    assert all(src.endswith(".tmp") for src in tmp_srcs)


# --------------------------------------------------------------- idempotency


def test_write_month_idempotent_byte_stable(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ING-003: same input frame + frozen clock => byte-identical re-write.

    `ingested_at_utc` is sourced from `_io._now_utc()`; freezing it via
    monkeypatch is how a re-run with the exact same wall clock is proven
    byte-for-byte identical (rather than treating `ingested_at_utc` as
    excluded from the identity check).
    """
    frozen_now = datetime(2021, 4, 1, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(_io, "_now_utc", lambda: frozen_now)

    month = date(2021, 3, 1)
    frame = _prices_frame(month)
    req_hash = "h" * 64

    path1 = _io.write_month(frame, "entsoe_prices_at", month, req_hash, tmp_settings)
    bytes1 = path1.read_bytes()

    path2 = _io.write_month(frame.copy(), "entsoe_prices_at", month, req_hash, tmp_settings)
    bytes2 = path2.read_bytes()

    assert path1 == path2
    assert bytes1 == bytes2, "re-run with identical input + frozen clock must be byte-identical"


def test_write_month_fixed_column_order_for_determinism(tmp_settings: Settings) -> None:
    """ING-070: writer output column order never depends on kwarg/dict order."""
    month = date(2021, 3, 1)
    frame = _prices_frame(month)[["zone", "ts_utc", "resolution", "price_eur_mwh"]]

    path = _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)
    out = pd.read_parquet(path)

    assert list(out.columns) == [
        "zone",
        "ts_utc",
        "resolution",
        "price_eur_mwh",
        "ingested_at_utc",
        "source",
        "request_hash",
    ]


# ------------------------------------------------------ write_month key_column


def test_write_month_date_key_happy_path(tmp_settings: Settings) -> None:
    """key_column='date': a plain date-keyed frame (GeoSphere §7) writes
    atomically with no tz assertion applied to the key column."""
    month = date(2021, 3, 1)
    frame = _geosphere_daily_frame(month)
    req_hash = _io.request_hash(
        "https://dataset.api.hub.geosphere.at/v1/station/historical/klima-v2-1d"
    )

    path = _io.write_month(
        frame, "geosphere_graz_daily", month, req_hash, tmp_settings, key_column="date"
    )

    assert path == _io.raw_month_path("geosphere_graz_daily", month, tmp_settings)
    assert path.exists()

    out = pd.read_parquet(path)
    assert list(out.columns) == [
        "date",
        "station_id",
        "tl_mittel_c",
        "parameter_raw",
        "ingested_at_utc",
        "source",
        "request_hash",
    ]
    assert (out["source"] == "geosphere").all()
    assert (out["request_hash"] == req_hash).all()
    assert len(out) == len(frame)


def test_write_month_date_key_rejects_missing_date_column(tmp_settings: Settings) -> None:
    month = date(2021, 3, 1)
    frame = _geosphere_daily_frame(month).drop(columns=["date"])
    with pytest.raises(ContractError, match="date"):
        _io.write_month(
            frame, "geosphere_graz_daily", month, "h" * 64, tmp_settings, key_column="date"
        )


def test_write_month_date_key_rejects_out_of_month_rows(tmp_settings: Settings) -> None:
    month = date(2021, 3, 1)
    frame = _geosphere_daily_frame(month)
    frame.loc[0, "date"] = pd.Timestamp("2021-04-01")
    with pytest.raises(ValueError, match="2021-03"):
        _io.write_month(
            frame, "geosphere_graz_daily", month, "h" * 64, tmp_settings, key_column="date"
        )


def test_write_month_date_key_applies_no_timezone_assertion(tmp_settings: Settings) -> None:
    """A plain (tz-naive) `date` column must be accepted as-is -- no UTC
    assertion is applied on the date-key path (unlike the ts_utc path)."""
    month = date(2021, 3, 1)
    frame = _geosphere_daily_frame(month)
    assert frame["date"].dt.tz is None

    path = _io.write_month(
        frame, "geosphere_graz_daily", month, "h" * 64, tmp_settings, key_column="date"
    )
    assert path.exists()


def test_write_month_round_trip_both_key_modes_preserve_provenance_order(
    tmp_settings: Settings,
) -> None:
    """Both a ts_utc-keyed frame and a date-keyed frame round-trip through
    write_month with the frame's own columns followed by the fixed ING-004
    provenance column order."""
    month = date(2021, 3, 1)

    ts_frame = _prices_frame(month)
    ts_path = _io.write_month(ts_frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)
    ts_out = pd.read_parquet(ts_path)
    assert list(ts_out.columns) == [*ts_frame.columns, *_io._PROVENANCE_COLUMNS]

    date_frame = _geosphere_daily_frame(month)
    date_path = _io.write_month(
        date_frame, "geosphere_graz_daily", month, "h" * 64, tmp_settings, key_column="date"
    )
    date_out = pd.read_parquet(date_path)
    assert list(date_out.columns) == [*date_frame.columns, *_io._PROVENANCE_COLUMNS]


def test_write_month_default_key_column_still_rejects_missing_ts_utc(
    tmp_settings: Settings,
) -> None:
    """Regression: the default (no key_column passed) call path is unchanged
    -- missing ts_utc still raises ContractError."""
    month = date(2021, 3, 1)
    frame = _prices_frame(month).drop(columns=["ts_utc"])
    with pytest.raises(ContractError, match="ts_utc"):
        _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)


def test_write_month_default_key_column_still_rejects_naive_ts_utc(
    tmp_settings: Settings,
) -> None:
    """Regression: the default (no key_column passed) call path is unchanged
    -- naive ts_utc still raises ValueError."""
    month = date(2021, 3, 1)
    frame = _prices_frame(month)
    frame["ts_utc"] = frame["ts_utc"].dt.tz_localize(None)
    with pytest.raises(ValueError, match="tz-aware"):
        _io.write_month(frame, "entsoe_prices_at", month, "h" * 64, tmp_settings)
