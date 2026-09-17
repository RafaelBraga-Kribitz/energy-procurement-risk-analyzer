"""AN-701 / AN-705 analytics operator gates (T5.07).

Uses injected synthetic mart frames (not a committed fixture warehouse).
Does not commit PNGs (D-05). Implements: AN-701, AN-704, AN-705, D-04.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from epra.analytics import _kit as kit
from epra.analytics.__main__ import main
from epra.common.config import Settings
from epra.common.db import connect, warehouse_path


def _hourly_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for year in (2022, 2023):
        for month in range(1, 13):
            for day in (5, 12, 19, 26):
                day_local = date(year, month, day)
                hdd = float(max(0, 12 - month) * 2)
                for hour in (0, 8, 12, 18):
                    peak = hour >= 8
                    at = 40.0 + (year - 2022) * 20.0 + month + (8.0 if peak else 0.0)
                    rows.append(
                        {
                            "year_local": year,
                            "month_local": month,
                            "hour_local": hour,
                            "date_local": day_local,
                            "price_at_eur_mwh": at,
                            "price_delu_eur_mwh": at - 4.0,
                            "is_peak_hour": peak,
                            "load_at_mw": 4800.0 + 20.0 * hdd + hour,
                            "hdd_18": hdd,
                            "is_weekend": day_local.weekday() >= 5,
                        }
                    )
    return pd.DataFrame(rows)


def _daily_frame() -> pd.DataFrame:
    rng = np.random.default_rng(4)
    shocks = np.concatenate(
        [
            rng.normal(0.0, 0.2, 60),
            rng.normal(0.0, 1.0, 60),
            rng.normal(0.0, 3.0, 60),
        ]
    )
    prices = 75.0 + np.cumsum(shocks)
    return pd.DataFrame(
        {
            "date_local": pd.date_range("2023-01-01", periods=180, freq="D"),
            "price_base_eur_mwh": prices,
        }
    )


def _wipe_analytics(settings: Settings) -> Path:
    out = kit.analytics_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    for name in kit.ARTIFACT_NAMES:
        path = out / name
        if path.exists():
            path.unlink()
    return out


def _prepare_cli(tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    hourly = _hourly_frame()
    daily = _daily_frame()
    connect(tmp_settings, read_only=False).close()
    assert warehouse_path(tmp_settings).is_file()
    monkeypatch.setattr("epra.analytics.descriptive.load_price_hourly", lambda _s: hourly)
    monkeypatch.setattr("epra.analytics.spread.load_price_hourly", lambda _s: hourly)
    monkeypatch.setattr("epra.analytics.weather.load_price_hourly", lambda _s: hourly)
    monkeypatch.setattr("epra.analytics.regimes.load_price_daily", lambda _s: daily)
    monkeypatch.setattr("epra.analytics.__main__.load_settings", lambda: tmp_settings)


def test_makefile_analyze_is_python_module_not_dbt() -> None:
    text = Path("Makefile").read_text(encoding="utf-8")
    start = text.index("analyze:")
    rest = text[start:]
    end = rest.find("\nsimulate:")
    block = rest if end < 0 else rest[:end]
    assert "python -m epra.analytics" in block
    assert "dbt" not in block
    assert "not implemented" not in block


def test_an701_twelve_artifacts_from_wiped_dir(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_cli(tmp_settings, monkeypatch)
    out = _wipe_analytics(tmp_settings)
    leftover = out / "a1_heatmap_hour_month.png"
    leftover.write_bytes(b"stale")
    leftover.unlink()
    assert main([]) == 0
    missing = [name for name in sorted(kit.ARTIFACT_NAMES) if not (out / name).is_file()]
    assert missing == []
    for name in (
        "a1_annual_summary.md",
        "a2_spread_summary.md",
        "a3_regime_stats.md",
        "a4_load_weather.md",
    ):
        prose = kit.prose_after_last_table((out / name).read_text(encoding="utf-8"))
        assert len(prose) >= 400, name


def test_an705_ssot_identical_on_second_run(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_cli(tmp_settings, monkeypatch)
    _wipe_analytics(tmp_settings)
    assert main([]) == 0
    path = kit.processed_dir(tmp_settings) / "ssot_inputs_analytics.parquet"
    first = pd.read_parquet(path).sort_values("key").reset_index(drop=True)
    assert main([]) == 0
    second = pd.read_parquet(path).sort_values("key").reset_index(drop=True)
    pd.testing.assert_frame_equal(first, second)
    assert set(first["tag"].astype(str)) == {"VERIFIED"}
    keys = set(first["key"].astype(str))
    assert "garch_persistence" in keys
    assert any(k.startswith("neg_hours_") for k in keys)
    assert any(k.startswith("spread_mean_") for k in keys)
    assert any(k.startswith("annual_mean_price_") for k in keys)
