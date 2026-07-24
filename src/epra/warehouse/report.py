"""Warehouse build report -- ``make warehouse`` / ``python -m epra.warehouse.report`` (M3).

Binding contract: SPEC-02 §6 (DM-060..066 sanity numbers), D-02 (human-readable
build report), D-05/D-06 (future-mart stand-in policy). Results are written to
``reports/warehouse/dbt_build_<date>.md``.

This module never builds or mutates the warehouse -- ``cd dbt && dbt build``
(``make transform``) is the only writer (SPEC-02). It opens the warehouse
read-only via ``epra.common.db.connect(settings, read_only=True)`` *after* a
build has completed, and renders the key sanity numbers a human reviewer
wants at a glance:

- per-year ``fct_price_hourly`` row counts (DM-062)
- monthly-mart month coverage for the three monthly marts (DM-050)
- the 2022-08 ``fct_price_monthly`` vs mean-of-hourly reconciliation delta
  (DM-064)
- an explicit flag on the two marts still backed by synthetic/thin-loader
  stand-ins (``fct_consumer_load_hourly``, ``fct_procurement_cost_monthly``;
  D-05/D-06, M4/M6 pending)

The DM-050/062/064/065/066 dbt tests (04-06) and the D-07 schema contract own
pass/fail *enforcement* of these numbers -- this report is informational
sanity-checking layered on top of an already-green ``dbt build``. It reuses
the ``GateResult``/``ValidationReport`` shape from ``epra.ingest.validate``
verbatim, renamed here to ``ModelBuildResult``/``BuildReport``.

Implements: D-02, D-05, D-06 (stand-in flags), DM-060..066.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from epra.common import logging as common_logging
from epra.common.config import REPO_ROOT, Settings, load_settings
from epra.common.db import connect

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result/Report framework -- verbatim reuse of validate.GateResult/ValidationReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelBuildResult:
    """One build-report row's outcome (one dbt model or DM-06x sanity number).

    Attributes:
        model_id: short label, e.g. ``"fct_price_hourly row counts (DM-062)"``.
        passed: ``True`` if the row's data was readable / within tolerance.
        summary: one-line human-readable outcome (used in the report table).
        evidence: optional detail frame (per-year counts, month coverage,
            reconciliation numbers, ...); ``None`` when nothing more than
            ``summary`` is needed.
    """

    model_id: str
    passed: bool
    summary: str
    evidence: pd.DataFrame | None = None

    def render_markdown(self) -> str:
        """Render this result as a markdown section for the build report."""
        status = "PASS" if self.passed else "FAIL"
        lines = [f"### {self.model_id} — {status}", "", self.summary]
        if self.evidence is not None and not self.evidence.empty:
            lines += ["", "```", self.evidence.to_string(index=False), "```"]
        return "\n".join(lines)


@dataclass
class BuildReport:
    """Aggregates ``ModelBuildResult``\\ s; renders the markdown build report."""

    results: list[ModelBuildResult] = field(default_factory=list)

    def add(self, result: ModelBuildResult) -> None:
        """Register one row's result."""
        self.results.append(result)

    @property
    def all_passed(self) -> bool:
        """``True`` iff every registered row's data was readable / within tolerance."""
        return all(result.passed for result in self.results)

    def render_markdown(self, *, run_date: date | None = None) -> str:
        """Render the full report: header, overall status, then every row's section."""
        run_date = run_date or date.today()
        overall = "ALL SANITY CHECKS OK" if self.all_passed else "SEE FLAGGED ROW(S) BELOW"
        header = [
            f"# dbt build report — {run_date:%Y-%m-%d}",
            "",
            f"**Overall: {overall}**",
            "",
            "D-02 human-readable sanity report over the built warehouse. Pass/fail "
            "*enforcement* of DM-050/062/064/065/066 belongs to the dbt build's own "
            "tests (04-06) -- this report only surfaces the numbers for a human "
            "reviewer.",
        ]
        body = [result.render_markdown() for result in self.results]
        return "\n\n".join([*header, *body]) + "\n"


# ---------------------------------------------------------------------------
# Sanity-number queries -- read-only against the built `marts` schema.
# ---------------------------------------------------------------------------

_STAND_IN_MARTS: tuple[str, ...] = ("fct_consumer_load_hourly", "fct_procurement_cost_monthly")


def _price_hourly_row_counts(con: duckdb.DuckDBPyConnection) -> ModelBuildResult:
    """DM-062 sanity number: per-year ``fct_price_hourly`` row counts."""
    frame = con.execute(
        "select year_local, count(*) as n_hours "
        "from marts.fct_price_hourly group by year_local order by year_local"
    ).fetchdf()
    if frame.empty:
        return ModelBuildResult(
            "fct_price_hourly row counts (DM-062)",
            False,
            "no rows in marts.fct_price_hourly -- has `dbt build` run?",
            None,
        )
    return ModelBuildResult(
        "fct_price_hourly row counts (DM-062)",
        True,
        f"{len(frame)} year(s) reported (per-year hour counts below; the DM-062 "
        "+/-24 boundary tolerance is enforced by dbt's own build-time test, not "
        "recomputed here)",
        frame,
    )


def _monthly_mart_coverage(con: duckdb.DuckDBPyConnection) -> ModelBuildResult:
    """DM-050 sanity number: month coverage per monthly mart."""
    frame = con.execute(
        """
        select 'fct_price_monthly' as mart_name,
               min(make_date(year_local, month_local, 1)) as min_month,
               max(make_date(year_local, month_local, 1)) as max_month,
               count(distinct make_date(year_local, month_local, 1)) as n_months
        from marts.fct_price_monthly
        union all
        select 'fct_generation_monthly',
               min(make_date(year_local, month_local, 1)),
               max(make_date(year_local, month_local, 1)),
               count(distinct make_date(year_local, month_local, 1))
        from marts.fct_generation_monthly
        union all
        select 'fct_procurement_cost_monthly',
               min(make_date(year_local, month_local, 1)),
               max(make_date(year_local, month_local, 1)),
               count(distinct make_date(year_local, month_local, 1))
        from marts.fct_procurement_cost_monthly
        order by mart_name
        """
    ).fetchdf()
    if frame.empty:
        return ModelBuildResult(
            "monthly-mart month coverage (DM-050)",
            False,
            "no rows in any monthly mart -- has `dbt build` run?",
            None,
        )
    return ModelBuildResult(
        "monthly-mart month coverage (DM-050)",
        True,
        f"{len(frame)} monthly mart(s) reported (min/max month + distinct month count; "
        "the DM-050 no-gap check itself is enforced by dbt's own build-time test)",
        frame,
    )


def _reconciliation_2022_08(con: duckdb.DuckDBPyConnection) -> ModelBuildResult:
    """DM-064 sanity number: ``fct_price_monthly`` 2022-08 base vs mean-of-hourly delta."""
    row = con.execute(
        """
        select
            (select avg(price_at_eur_mwh) from marts.fct_price_hourly
             where year_local = 2022 and month_local = 8) as hourly_mean,
            (select price_base_eur_mwh from marts.fct_price_monthly
             where year_local = 2022 and month_local = 8) as monthly_base
        """
    ).fetchone()
    if row is None or row[0] is None or row[1] is None:
        return ModelBuildResult(
            "2022-08 reconciliation delta (DM-064)",
            False,
            "no 2022-08 data in fct_price_hourly/fct_price_monthly -- has `dbt build` run?",
            None,
        )
    hourly_mean, monthly_base = float(row[0]), float(row[1])
    delta = monthly_base - hourly_mean
    ok = abs(delta) <= 0.01
    evidence = pd.DataFrame(
        [
            {
                "monthly_base_eur_mwh": round(monthly_base, 4),
                "hourly_mean_eur_mwh": round(hourly_mean, 4),
                "delta": round(delta, 4),
            }
        ]
    )
    summary = (
        "fct_price_monthly.price_base_eur_mwh matches mean(fct_price_hourly.price_at_eur_mwh) "
        f"for 2022-08 within 0.01 (delta={delta:.4f})"
        if ok
        else f"2022-08 reconciliation delta {delta:.4f} exceeds 0.01 tolerance"
    )
    return ModelBuildResult("2022-08 reconciliation delta (DM-064)", ok, summary, evidence)


def _stand_in_flag() -> ModelBuildResult:
    """D-05/D-06: flag the two marts still backed by synthetic/thin-loader stand-ins."""
    evidence = pd.DataFrame(
        [{"mart": mart, "status": "stand-in (M4/M6 pending)"} for mart in _STAND_IN_MARTS]
    )
    summary = (
        "fct_consumer_load_hourly (M4 consumer profile pending) and "
        "fct_procurement_cost_monthly (M6 strategy simulator pending) are thin loaders "
        "over synthetic/stand-in data, not real module output yet (D-05/D-06)"
    )
    return ModelBuildResult("future marts", True, summary, evidence)


def build_report(settings: Settings) -> BuildReport:
    """D-02: query the built warehouse (read-only) for the M3 build-report sanity numbers.

    Opens ``epra.common.db.connect(settings, read_only=True)`` -- never writes to the
    warehouse; the marts themselves are built exclusively by ``dbt build`` (SPEC-02).
    """
    con = connect(settings, read_only=True)
    try:
        report = BuildReport()
        report.add(_price_hourly_row_counts(con))
        report.add(_monthly_mart_coverage(con))
        report.add(_reconciliation_2022_08(con))
        report.add(_stand_in_flag())
        return report
    finally:
        con.close()


def _write_report(report: BuildReport, settings: Settings) -> Path:
    reports_root = settings.paths.reports
    reports_root = reports_root if reports_root.is_absolute() else REPO_ROOT / reports_root
    warehouse_dir = reports_root / "warehouse"
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    report_path = warehouse_dir / f"dbt_build_{date.today():%Y-%m-%d}.md"
    report_path.write_text(report.render_markdown(), encoding="utf-8")
    return report_path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.warehouse.report`` -- read the built warehouse, write the D-02 report.

    Returns 0 on success, 1 if reading the warehouse fails (e.g. ``dbt build``
    has not been run yet).
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.warehouse.report",
        description="Read the built dbt warehouse (read-only) and write the D-02 build report.",
    )
    parser.parse_args(argv)

    settings = load_settings()
    logfile = settings.paths.reports / "warehouse" / f"dbt_build_{date.today():%Y-%m-%d}.log"
    common_logging.setup(logfile=logfile)

    try:
        report = build_report(settings)
    except duckdb.Error as exc:
        logger.error("build report read failed: %s", exc)
        return 1

    report_path = _write_report(report, settings)
    logger.info("build report written to %s", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
