"""T6.05 annual summary, ST-602(a), dual-write parquet, CLI.

Implements: ST-301, ST-302, ST-304, ST-602, D-05.
"""

from __future__ import annotations

import pandas as pd
import pytest

from epra.common.config import Settings, load_strategy_config
from epra.common.db import warehouse_path
from epra.strategies.align import AlignedVolumes, processed_dir
from epra.strategies.annual import (
    annual_summary,
    check_st602a,
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
    assert (root / "procurement_cost_monthly" / "strategy_costs_monthly.parquet").is_file()
    assert not leftover.exists()


def test_run_writes_charts_and_ssot(tmp_settings: Settings) -> None:
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
    stacked = run(
        tmp_settings,
        aligned=aligned,
        monthly_oespi=oespi,
        anchors=_ANCHORS,
        w_peak=0.4,
        cfg=cfg,
    )
    assert set(stacked["strategy_id"]) >= {"S1", "S2", "S3", "S4_50"}
    reports = tmp_settings.paths.reports / "strategies"
    assert (reports / "s5_annual_costs.png").is_file()
    assert (reports / "s5_cumulative.png").is_file()
    md = (reports / "s5_unit_costs.md").read_text(encoding="utf-8")
    assert ST502_SENTENCE in md
    assert LP050_SENTENCE in md
    ssot = pd.read_parquet(processed_dir(tmp_settings) / "ssot_inputs_strategies.parquet")
    assert "wrong_strategy_cost_2022" in set(ssot["key"].astype(str))


def test_cli_missing_warehouse_exits_1(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("epra.common.config.load_settings", lambda: tmp_settings)
    assert not warehouse_path(tmp_settings).is_file()
    assert main([]) == 1
