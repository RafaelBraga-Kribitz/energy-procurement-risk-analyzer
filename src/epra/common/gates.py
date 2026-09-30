"""Shared check-result / check-report framework for the markdown gate reports.

One implementation behind two reports that previously carried verbatim copies
of the same code (audit 2026-09-30 §4):

- ``epra.ingest.validate`` -- ``GateResult`` / ``ValidationReport``, the
  SPEC-01 §8 ingestion validation report
  (``reports/ingestion/validation_<run-date>.md``, fail-fast per EN-061).
- ``epra.warehouse.report`` -- ``ModelBuildResult`` / ``BuildReport``, the
  SPEC-02 §6 dbt build report (``reports/warehouse/dbt_build_<date>.md``).

Each consumer subclasses ``CheckResult``/``CheckReport`` only to keep its
domain vocabulary (``gate_id`` vs ``model_id``) and its own report header;
rendering, aggregation and the pass/fail rule live here, once.

Implements: EN-061 (every registered check is listed exactly once and a failed
check is never silently dropped from the report).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from epra.common.timeutil import today_local


@dataclass(frozen=True)
class CheckResult:
    """One check's outcome -- one markdown section in a gate/build report.

    Attributes:
        check_id: short label, e.g. a SPEC REQ ID (``"ING-082"``) or a model
            sanity-row name (``"fct_price_hourly row counts (DM-062)"``).
        passed: ``True`` if the check's condition holds.
        summary: one-line human-readable outcome.
        evidence: optional detail frame; ``None`` when ``summary`` suffices.

    Implements: EN-061 (a result carries its own pass/fail + evidence so the
    report can never omit why a gate failed).
    """

    check_id: str
    passed: bool
    summary: str
    evidence: pd.DataFrame | None = None

    def render_markdown(self) -> str:
        """Render this result as one ``### <id> — PASS|FAIL`` markdown section.

        Implements: EN-061 (failure evidence is rendered, never swallowed).
        """
        status = "PASS" if self.passed else "FAIL"
        lines = [f"### {self.check_id} — {status}", "", self.summary]
        if self.evidence is not None and not self.evidence.empty:
            lines += ["", "```", self.evidence.to_string(index=False), "```"]
        return "\n".join(lines)


@dataclass
class CheckReport:
    """Aggregates ``CheckResult``\\ s and renders them as one markdown report.

    Invariant: lists every registered check exactly once -- no silent skips.

    Implements: EN-061 (all checks reported; failures surfaced, never hidden).
    """

    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        """Register one check's result.

        Implements: EN-061 (every registered check appears in the report).
        """
        self.results.append(result)

    @property
    def all_passed(self) -> bool:
        """``True`` iff every registered check passed.

        Implements: EN-061 (one failed check fails the whole report).
        """
        return all(result.passed for result in self.results)

    @property
    def failed(self) -> list[CheckResult]:
        """Every registered check that did not pass, in registration order.

        Implements: EN-061.
        """
        return [result for result in self.results if not result.passed]

    def render_sections(
        self,
        *,
        title: str,
        overall: str,
        preamble: Sequence[str] = (),
        run_date: date | None = None,
    ) -> str:
        """Render ``# <title> — <date>``, the overall line, ``preamble``, then each check.

        ``run_date`` defaults to today's Europe/Vienna date (T-1), never the
        machine-local date.

        Implements: EN-061 (every registered check rendered exactly once).
        """
        run_date = run_date or today_local()
        header = [f"# {title} — {run_date:%Y-%m-%d}", "", f"**Overall: {overall}**", *preamble]
        body = [result.render_markdown() for result in self.results]
        return "\n\n".join([*header, *body]) + "\n"
