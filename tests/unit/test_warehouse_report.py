"""D-02 build-report writer unit tests -- render + write path, network-free.

Exercises ``ModelBuildResult``/``BuildReport`` rendering on constructed inputs
and the ``_write_report`` write path -- no live warehouse connection is ever
opened (mirrors the ``GateResult``/``ValidationReport`` framework tests in
``tests/unit/test_ingest_gates.py``).

Implements: D-02.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from epra.common.config import load_settings
from epra.warehouse.report import BuildReport, ModelBuildResult, _write_report

# ---------------------------------------------------------------------------
# ModelBuildResult / BuildReport framework
# ---------------------------------------------------------------------------


def test_model_build_result_render_markdown_pass_no_evidence() -> None:
    result = ModelBuildResult("demo model", True, "all good")
    rendered = result.render_markdown()
    assert "### demo model — PASS" in rendered
    assert "all good" in rendered
    assert "```" not in rendered


def test_model_build_result_render_markdown_fail_with_evidence() -> None:
    evidence = pd.DataFrame([{"year_local": 2022, "n_hours": 8759}])
    result = ModelBuildResult("demo model", False, "one anomaly", evidence)
    rendered = result.render_markdown()
    assert "### demo model — FAIL" in rendered
    assert "one anomaly" in rendered
    assert "```" in rendered
    assert "8759" in rendered


def test_model_build_result_render_markdown_empty_evidence_omits_fence() -> None:
    result = ModelBuildResult("demo model", True, "no rows", pd.DataFrame())
    rendered = result.render_markdown()
    assert "```" not in rendered


def test_build_report_render_markdown_aggregates_all_results() -> None:
    report = BuildReport()
    report.add(ModelBuildResult("model a", True, "summary a"))
    report.add(ModelBuildResult("model b", False, "summary b"))
    rendered = report.render_markdown(run_date=date(2026, 7, 24))

    assert "2026-07-24" in rendered
    assert "### model a — PASS" in rendered
    assert "### model b — FAIL" in rendered


def test_build_report_all_passed_property() -> None:
    report = BuildReport()
    report.add(ModelBuildResult("model a", True, "ok"))
    assert report.all_passed is True
    report.add(ModelBuildResult("model b", False, "bad"))
    assert report.all_passed is False


# ---------------------------------------------------------------------------
# D-02 sanity-number rows: 2022-08 reconciliation delta + stand-in mart flag
# ---------------------------------------------------------------------------


def test_reconciliation_2022_08_row_renders_with_delta() -> None:
    evidence = pd.DataFrame(
        [{"monthly_base_eur_mwh": 250.1234, "hourly_mean_eur_mwh": 250.12, "delta": 0.0034}]
    )
    result = ModelBuildResult(
        "2022-08 reconciliation delta (DM-064)",
        True,
        "fct_price_monthly.price_base_eur_mwh matches mean(fct_price_hourly.price_at_eur_mwh) "
        "for 2022-08 within 0.01 (delta=0.0034)",
        evidence,
    )
    rendered = result.render_markdown()
    assert "2022-08 reconciliation delta (DM-064)" in rendered
    assert "0.0034" in rendered


def test_stand_in_marts_flagged_in_render() -> None:
    from epra.warehouse.report import _STAND_IN_MARTS, _stand_in_flag

    assert _STAND_IN_MARTS == ("fct_procurement_cost_monthly",)
    result = _stand_in_flag()
    rendered = result.render_markdown()
    assert "fct_procurement_cost_monthly" in rendered
    assert "stand-in (M6 pending)" in rendered
    assert "fct_consumer_load_hourly (stand-in" not in rendered
    assert "M4 consumer profile pending" not in rendered


# ---------------------------------------------------------------------------
# _write_report write path
# ---------------------------------------------------------------------------


def test_write_report_creates_file_under_reports_warehouse(tmp_path: Path) -> None:
    settings = load_settings()
    settings = settings.model_copy(
        update={"paths": settings.paths.model_copy(update={"reports": tmp_path})}
    )
    report = BuildReport()
    report.add(ModelBuildResult("model a", True, "ok"))

    report_path = _write_report(report, settings)

    assert report_path.exists()
    assert report_path.parent.name == "warehouse"
    assert report_path.name == f"dbt_build_{date.today():%Y-%m-%d}.md"
    content = report_path.read_text(encoding="utf-8")
    assert "model a" in content
