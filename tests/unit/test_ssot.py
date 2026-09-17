"""T6.08 SSOT assembler (GV-301/302, ADR-016).

Implements: GV-301, GV-302, ADR-016, D-16, D-17.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from epra.common.config import Settings
from epra.report import ssot as ssot_mod
from epra.report.ssot import (
    assemble,
    concat_producers,
    iso_mtime_utc,
    missing_gv302_keys,
    require_gv302,
)
from epra.strategies.align import STRATEGY_IDS, processed_dir


def _row(
    key: str,
    value: object,
    tag: str = "CALIBRATED",
    unit: str = "EUR",
    produced_by: str = "test",
) -> dict[str, object]:
    return {
        "key": key,
        "value": value,
        "unit": unit,
        "tag": tag,
        "produced_by": produced_by,
    }


def _complete_2022_rows() -> list[dict[str, object]]:
    rows = [
        _row("p_ref_base", 40.0, unit="EUR/MWh"),
        _row("p_ref_peak", 50.0, unit="EUR/MWh"),
        _row("oespi_base_ref", 70.0, unit="index"),
        _row("oespi_peak_ref", 80.0, unit="index"),
        _row("consumer_peak_share", 0.48, unit="share", tag="CALIBRATED"),
        _row("garch_persistence", 0.9, unit="1", tag="VERIFIED"),
        _row("annual_mean_price_2022", 200.0, unit="EUR/MWh", tag="VERIFIED"),
        _row("neg_hours_2022", 10.0, unit="hours", tag="VERIFIED"),
        _row("spread_mean_2022", 1.0, unit="EUR/MWh", tag="VERIFIED"),
        _row("wrong_strategy_cost_2022", 20.0),
        _row("wrong_strategy_cost_total", 20.0),
    ]
    for sid in STRATEGY_IDS:
        rows.append(_row(f"cost_{sid}_2022", 100.0 if sid != "S3" else 80.0))
        rows.append(_row(f"p95_next12m_{sid}", 1.0, tag="SIMULATED"))
        rows.append(_row(f"cvar95_next12m_{sid}", 2.0, tag="SIMULATED"))
    return rows


def test_duplicate_keys_raise() -> None:
    a = pd.DataFrame([_row("p_ref_base", 1.0)])
    b = pd.DataFrame([_row("p_ref_base", 2.0)])
    with pytest.raises(ValueError, match="duplicate SSOT keys"):
        concat_producers([a, b])


def test_assemble_byte_identical_and_data_last_month(tmp_settings: Settings) -> None:
    frames = [
        pd.DataFrame(
            [
                _row("p_ref_base", 40.0),
                _row("oespi_peak_ref", 80.0, tag="CALIBRATED"),
                _row("cost_S1_2022", 100.0),
                _row("cost_S3_2022", 80.0),
            ]
        )
    ]
    mtimes = (1_700_000_000.4, 1_700_000_010.9)
    body = assemble(
        tmp_settings,
        frames=frames,
        data_last_month="2024-01",
        mtimes=mtimes,
    )
    again = assemble(
        tmp_settings,
        frames=frames,
        data_last_month="2024-01",
        mtimes=mtimes,
    )
    assert body == again
    assert iso_mtime_utc(max(mtimes)) in body
    assert "data_last_month" in body
    assert "2024-01" in body
    assert "VERIFIED" in body
    assert "epra.report.ssot" in body
    assert "best_strategy_5yr" in body
    assert "S3" in body
    assert "oespi_peak_ref" in body
    dest = tmp_settings.paths.reports / "NUMERIC_SSOT.md"
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == body
    assert "cost_S1_2021" not in body
    assert "datetime.now" not in Path(ssot_mod.__file__).read_text(encoding="utf-8")


def test_renderer_copies_tags_not_retyped(tmp_settings: Settings) -> None:
    frames = [pd.DataFrame([_row("p95_next12m_S1", 9.0, tag="SIMULATED")])]
    body = assemble(
        tmp_settings,
        frames=frames,
        data_last_month="2024-01",
        mtimes=(0.0,),
    )
    assert "| p95_next12m_S1 | 9.0 | EUR | SIMULATED | test |" in body


def test_missing_producers_raise(tmp_settings: Settings) -> None:
    processed_dir(tmp_settings).mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError, match="ssot_inputs_"):
        assemble(tmp_settings, data_last_month="2024-01", mtimes=(0.0,))


def test_assemble_from_glob(tmp_settings: Settings) -> None:
    root = processed_dir(tmp_settings)
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([_row("p_ref_base", 40.0)]).to_parquet(
        root / "ssot_inputs_profile.parquet", index=False
    )
    pd.DataFrame([_row("garch_persistence", 0.9, tag="VERIFIED")]).to_parquet(
        root / "ssot_inputs_analytics.parquet", index=False
    )
    body = assemble(
        tmp_settings,
        data_last_month="2024-01",
        check_complete=False,
    )
    assert "p_ref_base" in body
    assert "garch_persistence" in body
    again = assemble(tmp_settings, data_last_month="2024-01", check_complete=False)
    assert body == again


def test_gv302_complete_on_present_year_only() -> None:
    frame = pd.DataFrame(_complete_2022_rows())
    frame = pd.concat(
        [
            frame,
            pd.DataFrame(
                [
                    _row("data_last_month", "2024-01", tag="VERIFIED", unit="YYYY-MM"),
                    _row("best_strategy_5yr", "S3", unit="strategy_id"),
                ]
            ),
        ],
        ignore_index=True,
    )
    require_gv302(frame)
    assert missing_gv302_keys(frame["key"].astype(str)) == []
    assert "cost_S1_2021" not in set(frame["key"].astype(str))


def test_gv302_incomplete_raises(tmp_settings: Settings) -> None:
    frames = [pd.DataFrame([_row("p_ref_base", 40.0)])]
    with pytest.raises(ValueError, match="GV-302 missing keys"):
        assemble(
            tmp_settings,
            frames=frames,
            data_last_month="2024-01",
            mtimes=(0.0,),
            check_complete=True,
        )


def test_assemble_complete_keys_byte_identical(tmp_settings: Settings) -> None:
    frames = [pd.DataFrame(_complete_2022_rows())]
    body = assemble(
        tmp_settings,
        frames=frames,
        data_last_month="2024-01",
        mtimes=(1_700_000_000.0,),
        check_complete=True,
    )
    again = assemble(
        tmp_settings,
        frames=frames,
        data_last_month="2024-01",
        mtimes=(1_700_000_000.0,),
        check_complete=True,
    )
    assert body == again
    assert "oespi_peak_ref" in body
    assert "SIMULATED" in body
    assert "cost_S1_2021" not in body
