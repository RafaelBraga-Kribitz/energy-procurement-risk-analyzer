"""M7 reporting tests: RP-301 chart data, executive charts, data-quality report,
EXEC_SUMMARY / README blocks (A-6, GV-303 end to end), hero status (A-2).

Implements tests for: RP-201..204, RP-301, SPEC-06 §5/§6, ADR-020 §3.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

import duckdb
import numpy as np
import pandas as pd
import pytest

from epra.common.config import REPO_ROOT, Settings
from epra.common.provenance import FIXTURE_BANNER
from epra.common.ssot import read_ssot_rows
from epra.report import charts, data_quality, exec_summary


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ssot_path(simulated_warehouse: Settings, tmp_path_factory: pytest.TempPathFactory) -> Path:
    gen = _script("generate_ssot")
    out = simulated_warehouse.paths.reports / "NUMERIC_SSOT.md"
    patch = pytest.MonkeyPatch()
    patch.setattr(gen, "load_settings", lambda: simulated_warehouse)
    try:
        assert gen.main(["--output", str(out), "--updated", "2026-10-14"]) == 0
    finally:
        patch.undo()
    return out


# ------------------------------------------------------------------- RP-301


def test_rp301_chart1_bars_rebuild_from_exported_csv(
    simulated_warehouse: Settings, tmp_path: Path
) -> None:
    annual = pd.read_parquet(
        simulated_warehouse.paths.data_processed / "strategy_annual_summary.parquet"
    )
    csv_path = tmp_path / "strategy_annual_summary.csv"
    annual.to_csv(csv_path, index=False)  # same writer contract as exports/ (DM-070)
    from_csv = pd.read_csv(csv_path)
    gap = from_csv.groupby("year")["cost_eur"].agg(lambda s: s.max() - s.min())
    bars = charts.wrong_cost_bars(annual)
    np.testing.assert_allclose(bars["gap_eur"].to_numpy(), gap.to_numpy(), rtol=1e-12)
    rows = read_ssot_rows(simulated_warehouse).set_index("key")["value"]
    for rec in bars.to_dict("records"):
        assert float(rows[f"wrong_strategy_cost_{rec['year']}"]) == pytest.approx(
            rec["gap_eur"], abs=0.01
        )


def test_rp201_204_executive_charts_written(simulated_warehouse: Settings) -> None:
    paths = charts.render_executive_charts(simulated_warehouse)
    assert [p.name for p in paths] == [
        "01_wrong_strategy_cost.png",
        "02_annual_costs_by_strategy.png",
        "03_forward_risk.png",
        "04_market_context.png",
    ]
    assert all(p.stat().st_size > 20_000 for p in paths)


# ------------------------------------------------------------- data quality


def _dq_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year_local": [2025, 2025, 2025],
            "month_local": [9, 10, 11],
            "expected_hours": [720, 745, 720],
            "priced_hours_at": [720, 745, 700],
            "priced_hours_delu": [720, 745, 700],
            "load_hours": [720, 745, 720],
            "weather_days": [30, 31, 30],
            "days_in_month": [30, 31, 30],
            "coverage_at_pct": [100.0, 100.0, 97.222],
            "n_dst_days": [0, 1, 0],
            "n_hours_from_pt15m": [0, 745, 700],
            "resolution": ["PT60M", "PT15M", "PT15M"],
            "n_negative_hours": [3, 0, 0],
            "has_oespi": [True, True, False],
        }
    )


def test_dq_kpis_and_freshness() -> None:
    monthly = _dq_frame()
    assert data_quality.freshness_days(monthly, date(2025, 12, 15)) == 15
    annual = monthly.groupby("year_local", as_index=False).agg(
        expected_hours=("expected_hours", "sum"),
        priced_hours_at=("priced_hours_at", "sum"),
        dst_days=("n_dst_days", "sum"),
        negative_hours=("n_negative_hours", "sum"),
    )
    kpis = data_quality.kpis(annual, monthly, date(2026, 3, 1)).set_index("indicator")["value"]
    assert kpis["Months below 100% AT coverage"] == "1"
    assert kpis["Months on 15-minute MTU (PT15M)"] == "2"
    assert "STALE" in kpis["Days since last data month ended"]


def test_dq_report_written(simulated_warehouse: Settings) -> None:
    con = duckdb.connect(str(simulated_warehouse.paths.warehouse))
    con.register("dq", _dq_frame())
    con.execute("create or replace table marts.fct_data_quality_monthly as select * from dq")
    con.close()
    path = data_quality.run(simulated_warehouse, today=date(2025, 12, 15))
    text = path.read_text(encoding="utf-8")
    assert "Kennzahlen" in text and "| 2025 | 11 |" in text  # the incomplete month is listed
    assert (path.parent / "dq_coverage.png").exists()


# --------------------------------------------------- EXEC_SUMMARY + README


def test_exec_summary_numbers_all_in_ssot(ssot_path: Path, tmp_path: Path) -> None:
    ssot = exec_summary.Ssot.from_markdown(ssot_path)
    text = exec_summary.exec_summary(ssot, fixture=False)
    for heading in (
        "## 1. The answer",
        "## 2. How to read this",
        "## 3. The market",
        "## 4. Strategy comparison",
        "## 5. Forward risk",
        "## 6. What would",
    ):
        assert heading in text
    assert FIXTURE_BANNER not in text
    assert "(CALIBRATED)" in text and "(SIMULATED)" in text and "(VERIFIED)" in text
    check = _script("check_ssot_consistency")
    doc = tmp_path / "EXEC_SUMMARY.md"
    doc.write_text(text, encoding="utf-8")
    literals = check.find_literals(text, doc.name)
    assert len(literals) >= 10
    assert check.mismatches(literals, check.load_ssot(ssot_path), check.load_whitelist()) == []


def test_readme_blocks_real_vs_fixture(ssot_path: Path) -> None:
    ssot = exec_summary.Ssot.from_markdown(ssot_path)
    real = exec_summary.readme_blocks(ssot, fixture=False)
    assert "€" in real["answer"] and "| Strategy |" in real["results"]
    assert real["chart"].startswith("![")
    fixture = exec_summary.readme_blocks(ssot, fixture=True)
    assert "€" not in "".join(fixture.values())  # no fixture number in README
    assert "![" not in fixture["chart"]  # fixture chart is linked, never embedded


def test_replace_block_and_run(
    simulated_warehouse: Settings, ssot_path: Path, tmp_path: Path
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "top\n<!-- epra:answer:start -->\nold\n<!-- epra:answer:end -->\n"
        "<!-- epra:chart:start -->\n<!-- epra:chart:end -->\n"
        "<!-- epra:results:start -->\n<!-- epra:results:end -->\n",
        encoding="utf-8",
    )
    exec_summary.run(simulated_warehouse, readme=readme)
    text = readme.read_text(encoding="utf-8")
    assert "old" not in text and "Buying electricity" in text
    with pytest.raises(ValueError, match="markers"):
        exec_summary.replace_block("no markers", "answer", "x")


def test_yearly_winners_single_and_many(ssot_path: Path) -> None:
    ssot = exec_summary.Ssot.from_markdown(ssot_path)
    sentence = exec_summary.yearly_winners(ssot, [2021, 2022], ["S1", "S3"])
    assert sentence.startswith("Cheapest strategy per year")
    one = exec_summary.yearly_winners(ssot, [2022], ["S3"])
    assert "in every year" in one
