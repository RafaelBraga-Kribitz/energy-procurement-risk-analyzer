"""Build-report unit tests (SPEC-02 §6) -- rendering, dbt run_results parsing, and
``build_report``/``main`` end-to-end against a tiny temp DuckDB warehouse plus a
synthetic ``run_results.json`` -- network-free, never touches the real warehouse.

Implements: DM-020, DM-050, DM-060..066 (report records dbt outcomes + sanity numbers).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest

import epra.warehouse.report as report_module
from epra.common import logging as common_logging
from epra.common.config import REPO_ROOT, Settings, load_settings
from epra.common.timeutil import today_local
from epra.warehouse.report import (
    BuildReport,
    DbtRunSummary,
    ModelBuildResult,
    _write_report,
    build_report,
    load_run_results,
)


@pytest.fixture(autouse=True)
def _no_warehouse_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """``EPRA_DUCKDB_PATH`` would redirect `connect()` away from the temp warehouse."""
    monkeypatch.delenv("EPRA_DUCKDB_PATH", raising=False)


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
# Sanity-number rows: 2022-08 reconciliation delta + stand-in mart flag
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
    evidence = pd.DataFrame(
        [
            {"mart": "fct_consumer_load_hourly", "status": "stand-in (M4/M6 pending)"},
            {"mart": "fct_procurement_cost_monthly", "status": "stand-in (M4/M6 pending)"},
        ]
    )
    result = ModelBuildResult(
        "future marts",
        True,
        "fct_consumer_load_hourly and fct_procurement_cost_monthly are thin loaders over "
        "synthetic/stand-in data, not real module output yet",
        evidence,
    )
    rendered = result.render_markdown()
    assert "stand-in (M4/M6 pending)" in rendered
    assert "fct_consumer_load_hourly" in rendered
    assert "fct_procurement_cost_monthly" in rendered


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
    assert report_path.name == f"dbt_build_{today_local():%Y-%m-%d}.md"
    content = report_path.read_text(encoding="utf-8")
    assert "model a" in content


# ---------------------------------------------------------------------------
# dbt run_results.json -> DbtRunSummary
# ---------------------------------------------------------------------------

_PREDUP_WARN = "test.epra.predup_count_prices"


def _run_results(tmp_path: Path, statuses: dict[str, str], which: str = "build") -> Path:
    """Write a minimal dbt ``run_results.json`` (real v6 shape, only the fields read)."""
    payload = {
        "metadata": {"dbt_version": "1.12.0", "generated_at": "2026-09-30T17:44:35Z"},
        "results": [{"unique_id": uid, "status": st} for uid, st in statuses.items()],
        "args": {"which": which},
    }
    path = tmp_path / "run_results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_run_results_missing_file_is_none(tmp_path: Path) -> None:
    assert load_run_results(tmp_path / "absent.json") is None


def test_load_run_results_counts_statuses_and_names_warn_error_nodes(tmp_path: Path) -> None:
    path = _run_results(
        tmp_path,
        {
            "model.epra.fct_price_hourly": "success",
            "test.epra.unique_fct_price_hourly_ts_utc": "pass",
            _PREDUP_WARN: "warn",
            "test.epra.dm_064_reconciliation": "fail",
            "model.epra.fct_price_monthly": "error",
            "model.epra.fct_generation_monthly": "skipped",
            "test.epra.mystery": "some-new-status",
        },
    )
    summary = load_run_results(path)

    assert summary is not None
    assert summary.counts == {"pass": 2, "warn": 1, "error": 3, "skip": 1}
    assert summary.warn_nodes == (_PREDUP_WARN,)
    assert summary.error_nodes == (
        "model.epra.fct_price_monthly",
        "test.epra.dm_064_reconciliation",
        "test.epra.mystery",  # unknown status never reads as OK
    )
    assert summary.status == "ERROR"
    assert summary.invocation == "build"


def test_load_run_results_rejects_non_dbt_document(tmp_path: Path) -> None:
    path = tmp_path / "run_results.json"
    path.write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="not a dbt run_results"):
        load_run_results(path)


def test_dbt_summary_render_flags_non_build_invocation(tmp_path: Path) -> None:
    summary = load_run_results(_run_results(tmp_path, {"test.epra.t": "pass"}, which="test"))
    assert summary is not None
    rendered = summary.render_markdown()
    assert "— PASS" in rendered
    assert "not `build`" in rendered


# ---------------------------------------------------------------------------
# BuildReport headline -- driven by dbt results first, not only sanity rows
# ---------------------------------------------------------------------------


def _summary(warn: tuple[str, ...] = (), error: tuple[str, ...] = ()) -> DbtRunSummary:
    return DbtRunSummary(
        source=Path("run_results.json"),
        invocation="build",
        generated_at="2026-09-30T17:44:35Z",
        counts={"pass": 10, "warn": len(warn), "error": len(error)},
        warn_nodes=warn,
        error_nodes=error,
    )


def test_headline_ok_only_when_dbt_clean_and_sanity_rows_pass() -> None:
    report = BuildReport(dbt=_summary())
    report.add(ModelBuildResult("row", True, "ok"))
    assert report.overall() == "ALL DBT TESTS PASSED; SANITY CHECKS OK"


def test_headline_surfaces_dbt_warn_even_when_sanity_rows_pass() -> None:
    report = BuildReport(dbt=_summary(warn=(_PREDUP_WARN,)))
    report.add(ModelBuildResult("row", True, "ok"))
    rendered = report.render_markdown(run_date=date(2026, 9, 30))

    assert "**Overall: 1 dbt WARN(s) — see below**" in rendered
    assert "ALL DBT TESTS PASSED" not in rendered
    assert f"- `{_PREDUP_WARN}`" in rendered


def test_headline_surfaces_dbt_error_and_flagged_rows() -> None:
    report = BuildReport(dbt=_summary(error=("test.epra.x",)))
    report.add(ModelBuildResult("row", False, "bad"))
    assert report.overall() == "1 dbt node(s) ERROR/FAIL; 1 sanity row(s) flagged — see below"


def test_headline_says_so_when_run_results_missing() -> None:
    report = BuildReport(dbt=None)
    report.add(ModelBuildResult("row", True, "ok"))
    rendered = report.render_markdown(run_date=date(2026, 9, 30))
    assert "NOT FOUND" in report.overall()
    assert "— MISSING" in rendered


# ---------------------------------------------------------------------------
# build_report / main end-to-end on a tiny temp DuckDB warehouse
# ---------------------------------------------------------------------------


def _warehouse_settings(tmp_path: Path) -> Settings:
    settings = load_settings()
    paths = settings.paths.model_copy(
        update={"warehouse": tmp_path / "epra.duckdb", "reports": tmp_path / "reports"}
    )
    return settings.model_copy(update={"paths": paths})


def _build_tiny_warehouse(settings: Settings, *, with_2022_08: bool = True) -> None:
    """Create the four marts ``build_report`` reads, with a handful of rows."""
    con = duckdb.connect(str(settings.paths.warehouse))
    try:
        con.execute("create schema marts")
        con.execute(
            "create table marts.fct_price_hourly "
            "(year_local integer, month_local integer, price_at_eur_mwh double)"
        )
        con.execute(
            "create table marts.fct_price_monthly "
            "(year_local integer, month_local integer, price_base_eur_mwh double)"
        )
        for mart in ("fct_generation_monthly", "fct_procurement_cost_monthly"):
            con.execute(f"create table marts.{mart} (year_local integer, month_local integer)")
            con.execute(f"insert into marts.{mart} values (2022, 7), (2022, 8)")
        if with_2022_08:
            con.execute(
                "insert into marts.fct_price_hourly values (2022, 8, 400.0), (2022, 8, 500.0), "
                "(2023, 1, 100.0)"
            )
            con.execute(
                "insert into marts.fct_price_monthly values (2022, 8, 450.0), (2023, 1, 100.0)"
            )
    finally:
        con.close()


def test_build_report_records_dbt_warn_and_sanity_numbers(tmp_path: Path) -> None:
    settings = _warehouse_settings(tmp_path)
    _build_tiny_warehouse(settings)
    run_results = _run_results(
        tmp_path, {"model.epra.fct_price_hourly": "success", _PREDUP_WARN: "warn"}
    )

    report = build_report(settings, run_results_path=run_results)

    assert report.dbt is not None and report.dbt.warn_nodes == (_PREDUP_WARN,)
    assert [r.check_id for r in report.results] == [
        "fct_price_hourly row counts (DM-062)",
        "monthly-mart month coverage (DM-050)",
        "2022-08 reconciliation delta (DM-064)",
        "future marts",
    ]
    assert report.all_passed  # sanity rows alone would have said "OK" ...
    assert report.overall() == "1 dbt WARN(s) — see below"  # ... the headline does not
    rendered = report.render_markdown(run_date=date(2026, 9, 30))
    assert "delta=0.0000" in rendered
    assert "pass=1, warn=1, error=0, skip=0" in rendered


def test_build_report_flags_rows_on_empty_marts(tmp_path: Path) -> None:
    settings = _warehouse_settings(tmp_path)
    _build_tiny_warehouse(settings, with_2022_08=False)

    report = build_report(settings, run_results_path=tmp_path / "absent.json")

    assert report.dbt is None
    failed = [r.check_id for r in report.failed]
    assert failed == [
        "fct_price_hourly row counts (DM-062)",
        "2022-08 reconciliation delta (DM-064)",
    ]
    assert report.overall().startswith("dbt run_results.json NOT FOUND")


def test_main_writes_report_with_dbt_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _warehouse_settings(tmp_path)
    _build_tiny_warehouse(settings)
    run_results = _run_results(tmp_path, {_PREDUP_WARN: "warn", "test.epra.t": "pass"})
    monkeypatch.setattr(report_module, "load_settings", lambda: settings)
    monkeypatch.setattr(report_module, "DBT_RUN_RESULTS", run_results)

    assert report_module.main([]) == 0

    report_path = tmp_path / "reports" / "warehouse" / f"dbt_build_{today_local():%Y-%m-%d}.md"
    content = report_path.read_text(encoding="utf-8")
    assert "**Overall: 1 dbt WARN(s) — see below**" in content
    assert _PREDUP_WARN in content


def test_main_returns_1_when_warehouse_has_no_marts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _warehouse_settings(tmp_path)
    duckdb.connect(str(settings.paths.warehouse)).close()  # empty warehouse, no marts schema
    monkeypatch.setattr(report_module, "load_settings", lambda: settings)
    monkeypatch.setattr(report_module, "DBT_RUN_RESULTS", tmp_path / "absent.json")

    assert report_module.main([]) == 1


def test_main_anchors_relative_reports_path_at_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The logfile never lands relative to the caller's cwd (audit 2026-09-30 §2)."""
    settings = _warehouse_settings(tmp_path)
    relative = settings.model_copy(
        update={"paths": settings.paths.model_copy(update={"reports": Path("reports")})}
    )
    monkeypatch.setattr(report_module, "load_settings", lambda: relative)
    monkeypatch.setattr(report_module, "build_report", lambda s: BuildReport())
    monkeypatch.setattr(report_module, "_write_report", lambda r, s: tmp_path / "r.md")
    captured: dict[str, Path | None] = {}
    monkeypatch.setattr(
        common_logging,
        "setup",
        lambda logfile=None, **_: captured.update(logfile=logfile),
    )

    assert report_module.main([]) == 0
    assert captured["logfile"] == (
        REPO_ROOT / "reports" / "warehouse" / f"dbt_build_{today_local():%Y-%m-%d}.log"
    )
