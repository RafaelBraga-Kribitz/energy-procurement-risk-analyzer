"""Ingestion validation gates — ``make validate-ingest`` (M1/M2).

Binding contract: SPEC-01 §8 (ENTSO-E, implemented here), §9 (GeoSphere,
M2), §10 (ÖSPI, M2). Results are written to
``reports/ingestion/validation_<date>.md``.

Gate summary (fail-fast per EN-061 — a failed gate raises, never warns):

- ING-080 hour coverage per zone-year (≤ 24 missing; DST 23/25 check)
- ING-081 price bounds −500..5000 EUR/MWh (out of range ⇒ investigate, not clip)
- ING-082 annual mean plausibility table (per-year ranges; widening needs ADR)
- ING-083 negative prices must exist in 2023/2024/2025 (else parser bug)
- ING-084 load plausibility 3000-13000 MW hourly, 6000-9000 MW annual mean
- ING-085 price↔load join coverage ≥ 99.5% per year
- ING-094 GeoSphere coverage/range/seasonal means (M2, not yet implemented)
- ING-101/103 ÖSPI reconciliation + series gates (M2, not yet implemented)

A-2 applies verbatim: on failure, investigate the pipeline — never adjust data
to pass, never widen a gate without an ADR.

Implements: ING-080, ING-081, ING-082, ING-083, ING-084, ING-085 (M1).
"""

from __future__ import annotations

import argparse
import logging
from calendar import isleap, monthrange
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from epra.common import logging as common_logging
from epra.common.config import REPO_ROOT, Settings, load_settings
from epra.common.timeutil import VIENNA, local_hours_in_day
from epra.ingest.entsoe import hourly_mean
from epra.ingest.exceptions import GateFailure

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gate framework (03_MODULES `epra.ingest.validate`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateResult:
    """One SPEC-01 §8 gate's outcome.

    Attributes:
        gate_id: SPEC REQ ID, e.g. ``"ING-082"``.
        passed: ``True`` if the gate's condition holds.
        summary: one-line human-readable outcome (used in the report table).
        evidence: optional detail frame (missing hours, out-of-range rows,
            ...); ``None`` when nothing more than ``summary`` is needed.
    """

    gate_id: str
    passed: bool
    summary: str
    evidence: pd.DataFrame | None = None

    def render_markdown(self) -> str:
        """Render this result as a markdown section for the validation report."""
        status = "PASS" if self.passed else "FAIL"
        lines = [f"### {self.gate_id} — {status}", "", self.summary]
        if self.evidence is not None and not self.evidence.empty:
            lines += ["", "```", self.evidence.to_string(index=False), "```"]
        return "\n".join(lines)


@dataclass
class ValidationReport:
    """Aggregates ``GateResult``\\ s; renders the markdown report; raises on failure.

    Invariant: lists every registered gate exactly once — no silent skips
    (T-02-13, EN-061).
    """

    results: list[GateResult] = field(default_factory=list)

    def add(self, result: GateResult) -> None:
        """Register one gate's result."""
        self.results.append(result)

    @property
    def all_passed(self) -> bool:
        """``True`` iff every registered gate passed."""
        return all(result.passed for result in self.results)

    def render_markdown(self, *, run_date: date | None = None) -> str:
        """Render the full report: header, overall status, then every gate section."""
        run_date = run_date or date.today()
        overall = "ALL GATES PASSED" if self.all_passed else "GATE FAILURE(S) — see below"
        header = [
            f"# Ingestion validation report — {run_date:%Y-%m-%d}",
            "",
            f"**Overall: {overall}**",
        ]
        body = [result.render_markdown() for result in self.results]
        return "\n\n".join([*header, *body]) + "\n"

    def raise_if_failed(self) -> None:
        """Raise ``GateFailure`` naming every failed gate id (EN-061). No-op if all passed."""
        failed = [result for result in self.results if not result.passed]
        if not failed:
            return
        gate_ids = ", ".join(result.gate_id for result in failed)
        summary = "; ".join(f"{result.gate_id}: {result.summary}" for result in failed)
        raise GateFailure(gate_ids, summary)


# ---------------------------------------------------------------------------
# ING-080..085 gate functions — pure, no mutation, no I/O (03_MODULES).
# ---------------------------------------------------------------------------

_PRICE_MIN_EUR_MWH = -500.0
_PRICE_MAX_EUR_MWH = 5000.0

#: SPEC-01 §8 ING-082 annual mean plausibility table. Widening a range here
#: needs an ADR (T-02-12, A-2) — never edit to make a gate pass.
_ANNUAL_MEAN_RANGE_EUR_MWH: dict[int, tuple[float, float]] = {
    2019: (25, 55),
    2020: (20, 50),
    2021: (80, 130),
    2022: (200, 320),
    2023: (70, 140),
    2024: (50, 110),
    2025: (40, 140),
}

_NEGATIVE_PRICE_REQUIRED_YEARS = (2023, 2024, 2025)

_LOAD_HOURLY_MIN_MW = 3000.0
_LOAD_HOURLY_MAX_MW = 13000.0
_LOAD_ANNUAL_MEAN_MIN_MW = 6000.0
_LOAD_ANNUAL_MEAN_MAX_MW = 9000.0

_JOIN_COVERAGE_MIN = 0.995


def _last_sunday(year: int, month: int) -> date:
    """First day-of-month's last Sunday — used for the ING-080 DST check dates."""
    last_day = date(year, month, monthrange(year, month)[1])
    offset = (last_day.weekday() - 6) % 7  # Python weekday(): Mon=0 .. Sun=6
    return last_day - timedelta(days=offset)


def gate_ing_080(hourly_by_zone: dict[str, pd.DataFrame]) -> GateResult:
    """ING-080: hour coverage per zone-year (≤24 missing) + DST 23/25 correctness check.

    Args:
        hourly_by_zone: dataset/zone label -> hourly-aggregated frame with a
            ``ts_utc`` column (already floored to the hour, e.g. via
            :func:`epra.ingest.entsoe.hourly_mean` — aggregating BEFORE this
            gate avoids false-missing-hours on PT15M-resolution raw data).
    """
    rows: list[dict[str, object]] = []
    all_ok = True
    for zone, frame in hourly_by_zone.items():
        if frame.empty:
            continue
        ts = frame["ts_utc"]
        for year_val in sorted(ts.dt.year.unique()):
            year = int(year_val)
            year_ts = ts[ts.dt.year == year]
            expected_hours = (366 if isleap(year) else 365) * 24
            actual_hours = int(year_ts.dt.floor("h").nunique())
            missing = expected_hours - actual_hours
            coverage_ok = missing <= 24
            all_ok = all_ok and coverage_ok
            rows.append(
                {
                    "zone": zone,
                    "year": year,
                    "check": "coverage",
                    "expected": expected_hours,
                    "actual": actual_hours,
                    "missing_hours": missing,
                    "ok": coverage_ok,
                }
            )

            local_dates = year_ts.dt.tz_convert(VIENNA).dt.date
            for month, label in ((3, "dst_mar"), (10, "dst_oct")):
                dst_date = _last_sunday(year, month)
                on_day = int((local_dates == dst_date).sum())
                if on_day == 0:
                    continue  # date isn't present at all -- coverage already flags it
                expected_local = local_hours_in_day(dst_date)
                dst_ok = on_day == expected_local
                all_ok = all_ok and dst_ok
                rows.append(
                    {
                        "zone": zone,
                        "year": year,
                        "check": label,
                        "expected": expected_local,
                        "actual": on_day,
                        "missing_hours": None,
                        "ok": dst_ok,
                    }
                )

    if not rows:
        return GateResult("ING-080", False, "no data supplied to ING-080 (nothing to check)", None)

    evidence = pd.DataFrame(rows)
    failing = evidence.loc[~evidence["ok"]]
    summary = (
        "all zone-years within coverage (<=24 missing hours); DST hour counts correct"
        if all_ok
        else f"{len(failing)} zone-year check(s) failed (see evidence)"
    )
    return GateResult("ING-080", all_ok, summary, evidence)


def gate_ing_081(prices_hourly: pd.DataFrame) -> GateResult:
    """ING-081: hourly AT price plausibility, −500 ≤ price ≤ 5000 EUR/MWh.

    Out-of-range values are a hard fail — investigate the pipeline, never clip.
    """
    if prices_hourly.empty:
        return GateResult("ING-081", False, "no AT price data supplied to ING-081", None)
    prices = prices_hourly["price_eur_mwh"]
    out_of_range = prices_hourly.loc[(prices < _PRICE_MIN_EUR_MWH) | (prices > _PRICE_MAX_EUR_MWH)]
    ok = out_of_range.empty
    summary = (
        f"all {len(prices_hourly)} hourly AT price(s) within "
        f"[{_PRICE_MIN_EUR_MWH}, {_PRICE_MAX_EUR_MWH}] EUR/MWh"
        if ok
        else f"{len(out_of_range)} hourly price(s) outside "
        f"[{_PRICE_MIN_EUR_MWH}, {_PRICE_MAX_EUR_MWH}] EUR/MWh"
    )
    return GateResult("ING-081", ok, summary, None if ok else out_of_range)


def gate_ing_082(prices_hourly: pd.DataFrame) -> GateResult:
    """ING-082: AT day-ahead annual mean must fall in the SPEC-01 §8 per-year table.

    A year outside the documented table (not just outside its range) also
    fails — a new year needs the table extended via ADR, not silently skipped.
    """
    rows: list[dict[str, object]] = []
    all_ok = True
    for year_val, group in prices_hourly.groupby(prices_hourly["ts_utc"].dt.year):
        year = int(year_val)
        mean_price = float(group["price_eur_mwh"].mean())
        bounds = _ANNUAL_MEAN_RANGE_EUR_MWH.get(year)
        ok = bounds is not None and bounds[0] <= mean_price <= bounds[1]
        all_ok = all_ok and ok
        rows.append(
            {
                "year": year,
                "mean_price_eur_mwh": round(mean_price, 2),
                "expected_range": bounds,
                "ok": ok,
            }
        )

    if not rows:
        return GateResult("ING-082", False, "no AT price data supplied to ING-082", None)

    evidence = pd.DataFrame(rows)
    failing = evidence.loc[~evidence["ok"]]
    summary = (
        "all annual means within the SPEC-01 §8 plausibility table"
        if all_ok
        else f"{len(failing)} year(s) outside plausibility table (see evidence)"
    )
    return GateResult("ING-082", all_ok, summary, evidence)


def gate_ing_083(prices_hourly: pd.DataFrame) -> GateResult:
    """ING-083: at least one negative hourly AT price in each of 2023/2024/2025.

    Zero negatives across all three years indicates a parser bug (fail).
    """
    rows: list[dict[str, object]] = []
    all_ok = True
    for year in _NEGATIVE_PRICE_REQUIRED_YEARS:
        year_prices = prices_hourly.loc[prices_hourly["ts_utc"].dt.year == year, "price_eur_mwh"]
        n_negative = int((year_prices < 0).sum())
        ok = n_negative > 0
        all_ok = all_ok and ok
        rows.append({"year": year, "n_negative": n_negative, "ok": ok})

    evidence = pd.DataFrame(rows)
    summary = (
        "at least one negative hourly AT price present in each of 2023/2024/2025"
        if all_ok
        else "no negative price found in one or more of 2023/2024/2025 (likely parser bug)"
    )
    return GateResult("ING-083", all_ok, summary, evidence)


def gate_ing_084(load_hourly: pd.DataFrame) -> GateResult:
    """ING-084: AT load plausibility -- hourly 3000-13000 MW, annual mean 6000-9000 MW."""
    if load_hourly.empty:
        return GateResult("ING-084", False, "no AT load data supplied to ING-084", None)
    load = load_hourly["load_mw"]
    out_of_range = load_hourly.loc[(load < _LOAD_HOURLY_MIN_MW) | (load > _LOAD_HOURLY_MAX_MW)]
    hourly_ok = out_of_range.empty

    year_key = load_hourly["ts_utc"].dt.year.rename("year")
    annual = load_hourly.groupby(year_key)["load_mw"].mean()
    annual_out_of_band = (annual < _LOAD_ANNUAL_MEAN_MIN_MW) | (annual > _LOAD_ANNUAL_MEAN_MAX_MW)
    annual_bad = annual.loc[annual_out_of_band]
    annual_ok = annual_bad.empty

    ok = hourly_ok and annual_ok
    parts = []
    if not hourly_ok:
        parts.append(
            f"{len(out_of_range)} hourly load value(s) outside "
            f"[{_LOAD_HOURLY_MIN_MW}, {_LOAD_HOURLY_MAX_MW}] MW"
        )
    if not annual_ok:
        parts.append(
            f"{len(annual_bad)} year(s) with annual mean outside "
            f"[{_LOAD_ANNUAL_MEAN_MIN_MW}, {_LOAD_ANNUAL_MEAN_MAX_MW}] MW"
        )
    summary = (
        "; ".join(parts) if parts else "AT load within hourly and annual mean plausibility bands"
    )

    evidence: pd.DataFrame | None
    if not hourly_ok:
        evidence = out_of_range
    elif not annual_ok:
        evidence = annual_bad.rename("annual_mean_mw").reset_index()
    else:
        evidence = None
    return GateResult("ING-084", ok, summary, evidence)


def gate_ing_085(prices_hourly: pd.DataFrame, load_hourly: pd.DataFrame) -> GateResult:
    """ING-085: every priced hour must have a load value -- join coverage >=99.5% per year."""
    rows: list[dict[str, object]] = []
    all_ok = True
    for year_val, price_group in prices_hourly.groupby(prices_hourly["ts_utc"].dt.year):
        year = int(year_val)
        price_hours = set(price_group["ts_utc"])
        load_hours = set(load_hourly.loc[load_hourly["ts_utc"].dt.year == year, "ts_utc"])
        matched = price_hours & load_hours
        coverage = (len(matched) / len(price_hours)) if price_hours else 0.0
        ok = coverage >= _JOIN_COVERAGE_MIN
        all_ok = all_ok and ok
        rows.append(
            {
                "year": year,
                "price_hours": len(price_hours),
                "matched_hours": len(matched),
                "coverage": round(coverage, 4),
                "ok": ok,
            }
        )

    if not rows:
        return GateResult("ING-085", False, "no AT price data supplied to ING-085", None)

    evidence = pd.DataFrame(rows)
    failing = evidence.loc[~evidence["ok"]]
    summary = (
        "price/load join coverage >=99.5% for every year"
        if all_ok
        else f"{len(failing)} year(s) below 99.5% price/load join coverage (see evidence)"
    )
    return GateResult("ING-085", all_ok, summary, evidence)


# ---------------------------------------------------------------------------
# run_gates -- loads raw parquet, aggregates to hourly mean, runs all M1 gates
# ---------------------------------------------------------------------------

#: (dataset dir name, value column) for the three ENTSO-E hourly inputs the M1
#: gates need. Generation (`entsoe_gen_at`) has no §8 gate defined -- excluded.
_HOURLY_DATASETS: tuple[tuple[str, str], ...] = (
    ("entsoe_prices_at", "price_eur_mwh"),
    ("entsoe_prices_delu", "price_eur_mwh"),
    ("entsoe_load_at", "load_mw"),
)


def _dataset_root(dataset: str, settings: Settings) -> Path:
    root = settings.paths.data_raw
    root = root if root.is_absolute() else REPO_ROOT / root
    return root / dataset


def _load_hourly(dataset: str, value_col: str, settings: Settings) -> pd.DataFrame:
    """Glob-read every monthly raw parquet for ``dataset``, aggregate to hourly mean.

    Aggregating BEFORE gating (via ``entsoe.hourly_mean``) avoids ING-080
    false-missing-hours on PT15M-resolution months (RESEARCH pitfall 6).
    """
    root = _dataset_root(dataset, settings)
    # Typed-empty (not bare `columns=[...]`) so `.dt`/numeric comparisons in
    # the gate functions work even when a dataset has no ingested data yet.
    empty = pd.DataFrame(
        {
            "ts_utc": pd.Series([], dtype="datetime64[ns, UTC]"),
            value_col: pd.Series([], dtype="float64"),
        }
    )
    if not root.exists():
        return empty
    paths = sorted(root.glob("*/*.parquet"))
    if not paths:
        return empty
    frames = [pd.read_parquet(path, columns=["ts_utc", value_col]) for path in paths]
    raw = pd.concat(frames, ignore_index=True)
    return hourly_mean(raw, value_col)


def _write_report(report: ValidationReport, settings: Settings) -> Path:
    reports_root = settings.paths.reports
    reports_root = reports_root if reports_root.is_absolute() else REPO_ROOT / reports_root
    ingestion_dir = reports_root / "ingestion"
    ingestion_dir.mkdir(parents=True, exist_ok=True)
    report_path = ingestion_dir / f"validation_{date.today():%Y-%m-%d}.md"
    report_path.write_text(report.render_markdown(), encoding="utf-8")
    return report_path


def run_gates(settings: Settings) -> None:
    """Run all M1 ENTSO-E gates (ING-080..085); write report; raise on failure (EN-061).

    Loads every monthly raw parquet for the three hourly ENTSO-E datasets
    under ``settings.paths.data_raw``, aggregates each to hourly mean, runs
    ING-080..085 in order, writes ``reports/ingestion/validation_<date>.md``
    listing every registered gate exactly once (T-02-13), then raises
    ``GateFailure`` if any gate failed (A-2 -- never warn-and-continue).
    """
    hourly = {
        dataset: _load_hourly(dataset, value_col, settings)
        for dataset, value_col in _HOURLY_DATASETS
    }
    at_prices = hourly["entsoe_prices_at"]
    at_load = hourly["entsoe_load_at"]

    report = ValidationReport()
    report.add(gate_ing_080(hourly))
    report.add(gate_ing_081(at_prices))
    report.add(gate_ing_082(at_prices))
    report.add(gate_ing_083(at_prices))
    report.add(gate_ing_084(at_load))
    report.add(gate_ing_085(at_prices, at_load))

    for result in report.results:
        logger.info("gate=%s passed=%s summary=%s", result.gate_id, result.passed, result.summary)

    report_path = _write_report(report, settings)
    logger.info("validation report written to %s", report_path)

    report.raise_if_failed()


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.validate`` -- run all M1 gates, write the report.

    Returns 0 if every gate passed, 1 if any gate failed (``GateFailure``).
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.ingest.validate",
        description="Run all M1 ENTSO-E validation gates (ING-080..085) and write the report.",
    )
    parser.parse_args(argv)

    settings = load_settings()
    logfile = settings.paths.reports / "ingestion" / f"validate_{date.today():%Y-%m-%d}.log"
    common_logging.setup(logfile=logfile)

    try:
        run_gates(settings)
    except GateFailure as exc:
        logger.error("validation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
