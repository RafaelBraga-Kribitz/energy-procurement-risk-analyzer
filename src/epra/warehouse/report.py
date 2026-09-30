"""Warehouse build report -- ``make warehouse`` / ``python -m epra.warehouse.report`` (M3).

Binding contract: SPEC-02 §6 (DM-060..066 -- "all must pass in ``dbt build``")
and DM-020 (pre-dedup duplicate count *warns*). Results are written to
``reports/warehouse/dbt_build_<date>.md``.

This module never builds or mutates the warehouse -- ``cd dbt && dbt build``
(``make transform``) is the only writer (SPEC-02, DM-002). After a build it
renders, for a human reviewer:

1. **The dbt build's own outcome**, read from ``dbt/target/run_results.json``:
   per-node status counts (pass / warn / error / skip) and the name of every
   WARN or ERROR node (e.g. the DM-020 ``predup_count_prices`` warning). The
   report headline is driven by these results first -- it can no longer say
   "OK" while a dbt test warned or failed, and it says so explicitly when
   ``run_results.json`` is missing (test outcomes then NOT recorded).
2. **Key sanity numbers**, read-only via ``epra.common.db.connect(settings,
   read_only=True)``: per-year ``fct_price_hourly`` row counts (DM-062),
   monthly-mart month coverage (DM-050), the 2022-08 ``fct_price_monthly`` vs
   mean-of-hourly reconciliation delta (DM-064), and an explicit flag on the
   two marts still backed by stand-in data (``fct_consumer_load_hourly``,
   ``fct_procurement_cost_monthly``; ADR-010, M4/M6 pending).

Pass/fail *enforcement* of DM-050/060..066 belongs to the dbt tests
themselves; this report surfaces their outcome and the numbers behind them.
The result/report rendering is the shared ``epra.common.gates`` framework
(also behind ``epra.ingest.validate``).

Implements: DM-050, DM-062, DM-064 (sanity numbers surfaced), DM-020 and
DM-060..066 (dbt test outcomes recorded in the report), ADR-010 (stand-in flag).
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from epra.common import logging as common_logging
from epra.common.config import Settings, load_settings, resolve_repo_path
from epra.common.db import connect
from epra.common.gates import CheckReport, CheckResult
from epra.common.timeutil import today_local

logger = logging.getLogger(__name__)

#: dbt's per-invocation results file, relative to REPO_ROOT (dbt project at ``dbt/``,
#: default ``target-path``). Written by every ``dbt build``/``dbt test`` run.
DBT_RUN_RESULTS = Path("dbt") / "target" / "run_results.json"

#: dbt node status -> report bucket. Unknown statuses count as ``error`` so the
#: headline never claims OK on a status this module does not understand.
_STATUS_BUCKET: dict[str, str] = {
    "pass": "pass",
    "success": "pass",
    "warn": "warn",
    "partial success": "warn",
    "fail": "error",
    "error": "error",
    "runtime error": "error",
    "skipped": "skip",
    "no-op": "skip",
}
_BUCKETS: tuple[str, ...] = ("pass", "warn", "error", "skip")


# ---------------------------------------------------------------------------
# Result/Report types -- thin domain aliases over epra.common.gates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelBuildResult(CheckResult):
    """One build-report sanity row (one mart or DM-06x sanity number).

    Construct positionally: ``ModelBuildResult(model_id, passed, summary, evidence)``.

    Implements: DM-050, DM-062, DM-064 (one row per surfaced sanity number).
    """

    @property
    def model_id(self) -> str:
        """Row label, e.g. ``"fct_price_hourly row counts (DM-062)"``.

        Implements: DM-062 (row labels cite the SPEC-02 §6 test they mirror).
        """
        return self.check_id


@dataclass(frozen=True)
class DbtRunSummary:
    """Per-node outcome of the last dbt invocation, from ``run_results.json``.

    Implements: DM-060..066 (records whether the SPEC-02 §6 tests passed),
    DM-020 (a WARN such as ``predup_count_prices`` is named, not hidden).
    """

    source: Path
    invocation: str | None
    generated_at: str | None
    counts: dict[str, int]
    warn_nodes: tuple[str, ...]
    error_nodes: tuple[str, ...]

    @property
    def status(self) -> str:
        """``ERROR`` if any node errored/failed, else ``WARN`` if any warned, else ``PASS``.

        Implements: DM-060..066 (all must pass in ``dbt build``).
        """
        if self.error_nodes:
            return "ERROR"
        return "WARN" if self.warn_nodes else "PASS"

    def render_markdown(self) -> str:
        """Render the dbt-results section: counts table plus every WARN/ERROR node.

        Implements: DM-020, DM-060..066.
        """
        counts = ", ".join(f"{bucket}={self.counts.get(bucket, 0)}" for bucket in _BUCKETS)
        lines = [
            f"### dbt build results (run_results.json) — {self.status}",
            "",
            f"`dbt {self.invocation or '?'}` generated_at={self.generated_at or '?'}: {counts}",
        ]
        if self.invocation != "build":
            lines += ["", f"Note: last dbt invocation was `{self.invocation}`, not `build`."]
        for label, nodes in (("ERROR/FAIL", self.error_nodes), ("WARN", self.warn_nodes)):
            if nodes:
                lines += ["", f"{label} node(s):", *(f"- `{node}`" for node in nodes)]
        return "\n".join(lines)


def load_run_results(path: Path) -> DbtRunSummary | None:
    """Summarise a dbt ``run_results.json``; ``None`` if the file does not exist.

    Implements: DM-060..066, DM-020 (test outcomes enter the build report).

    Raises:
        ValueError: the file exists but is not a dbt run-results document
            (no ``results`` list) -- a corrupt file must not read as "no tests".
    """
    if not path.exists():
        return None
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise ValueError(f"{path} is not a dbt run_results document (no 'results' list)")
    counts: Counter[str] = Counter()
    warn_nodes: list[str] = []
    error_nodes: list[str] = []
    for node in results:
        bucket = _STATUS_BUCKET.get(str(node.get("status", "")).lower(), "error")
        counts[bucket] += 1
        if bucket == "warn":
            warn_nodes.append(str(node.get("unique_id", "?")))
        elif bucket == "error":
            error_nodes.append(str(node.get("unique_id", "?")))
    metadata = payload.get("metadata") or {}
    return DbtRunSummary(
        source=path,
        invocation=(payload.get("args") or {}).get("which"),
        generated_at=metadata.get("generated_at"),
        counts=dict(counts),
        warn_nodes=tuple(sorted(warn_nodes)),
        error_nodes=tuple(sorted(error_nodes)),
    )


@dataclass
class BuildReport(CheckReport):
    """dbt build outcome + sanity rows, rendered as the markdown build report.

    ``dbt`` is ``None`` when no ``run_results.json`` was found -- the headline
    then states that dbt test outcomes were NOT recorded.

    Implements: DM-020, DM-050, DM-060..066 (see module docstring).
    """

    dbt: DbtRunSummary | None = None

    def overall(self) -> str:
        """Headline: dbt errors/warnings first, then flagged sanity rows; OK only if all clean.

        Implements: DM-060..066 (headline reflects the dbt test results), DM-020.
        """
        issues: list[str] = []
        if self.dbt is None:
            issues.append("dbt run_results.json NOT FOUND — dbt test outcomes not recorded")
        else:
            if self.dbt.error_nodes:
                issues.append(f"{len(self.dbt.error_nodes)} dbt node(s) ERROR/FAIL")
            if self.dbt.warn_nodes:
                issues.append(f"{len(self.dbt.warn_nodes)} dbt WARN(s)")
        if self.failed:
            issues.append(f"{len(self.failed)} sanity row(s) flagged")
        if not issues:
            return "ALL DBT TESTS PASSED; SANITY CHECKS OK"
        return "; ".join(issues) + " — see below"

    def render_markdown(self, *, run_date: date | None = None) -> str:
        """Render the full report: headline, dbt results section, then every sanity row.

        Implements: DM-020, DM-050, DM-060..066.
        """
        dbt_section = (
            self.dbt.render_markdown()
            if self.dbt is not None
            else "### dbt build results (run_results.json) — MISSING\n\n"
            f"`{DBT_RUN_RESULTS.as_posix()}` not found: run `make transform` "
            "(`cd dbt && dbt build`) before this report."
        )
        preamble = (
            "",
            "Human-readable build report over the warehouse (SPEC-02 §6). The dbt "
            "section records the build's own test outcomes; the sanity rows below "
            "only surface key numbers for a reviewer -- their pass/fail enforcement "
            "is the dbt tests' job.",
            dbt_section,
        )
        return self.render_sections(
            title="dbt build report", overall=self.overall(), preamble=preamble, run_date=run_date
        )


# ---------------------------------------------------------------------------
# Sanity-number queries -- read-only against the built `marts` schema.
# ---------------------------------------------------------------------------

_STAND_IN_MARTS: tuple[str, ...] = ("fct_consumer_load_hourly", "fct_procurement_cost_monthly")


def _price_hourly_row_counts(con: duckdb.DuckDBPyConnection) -> ModelBuildResult:
    """DM-062 sanity number: per-year ``fct_price_hourly`` row counts.

    Implements: DM-062.
    """
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
    """DM-050 sanity number: month coverage per monthly mart.

    Implements: DM-050.
    """
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
    """DM-064 sanity number: ``fct_price_monthly`` 2022-08 base vs mean-of-hourly delta.

    Implements: DM-064.
    """
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
    """ADR-010: flag the two marts still backed by synthetic/thin-loader stand-ins."""
    evidence = pd.DataFrame(
        [{"mart": mart, "status": "stand-in (M4/M6 pending)"} for mart in _STAND_IN_MARTS]
    )
    summary = (
        "fct_consumer_load_hourly (M4 consumer profile pending) and "
        "fct_procurement_cost_monthly (M6 strategy simulator pending) are thin loaders "
        "over synthetic/stand-in data, not real module output yet (ADR-010)"
    )
    return ModelBuildResult("future marts", True, summary, evidence)


def build_report(settings: Settings, *, run_results_path: Path | None = None) -> BuildReport:
    """Read the dbt build outcome + query the built warehouse (read-only) for sanity numbers.

    Implements: DM-020, DM-060..066 (dbt test outcomes from ``run_results.json``),
    DM-050, DM-062, DM-064 (sanity numbers), ADR-010 (stand-in flag).

    Args:
        settings: injected config (EN-040).
        run_results_path: dbt results file; defaults to the REPO_ROOT-anchored
            ``dbt/target/run_results.json``. A missing file is reported as
            such in the headline, never as "all passed".

    Opens ``epra.common.db.connect(settings, read_only=True)`` -- never writes to
    the warehouse; the marts are built exclusively by ``dbt build`` (DM-002).

    Raises:
        duckdb.Error: the warehouse or a mart cannot be read (``dbt build`` not run).
        ValueError: ``run_results.json`` exists but is not a dbt results document.
    """
    path = run_results_path if run_results_path is not None else resolve_repo_path(DBT_RUN_RESULTS)
    report = BuildReport(dbt=load_run_results(path))
    con = connect(settings, read_only=True)
    try:
        report.add(_price_hourly_row_counts(con))
        report.add(_monthly_mart_coverage(con))
        report.add(_reconciliation_2022_08(con))
        report.add(_stand_in_flag())
    finally:
        con.close()
    return report


def _write_report(report: BuildReport, settings: Settings) -> Path:
    """Write ``reports/warehouse/dbt_build_<Vienna run-date>.md`` (REPO_ROOT-anchored)."""
    run_date = today_local()
    warehouse_dir = resolve_repo_path(settings.paths.reports) / "warehouse"
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    report_path = warehouse_dir / f"dbt_build_{run_date:%Y-%m-%d}.md"
    report_path.write_text(report.render_markdown(run_date=run_date), encoding="utf-8")
    return report_path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.warehouse.report`` -- read dbt results + warehouse, write the report.

    Returns 0 when the report was written (its headline carries any dbt
    WARN/ERROR, which is also logged at WARNING), 1 if reading the warehouse
    or ``run_results.json`` fails (e.g. ``dbt build`` has not been run yet).

    Implements: EN-060 (REPO_ROOT-anchored logfile), DM-060..066 (report written
    after ``dbt build``).
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.warehouse.report",
        description="Read dbt run_results.json and the built warehouse (read-only); "
        "write the SPEC-02 §6 build report.",
    )
    parser.parse_args(argv)

    settings = load_settings()
    logfile = (
        resolve_repo_path(settings.paths.reports)
        / "warehouse"
        / f"dbt_build_{today_local():%Y-%m-%d}.log"
    )
    common_logging.setup(logfile=logfile)

    try:
        report = build_report(settings)
    except (duckdb.Error, ValueError) as exc:
        logger.error("build report read failed: %s", exc)
        return 1

    report_path = _write_report(report, settings)
    overall = report.overall()
    log = logger.info if overall.startswith("ALL DBT TESTS PASSED") else logger.warning
    log("build report written to %s -- %s", report_path, overall)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
