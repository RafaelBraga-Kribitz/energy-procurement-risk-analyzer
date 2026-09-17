"""T5.01 analytics kit tests — mart load, RP-702 stamp, SSOT, missing warehouse.

Implements: D-01, D-03, D-04, RP-701, RP-702.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from epra.analytics import _kit as kit
from epra.analytics.__main__ import main
from epra.common.config import Settings
from epra.common.db import connect, warehouse_path
from epra.report.style import DPI, FIGSIZE, SOURCE_NOTE


def test_artifact_names_match_spec04_section_6() -> None:
    assert len(kit.ARTIFACT_NAMES) == 12
    assert "a1_annual_summary.md" in kit.ARTIFACT_NAMES
    assert "a4_load_weather.md" in kit.ARTIFACT_NAMES


def test_stamp_rp702_sets_size_source_and_tag() -> None:
    fig: Figure
    fig, _ax = plt.subplots()
    kit.stamp_rp702(fig, tag="VERIFIED")
    assert tuple(fig.get_size_inches()) == FIGSIZE
    texts = " ".join(t.get_text() for t in fig.texts)
    assert SOURCE_NOTE in texts
    assert "VERIFIED" in texts
    plt.close(fig)


def test_save_png_writes_file(tmp_path: Path) -> None:
    fig, _ax = plt.subplots()
    dest = tmp_path / "demo.png"
    kit.save_png(fig, dest)
    assert dest.is_file()
    assert dest.stat().st_size > 0


def test_write_ssot_rows_upserts_by_key(tmp_settings: Settings) -> None:
    kit.write_ssot_rows(
        [
            {
                "key": "neg_hours_2022",
                "value": 12.0,
                "unit": "hours",
                "tag": "VERIFIED",
                "produced_by": "epra.analytics.descriptive",
            }
        ],
        tmp_settings,
    )
    kit.write_ssot_rows(
        [
            {
                "key": "spread_mean_2022",
                "value": 3.5,
                "unit": "EUR/MWh",
                "tag": "VERIFIED",
                "produced_by": "epra.analytics.spread",
            },
            {
                "key": "neg_hours_2022",
                "value": 99.0,
                "unit": "hours",
                "tag": "VERIFIED",
                "produced_by": "epra.analytics.descriptive",
            },
        ],
        tmp_settings,
    )
    out = pd.read_parquet(kit.processed_dir(tmp_settings) / "ssot_inputs_analytics.parquet")
    by_key = {str(r.key): float(r.value) for r in out.itertuples(index=False)}
    assert by_key["neg_hours_2022"] == 99.0
    assert by_key["spread_mean_2022"] == 3.5
    assert set(out.columns) == set(kit.SSOT_COLUMNS)


def test_prose_after_last_table_counts_an704() -> None:
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |\n\nHello world paragraph follows the table.\n"
    prose = kit.prose_after_last_table(md)
    assert prose.startswith("Hello world")
    assert "1 | 2" not in prose


def test_write_ssot_rows_roundtrip(tmp_settings: Settings) -> None:
    rows: list[dict[str, object]] = [
        {
            "key": "neg_hours_2022",
            "value": 12.0,
            "unit": "hours",
            "tag": "VERIFIED",
            "produced_by": "epra.analytics.descriptive",
        }
    ]
    path = kit.write_ssot_rows(rows, tmp_settings)
    out = pd.read_parquet(path)
    assert list(out.columns) == list(kit.SSOT_COLUMNS)
    assert out.iloc[0]["tag"] == "VERIFIED"
    assert float(out.iloc[0]["value"]) == 12.0


def test_write_ssot_rejects_non_verified(tmp_settings: Settings) -> None:
    with pytest.raises(ValueError, match="VERIFIED"):
        kit.write_ssot_rows(
            [
                {
                    "key": "x",
                    "value": 1.0,
                    "unit": "1",
                    "tag": "CALIBRATED",
                    "produced_by": "t",
                }
            ],
            tmp_settings,
        )


def test_load_price_hourly_raises_on_empty(tmp_settings: Settings) -> None:
    con = connect(tmp_settings, read_only=False)
    try:
        con.execute("create schema marts")
        con.execute(
            "create table marts.fct_price_hourly (ts_utc timestamp, price_at_eur_mwh double)"
        )
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="SQL returned empty"):
        kit.load_price_hourly(tmp_settings)


def test_load_price_hourly_returns_rows(tmp_settings: Settings) -> None:
    con = connect(tmp_settings, read_only=False)
    try:
        con.execute("create schema marts")
        con.execute(
            "create table marts.fct_price_hourly (ts_utc timestamp, price_at_eur_mwh double)"
        )
        con.execute("insert into marts.fct_price_hourly values ('2022-01-01 00:00:00', 10.0)")
    finally:
        con.close()
    frame = kit.load_price_hourly(tmp_settings)
    assert len(frame) == 1
    assert float(frame["price_at_eur_mwh"].iloc[0]) == 10.0


def test_cli_missing_warehouse_exits_1(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("epra.analytics.__main__.load_settings", lambda: tmp_settings)
    assert not warehouse_path(tmp_settings).is_file()
    assert main([]) == 1


def test_dpi_constant_is_rp701() -> None:
    assert DPI == 150
