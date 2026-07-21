"""Tests for `epra.ingest.entsoe` orchestration: `ingest_dataset`, `backfill`,
`ingest_incremental`, `latest_complete_month`, and the CLI `main()` (ING-001,
ING-002, ING-010, ING-040, ING-041, ING-042, REQ-ING-01).

Every test drives ENTSO-E fetches through the injectable `TransportFn` seam
with committed fixture XML (`tests/fixtures/entsoe/`) -- no network, no
`ENTSOE_API_TOKEN` needed (EN-070). Live backfill is exercised separately in
plan 02-07, gated behind `@pytest.mark.live`.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import pytest

from epra.common.config import Settings
from epra.ingest import _fetch, entsoe
from epra.ingest._fetch import EntsoeQuery
from epra.ingest._io import raw_month_path
from epra.ingest.exceptions import ContractError

FAKE_TOKEN = "test-token-do-not-log"


@pytest.fixture(autouse=True)
def _fake_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ingest_dataset` reaches `fetch_entsoe`, which reads a token even when
    the transport itself is stubbed -- never depend on a real one (A-7)."""
    monkeypatch.setattr(_fetch, "entsoe_token", lambda: FAKE_TOKEN)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip ING-007's politeness sleep so these tests stay fast."""
    monkeypatch.setattr(time, "sleep", lambda s: None)


def _read(fixtures_dir: Path, name: str) -> str:
    return (fixtures_dir / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Task 1: ingest_dataset
# --------------------------------------------------------------------------


def test_ingest_dataset_writes_one_parquet_per_month(
    tmp_settings: Settings, entsoe_fixtures_dir: Path
) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml")

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return xml

    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_prices_at",
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-02-01").date(),
        stub_transport,
    )

    path = raw_month_path("entsoe_prices_at", pd.Timestamp("2024-01-01").date(), tmp_settings)
    assert path.exists()
    frame = pd.read_parquet(path)
    assert list(frame.columns) == [
        "ts_utc",
        "price_eur_mwh",
        "resolution",
        "zone",
        "ingested_at_utc",
        "source",
        "request_hash",
    ]
    assert len(frame) == 4
    assert (frame["zone"] == "AT").all()
    assert (frame["source"] == "entsoe").all()


def test_ingest_dataset_maps_delu_zone(
    tmp_settings: Settings, entsoe_fixtures_dir: Path
) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml")
    xml = xml.replace(
        '<in_Domain.mRID codingScheme="A01">10YAT-APG------L</in_Domain.mRID>',
        '<in_Domain.mRID codingScheme="A01">10Y1001A1001A82H</in_Domain.mRID>',
    ).replace(
        '<out_Domain.mRID codingScheme="A01">10YAT-APG------L</out_Domain.mRID>',
        '<out_Domain.mRID codingScheme="A01">10Y1001A1001A82H</out_Domain.mRID>',
    )

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return xml

    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_prices_delu",
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-02-01").date(),
        stub_transport,
    )

    path = raw_month_path("entsoe_prices_delu", pd.Timestamp("2024-01-01").date(), tmp_settings)
    frame = pd.read_parquet(path)
    assert (frame["zone"] == "DE_LU").all()


def test_ingest_dataset_load_dataset_key(
    tmp_settings: Settings, entsoe_fixtures_dir: Path
) -> None:
    xml = _read(entsoe_fixtures_dir, "load_at.xml")

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return xml

    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_load_at",
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-02-01").date(),
        stub_transport,
    )

    path = raw_month_path("entsoe_load_at", pd.Timestamp("2024-01-01").date(), tmp_settings)
    frame = pd.read_parquet(path)
    assert "load_mw" in frame.columns
    assert (frame["zone"] == "AT").all()


def test_ingest_dataset_generation_dataset_key(
    tmp_settings: Settings, entsoe_fixtures_dir: Path
) -> None:
    xml = _read(entsoe_fixtures_dir, "gen_at.xml")

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return xml

    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_gen_at",
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-02-01").date(),
        stub_transport,
    )

    path = raw_month_path("entsoe_gen_at", pd.Timestamp("2024-01-01").date(), tmp_settings)
    frame = pd.read_parquet(path)
    assert "psr_type" in frame.columns
    assert set(frame["psr_type"]) == {"B16", "B10"}


def test_ingest_dataset_no_data_window_is_skipped_not_raised(
    tmp_settings: Settings, entsoe_fixtures_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    ack_xml = _read(entsoe_fixtures_dir, "acknowledgement.xml")

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return ack_xml

    caplog.set_level(logging.INFO, logger="epra.ingest.entsoe")

    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_prices_at",
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-02-01").date(),
        stub_transport,
    )

    path = raw_month_path("entsoe_prices_at", pd.Timestamp("2024-01-01").date(), tmp_settings)
    assert not path.exists()
    assert any("no data" in r.getMessage() for r in caplog.records)


def test_ingest_dataset_logs_a03_fill_count(
    tmp_settings: Settings, entsoe_fixtures_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_a03_forward_fill.xml")

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return xml

    caplog.set_level(logging.INFO, logger="epra.ingest.entsoe")

    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_prices_at",
        pd.Timestamp("2024-02-01").date(),
        pd.Timestamp("2024-03-01").date(),
        stub_transport,
    )

    assert any("a03_fills=2" in r.getMessage() for r in caplog.records)


def test_ingest_dataset_contract_error_leaves_no_partial_file(
    tmp_settings: Settings, entsoe_fixtures_dir: Path
) -> None:
    bad_xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml").replace(
        "<currency_Unit.name>EUR</currency_Unit.name>",
        "<currency_Unit.name>USD</currency_Unit.name>",
    )

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        return bad_xml

    with pytest.raises(ContractError):
        entsoe.ingest_dataset(
            tmp_settings,
            "entsoe_prices_at",
            pd.Timestamp("2024-01-01").date(),
            pd.Timestamp("2024-02-01").date(),
            stub_transport,
        )

    path = raw_month_path("entsoe_prices_at", pd.Timestamp("2024-01-01").date(), tmp_settings)
    assert not path.exists()
