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
from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

import pandas as pd
import pytest

from epra.common.config import Settings
from epra.ingest import _fetch, entsoe
from epra.ingest._fetch import EntsoeQuery
from epra.ingest._io import raw_month_path, write_month
from epra.ingest.exceptions import ContractError, NoDataError

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
# Task 0: iter_chunks (ING-030 <= 90-day bound; CR-01 regression coverage)
# --------------------------------------------------------------------------


def test_iter_chunks_never_exceeds_90_days_across_2019_2025() -> None:
    """Sweep the whole real backfill range (settings.window.start_date =
    2019-01-01 through a generous 2025 end) and assert every yielded window
    satisfies ING-030's <= 90-day limit -- the exact bound `EntsoeQuery`
    enforces in `_fetch.py`."""
    chunks = list(entsoe.iter_chunks(date(2019, 1, 1), date(2025, 12, 31)))

    assert chunks, "expected at least one chunk"
    for chunk_start, chunk_end in chunks:
        assert (chunk_end - chunk_start).days <= 90


def test_iter_chunks_covers_full_window_with_no_gaps_or_overlaps() -> None:
    chunks = list(entsoe.iter_chunks(date(2019, 1, 1), date(2025, 12, 31)))

    assert chunks[0][0] == date(2019, 1, 1)
    assert chunks[-1][1] == date(2026, 1, 1)
    for (_, prev_end), (next_start, _) in pairwise(chunks):
        assert prev_end == next_start  # contiguous: no gap, no overlap


def test_iter_chunks_apr_may_jun_91_day_span_is_split_not_rejected() -> None:
    """Regression for CR-01: Apr+May+Jun 2019 is a 91-day calendar span (a
    fixed group-of-3 chunking would yield a window `EntsoeQuery.__post_init__`
    rejects as exceeding ING-030's 90-day maximum). The fix must instead
    split it into <= 90-day windows that still cover Apr 1 -> Jul 1 exactly.
    """
    chunks = list(entsoe.iter_chunks(date(2019, 4, 1), date(2019, 6, 30)))

    for chunk_start, chunk_end in chunks:
        assert (chunk_end - chunk_start).days <= 90
    assert chunks[0][0] == date(2019, 4, 1)
    assert chunks[-1][1] == date(2019, 7, 1)


def test_iter_chunks_second_backfill_chunk_from_real_start_date_is_valid() -> None:
    """Regression for CR-01: with the real production start date
    (2019-01-01, per `config/settings.yaml`), the *second* yielded chunk used
    to be Apr 1 -> Jul 1, 2019 (91 days), which crashed `EntsoeQuery`
    construction on the very first `make backfill` run."""
    chunks = list(entsoe.iter_chunks(date(2019, 1, 1), date(2019, 12, 31)))

    assert len(chunks) >= 2
    second_start, second_end = chunks[1]
    assert (second_end - second_start).days <= 90
    # Every chunk must also be constructible as a real EntsoeQuery window.
    for chunk_start, chunk_end in chunks:
        assert (chunk_end - chunk_start) <= timedelta(days=90)


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


def test_ingest_dataset_maps_delu_zone(tmp_settings: Settings, entsoe_fixtures_dir: Path) -> None:
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


def test_ingest_dataset_load_dataset_key(tmp_settings: Settings, entsoe_fixtures_dir: Path) -> None:
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
    ack = _read(entsoe_fixtures_dir, "acknowledgement.xml")

    # The fixture covers less than the requested window, so ingest_dataset's
    # 100-document pagination will request the remainder; return a no-data
    # Acknowledgement for that follow-up so fills are counted exactly once.
    calls = {"n": 0}

    def stub_transport(query: EntsoeQuery, api_key: str) -> str:
        calls["n"] += 1
        return xml if calls["n"] == 1 else ack

    caplog.set_level(logging.INFO, logger="epra.ingest.entsoe")

    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_prices_at",
        pd.Timestamp("2024-02-01").date(),
        pd.Timestamp("2024-03-01").date(),
        stub_transport,
    )

    assert any("a03_fills=2" in r.getMessage() for r in caplog.records)


def _synth_prices_xml(start_utc: pd.Timestamp, n_days: int) -> str:
    """Minimal valid A44 publication doc: one PT60M Period of `n_days` days."""
    n_points = n_days * 24
    s = start_utc.strftime("%Y-%m-%dT%H:%MZ")
    e = (start_utc + pd.Timedelta(days=n_days)).strftime("%Y-%m-%dT%H:%MZ")
    points = "".join(
        f"<Point><position>{p}</position><price.amount>{40.0 + (p % 24)}</price.amount></Point>"
        for p in range(1, n_points + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Publication_MarketDocument "
        'xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">'
        "<mRID>synth</mRID><type>A44</type>"
        f"<period.timeInterval><start>{s}</start><end>{e}</end></period.timeInterval>"
        "<TimeSeries><mRID>1</mRID><businessType>A62</businessType>"
        '<in_Domain.mRID codingScheme="A01">10YAT-APG------L</in_Domain.mRID>'
        '<out_Domain.mRID codingScheme="A01">10YAT-APG------L</out_Domain.mRID>'
        "<currency_Unit.name>EUR</currency_Unit.name>"
        "<price_Measure_Unit.name>MWH</price_Measure_Unit.name><curveType>A01</curveType>"
        f"<Period><timeInterval><start>{s}</start><end>{e}</end></timeInterval>"
        f"<resolution>PT60M</resolution>{points}</Period></TimeSeries></Publication_MarketDocument>"
    )


def test_ingest_dataset_pages_past_100_document_cap(
    tmp_settings: Settings, entsoe_fixtures_dir: Path
) -> None:
    """A truncating transport (ENTSO-E's 100-doc cap) must not drop months.

    Regression: a wide window was silently truncated to its first ~50 days, and
    a later chunk's UTC-boundary sliver overwrote an earlier chunk's full month,
    leaving interior months (e.g. February) with ~0 hours on real backfills.
    """
    ack = _read(entsoe_fixtures_dir, "acknowledgement.xml")
    cap_days = 20  # each response covers at most 20 days, like the real cap

    def capped_transport(query: EntsoeQuery, api_key: str) -> str:
        start = pd.Timestamp(query.period_start)
        end = pd.Timestamp(query.period_end)
        remaining = int((end - start) / pd.Timedelta(days=1))
        n = min(cap_days, remaining)
        if n <= 0:
            return ack
        return _synth_prices_xml(start, n)

    # Two-month window -> one 59-day chunk -> must page ~3x to cover it.
    entsoe.ingest_dataset(
        tmp_settings,
        "entsoe_prices_at",
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-03-01").date(),
        capped_transport,
    )

    feb = (
        tmp_settings.paths.data_raw
        / "entsoe_prices_at"
        / "2024"
        / "entsoe_prices_at_2024-02.parquet"
    )
    assert feb.exists(), "interior month February was dropped by truncation"
    df = pd.read_parquet(feb)
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    # 2024-02 is fully interior to the window; expect ~a full month of hours,
    # not a boundary sliver (the old bug left ~1-2 hours here).
    assert df["ts_utc"].dt.floor("h").nunique() >= 600


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


# --------------------------------------------------------------------------
# Task 2: backfill, ingest_incremental, latest_complete_month
# --------------------------------------------------------------------------


def test_backfill_iterates_all_four_dataset_keys_in_order(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[str] = []

    def spy_ingest_dataset(
        settings: Settings,
        dataset_key: str,
        start: date,
        end: date,
        transport: object = None,
        *,
        use_cache: bool = True,
    ) -> None:
        captured.append(dataset_key)

    monkeypatch.setattr(entsoe, "ingest_dataset", spy_ingest_dataset)

    entsoe.backfill(tmp_settings, date(2019, 1, 1), date(2024, 1, 1))

    assert captured == [
        "entsoe_prices_at",
        "entsoe_prices_delu",
        "entsoe_load_at",
        "entsoe_gen_at",
    ]


def test_backfill_writes_real_files_for_all_datasets(
    tmp_settings: Settings, entsoe_fixtures_dir: Path
) -> None:
    prices_xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml")
    load_xml = _read(entsoe_fixtures_dir, "load_at.xml")
    gen_xml = _read(entsoe_fixtures_dir, "gen_at.xml")

    def transport(query: EntsoeQuery, api_key: str) -> str:
        if query.document_type == "day_ahead_prices":
            return prices_xml
        if query.document_type == "load":
            return load_xml
        return gen_xml

    entsoe.backfill(tmp_settings, date(2024, 1, 1), date(2024, 2, 1), transport)

    for dataset_key in (
        "entsoe_prices_at",
        "entsoe_prices_delu",
        "entsoe_load_at",
        "entsoe_gen_at",
    ):
        assert raw_month_path(dataset_key, date(2024, 1, 1), tmp_settings).exists()


def test_ingest_incremental_uses_45_day_lookback_from_today(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[tuple[str, date, date]] = []

    def spy_ingest_dataset(
        settings: Settings,
        dataset_key: str,
        start: date,
        end: date,
        transport: object = None,
        *,
        use_cache: bool = True,
    ) -> None:
        captured.append((dataset_key, start, end))

    monkeypatch.setattr(entsoe, "ingest_dataset", spy_ingest_dataset)

    entsoe.ingest_incremental(tmp_settings)

    assert len(captured) == 4
    for _, start, end in captured:
        assert end == date.today()
        assert (end - start).days == tmp_settings.ingest.incremental_lookback_days == 45


def _full_month_price_frame(year: int, month: int, zone: str) -> pd.DataFrame:
    start = pd.Timestamp(year=year, month=month, day=1, tz="UTC")
    end = start + pd.offsets.MonthBegin(1)
    ts = pd.date_range(start, end, freq="h", inclusive="left")
    return pd.DataFrame(
        {
            "ts_utc": ts,
            "price_eur_mwh": 50.0,
            "resolution": "PT60M",
            "zone": zone,
        }
    )


def _partial_month_price_frame(year: int, month: int, zone: str, missing_day: int) -> pd.DataFrame:
    frame = _full_month_price_frame(year, month, zone)
    return frame[frame["ts_utc"].dt.day != missing_day].reset_index(drop=True)


def test_latest_complete_month_returns_min_of_at_and_delu(tmp_settings: Settings) -> None:
    write_month(
        _full_month_price_frame(2024, 1, "AT"),
        "entsoe_prices_at",
        date(2024, 1, 1),
        "h",
        tmp_settings,
    )
    write_month(
        _full_month_price_frame(2024, 2, "AT"),
        "entsoe_prices_at",
        date(2024, 2, 1),
        "h",
        tmp_settings,
    )
    write_month(
        _full_month_price_frame(2024, 1, "DE_LU"),
        "entsoe_prices_delu",
        date(2024, 1, 1),
        "h",
        tmp_settings,
    )

    assert entsoe.latest_complete_month(tmp_settings) == date(2024, 1, 1)


def test_latest_complete_month_excludes_incomplete_month(tmp_settings: Settings) -> None:
    write_month(
        _full_month_price_frame(2024, 1, "AT"),
        "entsoe_prices_at",
        date(2024, 1, 1),
        "h",
        tmp_settings,
    )
    write_month(
        _partial_month_price_frame(2024, 2, "AT", missing_day=15),
        "entsoe_prices_at",
        date(2024, 2, 1),
        "h",
        tmp_settings,
    )
    write_month(
        _full_month_price_frame(2024, 1, "DE_LU"),
        "entsoe_prices_delu",
        date(2024, 1, 1),
        "h",
        tmp_settings,
    )
    write_month(
        _full_month_price_frame(2024, 2, "DE_LU"),
        "entsoe_prices_delu",
        date(2024, 2, 1),
        "h",
        tmp_settings,
    )

    assert entsoe.latest_complete_month(tmp_settings) == date(2024, 1, 1)


def test_latest_complete_month_raises_when_no_data_ingested(tmp_settings: Settings) -> None:
    with pytest.raises(NoDataError):
        entsoe.latest_complete_month(tmp_settings)


# --------------------------------------------------------------------------
# Task 3: CLI main()
# --------------------------------------------------------------------------


def test_main_requires_backfill_or_incremental() -> None:
    with pytest.raises(SystemExit):
        entsoe.main([])


def test_main_backfill_and_incremental_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit):
        entsoe.main(["--backfill", "--incremental"])


def test_main_backfill_rejects_malformed_date() -> None:
    with pytest.raises(SystemExit):
        entsoe.main(["--backfill", "--start", "not-a-date"])


def test_main_backfill_invokes_backfill_with_explicit_window(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entsoe, "load_settings", lambda: tmp_settings)
    captured: dict[str, object] = {}

    def fake_backfill(
        settings: Settings,
        start: date,
        end: date,
        transport: object = None,
        *,
        use_cache: bool = True,
    ) -> None:
        captured["start"] = start
        captured["end"] = end
        captured["use_cache"] = use_cache

    monkeypatch.setattr(entsoe, "backfill", fake_backfill)

    code = entsoe.main(["--backfill", "--start", "2024-01-01", "--end", "2024-02-01"])

    assert code == 0
    assert captured == {"start": date(2024, 1, 1), "end": date(2024, 2, 1), "use_cache": True}


def test_main_backfill_no_cache_flag_forwarded(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entsoe, "load_settings", lambda: tmp_settings)
    captured: dict[str, object] = {}

    def fake_backfill(
        settings: Settings,
        start: date,
        end: date,
        transport: object = None,
        *,
        use_cache: bool = True,
    ) -> None:
        captured["use_cache"] = use_cache

    monkeypatch.setattr(entsoe, "backfill", fake_backfill)

    entsoe.main(["--backfill", "--start", "2024-01-01", "--end", "2024-02-01", "--no-cache"])

    assert captured["use_cache"] is False


def test_main_backfill_defaults_start_and_uses_latest_complete_month(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entsoe, "load_settings", lambda: tmp_settings)
    monkeypatch.setattr(entsoe, "latest_complete_month", lambda settings: date(2024, 3, 1))
    captured: dict[str, object] = {}

    def fake_backfill(
        settings: Settings,
        start: date,
        end: date,
        transport: object = None,
        *,
        use_cache: bool = True,
    ) -> None:
        captured["start"] = start
        captured["end"] = end

    monkeypatch.setattr(entsoe, "backfill", fake_backfill)

    code = entsoe.main(["--backfill"])

    assert code == 0
    assert captured["start"] == tmp_settings.window.start_date
    assert captured["end"] == date(2024, 3, 1)


def test_main_backfill_falls_back_to_conservative_end_when_no_data(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No monkeypatch of latest_complete_month -- it runs for real against the
    # empty tmp_settings raw dir, raises NoDataError, and main() falls back.
    monkeypatch.setattr(entsoe, "load_settings", lambda: tmp_settings)
    captured: dict[str, object] = {}

    def fake_backfill(
        settings: Settings,
        start: date,
        end: date,
        transport: object = None,
        *,
        use_cache: bool = True,
    ) -> None:
        captured["end"] = end

    monkeypatch.setattr(entsoe, "backfill", fake_backfill)

    code = entsoe.main(["--backfill"])

    assert code == 0
    end = captured["end"]
    assert isinstance(end, date)
    assert end < date.today()
    assert end.day == 1


def test_main_backfill_rejects_inverted_window(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entsoe, "load_settings", lambda: tmp_settings)

    code = entsoe.main(["--backfill", "--start", "2024-02-01", "--end", "2024-01-01"])

    assert code == 1


def test_main_incremental_invokes_ingest_incremental(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entsoe, "load_settings", lambda: tmp_settings)
    calls: list[bool] = []

    def fake_incremental(
        settings: Settings, transport: object = None, *, use_cache: bool = True
    ) -> None:
        calls.append(use_cache)

    monkeypatch.setattr(entsoe, "ingest_incremental", fake_incremental)

    code = entsoe.main(["--incremental"])

    assert code == 0
    assert calls == [True]


def test_main_incremental_rejects_start_override(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entsoe, "load_settings", lambda: tmp_settings)

    code = entsoe.main(["--incremental", "--start", "2024-01-01"])

    assert code == 1
