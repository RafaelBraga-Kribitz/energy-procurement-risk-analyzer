"""SPEC-04 M5 tests: A1-A4 formulas, AN-304 gate logic, AN-701/703/704/705.

The integration fixture builds a throwaway DuckDB warehouse with ``marts``
tables shaped exactly like SPEC-02 §5, filled with a seeded synthetic series
(calm 2019-2020, a high-volatility 2021-09..2023-06, calmer after) so the
modules run end to end without the real warehouse.

Implements tests for: AN-101..105, AN-201..203, AN-301..304, AN-401..402,
AN-701, AN-703, AN-704, AN-705.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from epra.analytics import descriptive, regimes, spread, weather
from epra.analytics.__main__ import main as analytics_main
from epra.common.config import Settings
from epra.common.ssot import read_ssot_rows

M5_ARTIFACTS = [
    "a1_annual_summary.md",
    "a1_heatmap_hour_month.png",
    "a1_duration_curves.png",
    "a1_negative_hours.png",
    "a2_spread_monthly.png",
    "a2_spread_summary.md",
    "a3_realized_vol.png",
    "a3_regimes.png",
    "a3_regime_stats.md",
    "a3_garch_vs_realized.png",
    "a4_load_vs_hdd.png",
    "a4_load_weather.md",
]


@pytest.fixture(scope="module")
def warehouse_settings(synthetic_warehouse: Settings) -> Settings:
    return synthetic_warehouse


@pytest.fixture(scope="module")
def ran(warehouse_settings: Settings) -> Settings:
    descriptive.run(warehouse_settings)
    spread.run(warehouse_settings)
    weather.run(warehouse_settings)
    regimes.run(warehouse_settings)
    return warehouse_settings


# ------------------------------------------------------------------ formulas


def test_an101_annual_summary_values() -> None:
    hourly = pd.DataFrame(
        {
            "year_local": [2020] * 4,
            "month_local": [6, 6, 6, 1],
            "hour_local": [12, 13, 3, 3],
            "is_peak_hour": [True, True, False, False],
            "price_at_eur_mwh": [-10.0, 600.0, 20.0, 30.0],
        }
    )
    row = descriptive.annual_summary(hourly).iloc[0]
    assert row["mean"] == pytest.approx(160.0)
    assert row["peak"] == pytest.approx(295.0)
    assert row["offpeak"] == pytest.approx(25.0)
    assert row["neg_hours"] == 1
    assert row["neg_mean_depth"] == pytest.approx(10.0)
    assert row["neg_share_solar_pct"] == pytest.approx(100.0)
    assert row["hours_above_500"] == 1


def test_an202_spread_summary() -> None:
    hourly = pd.DataFrame(
        {
            "year_local": [2021] * 4,
            "month_local": [1] * 4,
            "is_peak_hour": [True, False, True, False],
            "spread_at_delu_eur_mwh": [4.0, -2.0, 6.0, 0.0],
        }
    )
    row = spread.spread_summary(hourly).iloc[0]
    assert row["mean"] == pytest.approx(2.0)
    assert row["share_at_above_de_pct"] == pytest.approx(50.0)
    assert row["mean_peak"] == pytest.approx(5.0)
    assert row["mean_offpeak"] == pytest.approx(-1.0)


def test_t3_daily_differences_are_arithmetic_with_negative_prices() -> None:
    daily = pd.DataFrame(
        {"date_local": pd.date_range("2024-05-01", periods=3), "price_base_eur_mwh": [5, -5, 10]}
    )
    out = regimes.daily_differences(daily)
    assert out["d_t"].tolist() == [-10.0, 15.0]


def test_an304_gate_logic() -> None:
    dates = pd.to_datetime(["2019-03-01", "2019-03-02", "2022-01-01", "2022-01-02"])
    frame = pd.DataFrame({"date_local": dates, "regime": ["calm", "calm", "crisis", "calm"]})
    gate = regimes.regime_gate(frame)
    assert gate.calm_2019_share == 1.0
    assert gate.crisis_top2_share == 0.5
    assert not gate.passed


# --------------------------------------------------------------- integration


def test_an701_all_artifacts_exist(ran: Settings) -> None:
    out = ran.paths.reports / "analytics"
    missing = [name for name in M5_ARTIFACTS if not (out / name).exists()]
    assert not missing


@pytest.mark.parametrize("name", [n for n in M5_ARTIFACTS if n.endswith(".md")])
def test_an704_prose_after_last_table(ran: Settings, name: str) -> None:
    text = (ran.paths.reports / "analytics" / name).read_text(encoding="utf-8")
    lines = text.splitlines()
    last_table = max(i for i, line in enumerate(lines) if line.startswith("|"))
    prose = " ".join(
        line for line in lines[last_table + 1 :] if line and not line.startswith(("#", "**", ">"))
    )
    assert len(prose) >= 400, f"{name}: only {len(prose)} chars of prose"


def test_an105_paragraph_content(ran: Settings) -> None:
    text = (ran.paths.reports / "analytics" / "a1_annual_summary.md").read_text(encoding="utf-8")
    assert "So what for a procurement manager" in text
    assert "solar" in text and "2022" in text and "negative" in text


def test_an402_states_reference_consumer_weather_invariant(ran: Settings) -> None:
    text = (ran.paths.reports / "analytics" / "a4_load_weather.md").read_text(encoding="utf-8")
    assert "weather-invariant by construction" in text


def test_an304_gate_passes_and_regimes_written(ran: Settings) -> None:
    text = (ran.paths.reports / "analytics" / "a3_regime_stats.md").read_text(encoding="utf-8")
    assert "AN-304 sanity gate: PASS" in text
    labels = pd.read_parquet(regimes.regimes_path(ran))
    assert set(labels["regime"]) <= set(regimes.REGIME_LABELS)


def test_an703_ssot_rows_verified_and_complete_years_only(ran: Settings) -> None:
    rows = read_ssot_rows(ran)
    analytics = rows[rows["produced_by"].str.startswith("analytics/")]
    assert set(analytics["tag"]) == {"VERIFIED"}
    keys = set(analytics["key"])
    assert {
        "annual_mean_price_2019",
        "neg_hours_2024",
        "spread_mean_2022",
        "garch_persistence",
        "data_last_month",
    } <= keys
    assert not any(re.search(r"_2026$", k) for k in keys)  # 2026 is unpriced in the fixture


def test_an705_rerun_identical(ran: Settings) -> None:
    out = ran.paths.reports / "analytics"
    before = {p.name: p.read_bytes() for p in sorted(out.iterdir())}
    ssot_before = read_ssot_rows(ran)
    descriptive.run(ran)
    spread.run(ran)
    weather.run(ran)
    regimes.run(ran)
    after = {p.name: p.read_bytes() for p in sorted(out.iterdir())}
    assert before == after
    pd.testing.assert_frame_equal(ssot_before, read_ssot_rows(ran))


def _isolated(settings: Settings, tmp_path: Path) -> Settings:
    paths = settings.paths.model_copy(
        update={"reports": tmp_path / "reports", "data_processed": tmp_path / "processed"}
    )
    return settings.model_copy(update={"paths": paths})


def test_gate_failure_raises(
    warehouse_settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(regimes, "CALM_MIN_SHARE", 1.01)
    with pytest.raises(regimes.RegimeGateFailure, match="AN-304"):
        regimes.run(_isolated(warehouse_settings, tmp_path))


@pytest.mark.parametrize(("calm_min", "code"), [(0.6, 0), (1.01, 1)])
def test_main_exit_code_follows_gate(
    warehouse_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    calm_min: float,
    code: int,
) -> None:
    import epra.analytics.__main__ as entry

    monkeypatch.setattr(entry, "load_settings", lambda: _isolated(warehouse_settings, tmp_path))
    monkeypatch.setattr(regimes, "CALM_MIN_SHARE", calm_min)
    assert analytics_main([]) == code
