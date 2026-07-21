"""Unit tests for the ENTSO-E Appendix-A XML parsers in `epra.ingest.entsoe`
(ING-031, ING-032, ING-050, ING-060, ING-063).

Every test reads a committed fixture from `tests/fixtures/entsoe/`
(`entsoe_fixtures_dir` in `tests/conftest.py`) — no network, no
`ENTSOE_API_TOKEN` needed (EN-070).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from epra.ingest.entsoe import (
    PSR_NAMES,
    infer_resolution,
    parse_gl_xml,
    parse_publication_xml,
)
from epra.ingest.exceptions import ContractError, NoDataError


def _read(fixtures_dir: Path, name: str) -> str:
    return (fixtures_dir / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# parse_publication_xml — day-ahead prices
# --------------------------------------------------------------------------


def test_parse_publication_xml_pt60m_columns_and_zone(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml")
    df = parse_publication_xml(xml)

    assert list(df.columns) == ["ts_utc", "price_eur_mwh", "resolution", "zone"]
    assert len(df) == 4
    assert (df["resolution"] == "PT60M").all()
    assert (df["zone"] == "AT").all()
    assert df["ts_utc"].dt.tz is not None
    assert str(df["ts_utc"].dt.tz) == "UTC"
    assert df["price_eur_mwh"].tolist() == [45.67, 50.12, 48.30, 52.00]
    assert df.attrs["a03_fills"] == 0


def test_parse_publication_xml_pt60m_ts_utc_boundary(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml")
    df = parse_publication_xml(xml)

    first = df["ts_utc"].iloc[0]
    assert first == pd.Timestamp("2024-01-01T00:00:00Z")


def test_parse_publication_xml_pt15m_resolution(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt15m_at.xml")
    df = parse_publication_xml(xml)

    assert len(df) == 4
    assert (df["resolution"] == "PT15M").all()
    assert df["price_eur_mwh"].tolist() == [42.10, 43.50, 41.00, 44.20]


def test_parse_publication_xml_a03_forward_fill_within_period(
    entsoe_fixtures_dir: Path,
) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_a03_forward_fill.xml")
    df = parse_publication_xml(xml)

    # positions 1..4 present in output; 2 and 4 were omitted in the fixture
    # and must inherit the last present value (ING-063).
    assert len(df) == 4
    assert df["price_eur_mwh"].tolist() == [40.00, 40.00, 45.00, 45.00]
    assert df.attrs["a03_fills"] == 2


def test_parse_publication_xml_wrong_currency_raises_contract_error(
    entsoe_fixtures_dir: Path,
) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml").replace(
        "<currency_Unit.name>EUR</currency_Unit.name>",
        "<currency_Unit.name>USD</currency_Unit.name>",
    )
    with pytest.raises(ContractError, match="currency"):
        parse_publication_xml(xml)


def test_parse_publication_xml_wrong_unit_raises_contract_error(
    entsoe_fixtures_dir: Path,
) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml").replace(
        "<price_Measure_Unit.name>MWH</price_Measure_Unit.name>",
        "<price_Measure_Unit.name>KWH</price_Measure_Unit.name>",
    )
    with pytest.raises(ContractError, match="MWH"):
        parse_publication_xml(xml)


def test_parse_publication_xml_acknowledgement_raises_no_data_error(
    entsoe_fixtures_dir: Path,
) -> None:
    xml = _read(entsoe_fixtures_dir, "acknowledgement.xml")
    with pytest.raises(NoDataError, match="No matching data found"):
        parse_publication_xml(xml)


def test_parse_publication_xml_dst_spring_23_hours(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "dst_spring.xml")
    df = parse_publication_xml(xml)

    assert len(df) == 23
    assert df["ts_utc"].dt.tz is not None
    assert df["ts_utc"].is_monotonic_increasing
    assert df["ts_utc"].nunique() == 23


def test_parse_publication_xml_dst_fall_25_hours(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "dst_fall.xml")
    df = parse_publication_xml(xml)

    assert len(df) == 25
    assert df["ts_utc"].dt.tz is not None
    assert df["ts_utc"].is_monotonic_increasing
    assert df["ts_utc"].nunique() == 25


# --------------------------------------------------------------------------
# parse_gl_xml — load and generation
# --------------------------------------------------------------------------


def test_parse_gl_xml_load_columns(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "load_at.xml")
    df = parse_gl_xml(xml, "load")

    assert list(df.columns) == ["ts_utc", "load_mw", "resolution", "zone"]
    assert len(df) == 4
    assert (df["resolution"] == "PT15M").all()
    assert (df["zone"] == "AT").all()
    assert df["load_mw"].tolist() == [5000.0, 5100.0, 4950.0, 5200.0]


def test_parse_gl_xml_generation_long_format(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "gen_at.xml")
    df = parse_gl_xml(xml, "generation")

    assert list(df.columns) == [
        "ts_utc",
        "psr_type",
        "psr_name",
        "kind",
        "value_mw",
        "resolution",
        "zone",
    ]
    assert len(df) == 4  # 2 PSR types x 2 points each

    solar = df[df["psr_type"] == "B16"]
    assert (solar["psr_name"] == "Solar").all()
    assert (solar["kind"] == "aggregated").all()
    assert solar["value_mw"].tolist() == [120.5, 130.2]

    hydro_pumped = df[df["psr_type"] == "B10"]
    assert (hydro_pumped["psr_name"] == "Hydro Pumped Storage").all()
    assert (hydro_pumped["kind"] == "consumption").all()
    assert hydro_pumped["value_mw"].tolist() == [15.0, 20.0]


def test_parse_gl_xml_unknown_psr_code_keeps_row(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "gen_at.xml").replace(
        "<psrType>B16</psrType>", "<psrType>B99</psrType>"
    )
    df = parse_gl_xml(xml, "generation")

    unknown = df[df["psr_type"] == "B99"]
    assert len(unknown) == 2
    assert (unknown["psr_name"] == "UNKNOWN(B99)").all()


def test_parse_gl_xml_acknowledgement_raises_no_data_error(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "acknowledgement.xml")
    with pytest.raises(NoDataError, match="No matching data found"):
        parse_gl_xml(xml, "load")


# --------------------------------------------------------------------------
# infer_resolution
# --------------------------------------------------------------------------


def test_infer_resolution_matches_pt60m_fixture(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt60m_at.xml")
    df = parse_publication_xml(xml)

    assert infer_resolution(df["ts_utc"]) == "PT60M"


def test_infer_resolution_matches_pt15m_fixture(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "prices_pt15m_at.xml")
    df = parse_publication_xml(xml)

    assert infer_resolution(df["ts_utc"]) == "PT15M"


def test_infer_resolution_matches_load_fixture(entsoe_fixtures_dir: Path) -> None:
    xml = _read(entsoe_fixtures_dir, "load_at.xml")
    df = parse_gl_xml(xml, "load")

    assert infer_resolution(df["ts_utc"]) == "PT15M"


# --------------------------------------------------------------------------
# PSR_NAMES (Appendix B)
# --------------------------------------------------------------------------


def test_psr_names_covers_appendix_b() -> None:
    assert PSR_NAMES["B16"] == "Solar"
    assert PSR_NAMES["B10"] == "Hydro Pumped Storage"
    assert PSR_NAMES["B04"] == "Fossil Gas"
    # Appendix B lists 18 codes (B01..B06, B09..B20 — B07/B08 are not defined).
    assert len(PSR_NAMES) == 18
