"""T6.05 annual summary, ST-602, dual-write parquet, CLI, ST-304 charts.

Implements: ST-301, ST-302, ST-304, ST-602, ST-204, D-05.
"""

from __future__ import annotations

import pandas as pd
import pytest
from matplotlib import pyplot as plt
from matplotlib.colors import to_hex

from epra.analytics._kit import prose_after_last_table
from epra.common.config import Settings, load_strategy_config
from epra.common.db import warehouse_path
from epra.report.style import STRATEGY_COLORS
from epra.strategies.align import AlignedVolumes, processed_dir
from epra.strategies.annual import (
    annual_summary,
    check_st602a,
    check_st602b,
    figure_annual_costs,
    figure_cumulative,
    write_strategy_costs,
)
from epra.strategies.calibration import Anchors
from epra.strategies.retrospective import LP050_SENTENCE, ST502_SENTENCE, main, run

_ANCHORS = Anchors(p_ref_base=50.0, p_ref_peak=70.0, oespi_base_ref=100.0, oespi_peak_ref=100.0)


def test_annual_summary_rank_and_delta() -> None:
    monthly = pd.DataFrame(
        {
            "year_local": [2022, 2022],
            "strategy_id": ["S1", "S3"],
            "volume_mwh": [10.0, 10.0],
            "cost_eur": [100.0, 80.0],
            "unit_cost_eur_mwh": [10.0, 8.0],
        }
    )
    annual = annual_summary(monthly)
    s1 = annual.loc[annual["strategy_id"] == "S1"].iloc[0]
    assert int(s1["rank"]) == 2
    assert float(s1["delta_vs_min_eur"]) == pytest.approx(20.0)


def test_st602a_skip_fail_pass() -> None:
    skip = annual_summary(
        pd.DataFrame(
            {
                "year_local": [2021],
                "strategy_id": ["S1"],
                "volume_mwh": [1.0],
                "cost_eur": [1.0],
                "unit_cost_eur_mwh": [1.0],
            }
        )
    )
    assert check_st602a(skip).status == "skip"
    fail = annual_summary(
        pd.DataFrame(
            {
                "year_local": [2022, 2022],
                "strategy_id": ["S1", "S3"],
                "volume_mwh": [1.0, 1.0],
                "cost_eur": [10.0, 20.0],
                "unit_cost_eur_mwh": [10.0, 20.0],
            }
        )
    )
    assert check_st602a(fail).status == "fail"
    ok = annual_summary(
        pd.DataFrame(
            {
                "year_local": [2022, 2022],
                "strategy_id": ["S1", "S3"],
                "volume_mwh": [1.0, 1.0],
                "cost_eur": [20.0, 10.0],
                "unit_cost_eur_mwh": [20.0, 10.0],
            }
        )
    )
    assert check_st602a(ok).status == "pass"


def test_st602b_hybrid_between_legs() -> None:
    ok = annual_summary(
        pd.DataFrame(
            {
                "year_local": [2022, 2022, 2022],
                "strategy_id": ["S1", "S3", "S4_50"],
                "volume_mwh": [1.0, 1.0, 1.0],
                "cost_eur": [20.0, 10.0, 15.0],
                "unit_cost_eur_mwh": [20.0, 10.0, 15.0],
            }
        )
    )
    assert check_st602b(ok).status == "pass"
    fail = annual_summary(
        pd.DataFrame(
            {
                "year_local": [2022, 2022, 2022],
                "strategy_id": ["S1", "S3", "S4_50"],
                "volume_mwh": [1.0, 1.0, 1.0],
                "cost_eur": [20.0, 10.0, 30.0],
                "unit_cost_eur_mwh": [20.0, 10.0, 30.0],
            }
        )
    )
    assert check_st602b(fail).status == "fail"


def test_dual_write_wipes_standin(tmp_settings: Settings) -> None:
    root = processed_dir(tmp_settings)
    leftover = root / "procurement_cost_monthly" / "old.parquet"
    leftover.parent.mkdir(parents=True)
    leftover.write_text("junk", encoding="utf-8")
    monthly = pd.DataFrame(
        {
            "year_local": [2022],
            "month_local": [1],
            "strategy_id": ["S1"],
            "volume_mwh": [1.0],
            "cost_eur": [2.0],
            "unit_cost_eur_mwh": [2.0],
        }
    )
    write_strategy_costs(monthly, tmp_settings)
    assert (root / "strategy_costs_monthly.parquet").is_file()
    written = pd.read_parquet(root / "procurement_cost_monthly" / "strategy_costs_monthly.parquet")
    assert written["year_local"].dtype == "int64"
    assert written["month_local"].dtype == "int64"
    assert not leftover.exists()


def test_annual_bar_object_inspected() -> None:
    annual = annual_summary(
        pd.DataFrame(
            {
                "year_local": [2022, 2022],
                "strategy_id": ["S1", "S3"],
                "volume_mwh": [1.0, 1.0],
                "cost_eur": [20.0, 10.0],
                "unit_cost_eur_mwh": [20.0, 10.0],
            }
        )
    )
    fig = figure_annual_costs(annual)
    texts = " ".join(t.get_text() for t in fig.texts)
    assert ST502_SENTENCE in texts
    assert LP050_SENTENCE in texts
    ax = fig.axes[0]
    assert ax.get_ylabel() == "EUR"
    assert to_hex(ax.patches[0].get_facecolor()).lower() == STRATEGY_COLORS["S1"].lower()
    fig2 = figure_cumulative(annual)
    texts2 = " ".join(t.get_text() for t in fig2.texts)
    assert ST502_SENTENCE in texts2
    plt.close(fig)
    plt.close(fig2)


def _run_fixture(tmp_settings: Settings) -> pd.DataFrame:
    ts = pd.Timestamp("2022-01-03 10:00:00", tz="UTC")
    hourly = pd.DataFrame(
        {
            "ts_utc": [ts],
            "load_mwh": [10.0],
            "price_at_eur_mwh": [100.0],
            "year_local": [2022],
            "month_local": [1],
            "is_peak_hour": [True],
        }
    )
    monthly = pd.DataFrame({"year_local": [2022], "month_local": [1], "volume_mwh": [10.0]})
    aligned = AlignedVolumes(hourly=hourly, monthly=monthly, dropped_hours=0)
    oespi = pd.concat(
        [
            pd.DataFrame(
                {
                    "year_local": [2021] * 12,
                    "month_local": list(range(1, 13)),
                    "oespi_base": [100.0] * 12,
                    "oespi_peak": [100.0] * 12,
                }
            ),
            pd.DataFrame(
                {
                    "year_local": [2022] * 12,
                    "month_local": list(range(1, 13)),
                    "oespi_base": [100.0] * 12,
                    "oespi_peak": [100.0] * 12,
                }
            ),
        ]
    )
    cfg = load_strategy_config().model_copy(update={"retrospective_years": [2022]})
    return run(
        tmp_settings,
        aligned=aligned,
        monthly_oespi=oespi,
        anchors=_ANCHORS,
        w_peak=0.4,
        cfg=cfg,
    )


def test_run_writes_charts_and_ssot(tmp_settings: Settings) -> None:
    stacked = _run_fixture(tmp_settings)
    assert set(stacked["strategy_id"]) >= {"S1", "S2", "S3", "S4_50"}
    reports = tmp_settings.paths.reports / "strategies"
    assert (reports / "s5_annual_costs.png").is_file()
    assert (reports / "s5_cumulative.png").is_file()
    md = (reports / "s5_unit_costs.md").read_text(encoding="utf-8")
    assert ST502_SENTENCE in md
    assert LP050_SENTENCE in md
    prose = prose_after_last_table(md)
    assert len(prose) >= 400
    ssot = pd.read_parquet(processed_dir(tmp_settings) / "ssot_inputs_strategies.parquet")
    keys = set(ssot["key"].astype(str))
    assert "wrong_strategy_cost_2022" in keys
    assert "wrong_strategy_cost_total" in keys
    assert "p_ref_base" in keys
    assert "oespi_peak_ref" in keys
    assert (ssot["tag"] == "CALIBRATED").all()


def test_cli_missing_warehouse_exits_1(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("epra.common.config.load_settings", lambda: tmp_settings)
    assert not warehouse_path(tmp_settings).is_file()
    assert main([]) == 1
