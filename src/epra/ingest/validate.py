"""Ingestion validation gates — ``make validate-ingest`` (M1/M2).

Binding contract: SPEC-01 §8 (ENTSO-E, implemented here), §9 (GeoSphere,
M2), §10 (ÖSPI, M2). Results are written to
``reports/ingestion/validation_<date>.md``.

Gate summary (fail-fast per EN-061 — a failed gate raises, never warns):

- ING-080 hour coverage per zone-year (≤ 24 missing; DST 23/25 check)
- ING-081 price bounds −500..5000 EUR/MWh (out of range ⇒ investigate, not clip)
- ING-082 annual mean plausibility table (per-year ranges; widening needs ADR)
- ING-083 negative prices must exist in each spec-required year the data covers
  in full (else parser bug) — ADR-006
- ING-084 load plausibility 3000-13000 MW hourly, 6000-9000 MW annual mean
- ING-085 price↔load join coverage ≥ 99.5% per year
- ING-094 GeoSphere coverage ≥99% of days; −30..42°C range; Jul/Jan seasonal means
- ING-101/103 ÖSPI reconciliation + series gates (M2, not yet implemented)

A-2 applies verbatim: on failure, investigate the pipeline — never adjust data
to pass, never widen a gate without an ADR.

Implements: ING-080, ING-081, ING-082, ING-083, ING-084, ING-085 (M1), ING-094 (M2).
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
from epra.ingest._io import _dataset_root
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

# SPEC-01 §8 years where negative day-ahead prices are expected. ING-083 asserts
# only those that are *complete* in the ingested data (ADR-006), so the gate is
# horizon-robust and extends automatically as 2024/2025 fill in.
_NEGATIVE_PRICE_REQUIRED_YEARS = (2023, 2024, 2025)

_LOAD_HOURLY_MIN_MW = 3000.0
_LOAD_HOURLY_MAX_MW = 13000.0
_LOAD_ANNUAL_MEAN_MIN_MW = 6000.0
_LOAD_ANNUAL_MEAN_MAX_MW = 9000.0

_JOIN_COVERAGE_MIN = 0.995

#: SPEC-01 §9 ING-094 GeoSphere plausibility constants. Widening any of these
#: needs an ADR (A-2, EN-061) -- never edit to make a gate pass.
_GEOSPHERE_COVERAGE_MIN = 0.99
_TL_MITTEL_MIN_C = -30.0
_TL_MITTEL_MAX_C = 42.0
_JULY_MEAN_RANGE_C = (15.0, 30.0)
_JANUARY_MEAN_RANGE_C = (-10.0, 8.0)


def _last_sunday(year: int, month: int) -> date:
    """First day-of-month's last Sunday — used for the ING-080 DST check dates."""
    last_day = date(year, month, monthrange(year, month)[1])
    offset = (last_day.weekday() - 6) % 7  # Python weekday(): Mon=0 .. Sun=6
    return last_day - timedelta(days=offset)


def _local_year(frame: pd.DataFrame) -> pd.Series:
    """Vienna-local calendar year for each row (T-1, ADR-006).

    The analytic domain is Europe/Vienna, so per-year gate checks must bucket by
    the local year -- e.g. ``2019-01-01 00:00`` Vienna (stored as
    ``2018-12-31 23:00 UTC``) belongs to local year 2019, not 2018.
    """
    return pd.Series(frame["ts_utc"].dt.tz_convert(VIENNA).dt.year)


def _complete_local_years(*frames: pd.DataFrame) -> set[int]:
    """Vienna-local years the ingested data fully spans (ADR-006).

    A year ``Y`` is *complete* iff ``min_local <= Y-01-01 00:00`` and
    ``max_local >= Y-12-31 23:00``. The leading local year at the window start
    and the trailing local year at the data horizon may be partial by
    construction; gates report those as ``scope="boundary"`` (informational) and
    never fail on them, while still failing on real gaps in complete years (A-2).
    Boundary hours are never trimmed -- that ``2018-12-31 23:00 UTC`` hour is a
    real ``2019-01-01 00:00`` Vienna hour and stays in raw.
    """
    lo: pd.Timestamp | None = None
    hi: pd.Timestamp | None = None
    for frame in frames:
        if frame is None or frame.empty:
            continue
        local = frame["ts_utc"].dt.tz_convert(VIENNA)
        fmin, fmax = local.min(), local.max()
        lo = fmin if lo is None else min(lo, fmin)
        hi = fmax if hi is None else max(hi, fmax)
    if lo is None or hi is None:
        return set()
    complete: set[int] = set()
    # A 1-day grace absorbs the fixed UTC<->Vienna boundary offset (Jan-01 00:00
    # Vienna is stored as Dec-31 23:00 UTC) and a single missing boundary hour --
    # which ING-080's own 24-hour tolerance already forgives. It can never admit
    # a genuinely partial boundary year: the window-start and data-horizon years
    # are short by whole months, not hours.
    for year in range(int(lo.year), int(hi.year) + 1):
        starts_by = pd.Timestamp(year=year, month=1, day=2, tz=VIENNA)
        ends_after = pd.Timestamp(year=year, month=12, day=31, tz=VIENNA)
        if lo <= starts_by and hi >= ends_after:
            complete.add(year)
    return complete


def gate_ing_080(hourly_by_zone: dict[str, pd.DataFrame]) -> GateResult:
    """ING-080: hour coverage per zone-year (≤24 missing) + DST 23/25 correctness check.

    Args:
        hourly_by_zone: dataset/zone label -> hourly-aggregated frame with a
            ``ts_utc`` column (already floored to the hour, e.g. via
            :func:`epra.ingest.entsoe.hourly_mean` — aggregating BEFORE this
            gate avoids false-missing-hours on PT15M-resolution raw data).
    """
    complete = _complete_local_years(*hourly_by_zone.values())
    rows: list[dict[str, object]] = []
    all_ok = True
    for zone, frame in hourly_by_zone.items():
        if frame.empty:
            continue
        ts = frame["ts_utc"]
        local_year = _local_year(frame)
        for year_val in sorted(local_year.unique()):
            year = int(year_val)
            in_scope = year in complete
            year_ts = ts[local_year == year]
            expected_hours = (366 if isleap(year) else 365) * 24
            actual_hours = int(year_ts.dt.floor("h").nunique())
            missing = expected_hours - actual_hours
            # Boundary years (window start / data horizon) are partial by
            # construction -- report, do not fail (ADR-006).
            coverage_ok = (missing <= 24) if in_scope else True
            all_ok = all_ok and coverage_ok
            rows.append(
                {
                    "zone": zone,
                    "year": year,
                    "check": "coverage",
                    "expected": expected_hours,
                    "actual": actual_hours,
                    "missing_hours": missing,
                    "scope": "complete" if in_scope else "boundary",
                    "ok": coverage_ok,
                }
            )

            if not in_scope:
                continue  # a partial boundary year may lack a DST transition day
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
                        "scope": "complete",
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
    complete = _complete_local_years(prices_hourly)
    rows: list[dict[str, object]] = []
    all_ok = True
    for year_val, group in prices_hourly.groupby(_local_year(prices_hourly)):
        year = int(year_val)
        in_scope = year in complete
        mean_price = float(group["price_eur_mwh"].mean())
        bounds = _ANNUAL_MEAN_RANGE_EUR_MWH.get(year)
        # Assert the plausibility table only for complete years; a partial
        # boundary year's mean is not comparable to a full-year range (ADR-006).
        ok = (bounds is not None and bounds[0] <= mean_price <= bounds[1]) if in_scope else True
        all_ok = all_ok and ok
        rows.append(
            {
                "year": year,
                "mean_price_eur_mwh": round(mean_price, 2),
                "expected_range": bounds,
                "scope": "complete" if in_scope else "boundary",
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
    """ING-083: negative hourly AT prices must appear in each spec-required year
    the data covers in full (ADR-006).

    Negative day-ahead prices are a real market feature; zero negatives in a
    complete required year indicates a parser bug (fail). Only the
    ``_NEGATIVE_PRICE_REQUIRED_YEARS`` that are *complete* in the ingested data
    are asserted, so the gate is not brittle to the data horizon -- it extends to
    2024/2025 automatically once those local years complete.
    """
    complete = _complete_local_years(prices_hourly)
    checkable = sorted(y for y in _NEGATIVE_PRICE_REQUIRED_YEARS if y in complete)
    if not checkable:
        return GateResult(
            "ING-083",
            True,
            "no complete year among the negative-price-required years yet -- skipped",
            None,
        )
    local_year = _local_year(prices_hourly)
    rows: list[dict[str, object]] = []
    all_ok = True
    for year in checkable:
        year_prices = prices_hourly.loc[local_year == year, "price_eur_mwh"]
        n_negative = int((year_prices < 0).sum())
        ok = n_negative > 0
        all_ok = all_ok and ok
        rows.append({"year": year, "n_negative": n_negative, "ok": ok})

    evidence = pd.DataFrame(rows)
    yrs = "/".join(str(y) for y in checkable)
    summary = (
        f"at least one negative hourly AT price present in each complete required year ({yrs})"
        if all_ok
        else f"no negative price found in one or more complete required year(s) ({yrs}) "
        "-- likely parser bug"
    )
    return GateResult("ING-083", all_ok, summary, evidence)


def gate_ing_084(load_hourly: pd.DataFrame) -> GateResult:
    """ING-084: AT load plausibility -- hourly 3000-13000 MW, annual mean 6000-9000 MW."""
    if load_hourly.empty:
        return GateResult("ING-084", False, "no AT load data supplied to ING-084", None)
    load = load_hourly["load_mw"]
    out_of_range = load_hourly.loc[(load < _LOAD_HOURLY_MIN_MW) | (load > _LOAD_HOURLY_MAX_MW)]
    hourly_ok = out_of_range.empty

    # Annual mean is only comparable for complete years; a partial boundary
    # year's mean is not asserted (ADR-006). The hourly-range check above still
    # covers every row regardless of year.
    complete = _complete_local_years(load_hourly)
    year_key = _local_year(load_hourly).rename("year")
    annual = load_hourly.groupby(year_key)["load_mw"].mean()
    complete_annual = annual.loc[[y for y in annual.index if int(y) in complete]]
    annual_out_of_band = (complete_annual < _LOAD_ANNUAL_MEAN_MIN_MW) | (
        complete_annual > _LOAD_ANNUAL_MEAN_MAX_MW
    )
    annual_bad = complete_annual.loc[annual_out_of_band]
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
    complete = _complete_local_years(prices_hourly, load_hourly)
    price_local_year = _local_year(prices_hourly)
    load_local_year = _local_year(load_hourly)
    rows: list[dict[str, object]] = []
    all_ok = True
    for year_val, price_group in prices_hourly.groupby(price_local_year):
        year = int(year_val)
        in_scope = year in complete
        price_hours = set(price_group["ts_utc"])
        load_hours = set(load_hourly.loc[load_local_year == year, "ts_utc"])
        matched = price_hours & load_hours
        coverage = (len(matched) / len(price_hours)) if price_hours else 0.0
        # Boundary years are informational (ADR-006).
        ok = (coverage >= _JOIN_COVERAGE_MIN) if in_scope else True
        all_ok = all_ok and ok
        rows.append(
            {
                "year": year,
                "price_hours": len(price_hours),
                "matched_hours": len(matched),
                "coverage": round(coverage, 4),
                "scope": "complete" if in_scope else "boundary",
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


def gate_ing_094(geosphere_daily: pd.DataFrame) -> GateResult:
    """ING-094: GeoSphere coverage >=99%; -30<=tl_mittel<=42; Jul/Jan seasonal means.

    Args:
        geosphere_daily: the §7 GeoSphere frame (``date``, ``station_id``,
            ``tl_mittel_c``, ``parameter_raw``, + ING-004 provenance).

    Coverage's denominator is the number of CALENDAR DAYS spanned by the
    ingested data itself (``min(date)..max(date)``, inclusive) -- NOT an
    hours-based constant copied from the ENTSO-E gates (RESEARCH Pitfall 6).
    Empty input returns ``passed=False`` (A-2 -- no vacuous pass). A missing
    July or January in the data does not fail those specific checks (nothing
    to assert yet), but never counts toward a false "all passed" if coverage
    or range still fail.
    """
    if geosphere_daily.empty:
        return GateResult("ING-094", False, "no GeoSphere data supplied to ING-094", None)

    dates = pd.to_datetime(geosphere_daily["date"])
    n_actual = int(dates.dt.normalize().nunique())
    span_days = int((dates.max() - dates.min()).days) + 1
    coverage = (n_actual / span_days) if span_days else 0.0
    coverage_ok = coverage >= _GEOSPHERE_COVERAGE_MIN

    temps = geosphere_daily["tl_mittel_c"]
    out_of_range = geosphere_daily.loc[(temps < _TL_MITTEL_MIN_C) | (temps > _TL_MITTEL_MAX_C)]
    range_ok = out_of_range.empty

    month = dates.dt.month
    july_mean = float(temps.loc[month == 7].mean()) if (month == 7).any() else None
    january_mean = float(temps.loc[month == 1].mean()) if (month == 1).any() else None
    july_ok = july_mean is None or (_JULY_MEAN_RANGE_C[0] <= july_mean <= _JULY_MEAN_RANGE_C[1])
    january_ok = january_mean is None or (
        _JANUARY_MEAN_RANGE_C[0] <= january_mean <= _JANUARY_MEAN_RANGE_C[1]
    )

    all_ok = coverage_ok and range_ok and july_ok and january_ok

    evidence = pd.DataFrame(
        [
            {
                "check": "coverage",
                "expected": f">={_GEOSPHERE_COVERAGE_MIN:.0%}",
                "actual": f"{coverage:.4f} ({n_actual}/{span_days} days)",
                "ok": coverage_ok,
            },
            {
                "check": "range",
                "expected": f"[{_TL_MITTEL_MIN_C}, {_TL_MITTEL_MAX_C}] degC",
                "actual": f"{len(out_of_range)} row(s) out of range",
                "ok": range_ok,
            },
            {
                "check": "july_mean",
                "expected": str(_JULY_MEAN_RANGE_C),
                "actual": "n/a (no July data)" if july_mean is None else f"{july_mean:.2f}",
                "ok": july_ok,
            },
            {
                "check": "january_mean",
                "expected": str(_JANUARY_MEAN_RANGE_C),
                "actual": (
                    "n/a (no January data)" if january_mean is None else f"{january_mean:.2f}"
                ),
                "ok": january_ok,
            },
        ]
    )
    failing = evidence.loc[~evidence["ok"]]
    summary = (
        "coverage/range/seasonal-mean checks all pass"
        if all_ok
        else f"{len(failing)} ING-094 check(s) failed (see evidence)"
    )
    return GateResult("ING-094", all_ok, summary, evidence)


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
