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
- ING-103 ÖSPI continuity, positivity, crisis visibility (2022≥3×2019), MoM ≤60%
  (ING-101 double-entry reconciliation lives in ``scripts/oespi_reconcile.py``,
  not run through this framework — its own CLI + exit code is the gate)
- ING-111 calendar spine — 2024 Styrian holiday count/fixed holidays, Mon/Sun
  peak-hour correctness (thin wrapper over ``epra.ingest.calendar.build_calendar``)

A missing real ``data/manual/oespi_monthly.csv`` (the ING-101 double-entry
reconciled file, a 03-06 human checkpoint) degrades ``run_gates`` to a
non-fatal informational ING-103 result rather than crashing or failing — D-06
explicitly excludes the real ÖSPI transcription from being a CI/local
blocker. GeoSphere (ING-094) and the calendar spine (ING-111) have no such
carve-out: missing/incomplete data there is a genuine (non-crashing) gate
failure, same as any M1 gate.

A-2 applies verbatim: on failure, investigate the pipeline — never adjust data
to pass, never widen a gate without an ADR.

Implements: ING-080, ING-081, ING-082, ING-083, ING-084, ING-085 (M1), ING-094,
ING-103, ING-111 (M2).
"""

from __future__ import annotations

import argparse
import logging
from calendar import isleap, monthrange
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from holidays.countries.austria import Austria

from epra.common import logging as common_logging
from epra.common.config import Settings, load_settings, resolve_repo_path
from epra.common.gates import CheckReport, CheckResult
from epra.common.timeutil import VIENNA, local_hours_in_day, next_month, today_local
from epra.ingest._io import dataset_root
from epra.ingest.calendar import build_calendar
from epra.ingest.entsoe import hourly_mean, latest_complete_month
from epra.ingest.exceptions import GateFailure, NoDataError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gate framework (03_MODULES `epra.ingest.validate`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateResult(CheckResult):
    """One SPEC-01 §8-§11 gate's outcome (``check_id`` is the SPEC REQ ID).

    Thin domain alias over the shared `epra.common.gates.CheckResult`
    (rendering lives there, once). Construct positionally:
    ``GateResult("ING-082", passed, summary, evidence)``.

    Implements: EN-061 (gate outcome + evidence carried into the report).
    """

    @property
    def gate_id(self) -> str:
        """SPEC REQ ID of the gate, e.g. ``"ING-082"``.

        Implements: EN-061 (failed gates are named by REQ ID).
        """
        return self.check_id


@dataclass
class ValidationReport(CheckReport):
    """Aggregates ``GateResult``\\ s; renders the markdown report; raises on failure.

    Invariant: lists every registered gate exactly once — no silent skips
    (T-02-13, EN-061).

    Implements: EN-061 (fail-fast), SPEC-01 §8 report
    (``reports/ingestion/validation_<run-date>.md``).
    """

    def render_markdown(self, *, run_date: date | None = None) -> str:
        """Render the full report: header, overall status, then every gate section.

        Implements: EN-061 (every registered gate rendered exactly once).
        """
        overall = "ALL GATES PASSED" if self.all_passed else "GATE FAILURE(S) — see below"
        return self.render_sections(
            title="Ingestion validation report", overall=overall, run_date=run_date
        )

    def raise_if_failed(self) -> None:
        """Raise ``GateFailure`` naming every failed gate id (EN-061). No-op if all passed.

        Implements: EN-061.
        """
        failed = self.failed
        if not failed:
            return
        gate_ids = ", ".join(result.check_id for result in failed)
        summary = "; ".join(f"{result.check_id}: {result.summary}" for result in failed)
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

#: SPEC-01 §10 ING-103 ÖSPI series-gate constants. Widening either needs an
#: ADR (A-2, EN-061) -- never edit to make a gate pass.
_OESPI_CRISIS_MULTIPLIER = 3.0
_OESPI_MOM_MAX_ABS_CHANGE = 0.60


def _last_sunday(year: int, month: int) -> date:
    """First day-of-month's last Sunday — used for the ING-080 DST check dates.

    Implements: ING-080 (DST check dates).
    """
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


def _dst_rows(zone: str, year: int, year_ts: pd.Series) -> list[dict[str, object]]:
    """ING-080 DST sub-check rows for one complete zone-year (23 h in March, 25 h in October).

    A DST date absent from the data is skipped -- the coverage row already flags it.

    Implements: ING-080 (DST 23/25 check).
    """
    local_dates = year_ts.dt.tz_convert(VIENNA).dt.date
    rows: list[dict[str, object]] = []
    for month, label in ((3, "dst_mar"), (10, "dst_oct")):
        dst_date = _last_sunday(year, month)
        on_day = int((local_dates == dst_date).sum())
        if on_day == 0:
            continue
        expected_local = local_hours_in_day(dst_date)
        rows.append(
            {
                "zone": zone,
                "year": year,
                "check": label,
                "expected": expected_local,
                "actual": on_day,
                "missing_hours": None,
                "scope": "complete",
                "ok": on_day == expected_local,
            }
        )
    return rows


def _zone_coverage_rows(
    zone: str, frame: pd.DataFrame, complete: set[int]
) -> list[dict[str, object]]:
    """ING-080 coverage (+ DST, complete years only) rows for one zone's hourly frame.

    Implements: ING-080 (ADR-006 boundary-year scoping).
    """
    ts = frame["ts_utc"]
    local_year = _local_year(frame)
    rows: list[dict[str, object]] = []
    for year_val in sorted(local_year.unique()):
        year = int(year_val)
        in_scope = year in complete
        year_ts = ts[local_year == year]
        expected_hours = (366 if isleap(year) else 365) * 24
        actual_hours = int(year_ts.dt.floor("h").nunique())
        missing = expected_hours - actual_hours
        rows.append(
            {
                "zone": zone,
                "year": year,
                "check": "coverage",
                "expected": expected_hours,
                "actual": actual_hours,
                "missing_hours": missing,
                "scope": "complete" if in_scope else "boundary",
                # Boundary years (window start / data horizon) are partial by
                # construction -- report, do not fail (ADR-006).
                "ok": (missing <= 24) if in_scope else True,
            }
        )
        if in_scope:  # a partial boundary year may lack a DST transition day
            rows.extend(_dst_rows(zone, year, year_ts))
    return rows


def gate_ing_080(hourly_by_zone: dict[str, pd.DataFrame]) -> GateResult:
    """ING-080: hour coverage per zone-year (≤24 missing) + DST 23/25 correctness check.

    Implements: ING-080 (ADR-006 boundary-year scoping).

    Args:
        hourly_by_zone: dataset/zone label -> hourly-aggregated frame with a
            ``ts_utc`` column (already floored to the hour, e.g. via
            :func:`epra.ingest.entsoe.hourly_mean` — aggregating BEFORE this
            gate avoids false-missing-hours on PT15M-resolution raw data).
    """
    complete = _complete_local_years(*hourly_by_zone.values())
    rows: list[dict[str, object]] = []
    for zone, frame in hourly_by_zone.items():
        if not frame.empty:
            rows.extend(_zone_coverage_rows(zone, frame, complete))

    if not rows:
        return GateResult("ING-080", False, "no data supplied to ING-080 (nothing to check)", None)

    evidence = pd.DataFrame(rows)
    ok_mask = evidence["ok"].astype(bool)
    all_ok = bool(ok_mask.all())
    summary = (
        "all zone-years within coverage (<=24 missing hours); DST hour counts correct"
        if all_ok
        else f"{int((~ok_mask).sum())} zone-year check(s) failed (see evidence)"
    )
    return GateResult("ING-080", all_ok, summary, evidence)


def gate_ing_081(prices_hourly: pd.DataFrame) -> GateResult:
    """ING-081: hourly AT price plausibility, −500 ≤ price ≤ 5000 EUR/MWh.

    Out-of-range values are a hard fail — investigate the pipeline, never clip.

    Implements: ING-081.
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

    Implements: ING-082 (ADR-006 boundary-year scoping).
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

    Implements: ING-083 (ADR-006).
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
    """ING-084: AT load plausibility -- hourly 3000-13000 MW, annual mean 6000-9000 MW.

    Implements: ING-084 (ADR-006 boundary-year scoping for the annual mean).
    """
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
    """ING-085: every priced hour must have a load value -- join coverage >=99.5% per year.

    Implements: ING-085 (ADR-006 boundary-year scoping).
    """
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


def _checks_result(gate_id: str, checks: list[dict[str, object]], pass_summary: str) -> GateResult:
    """Aggregate ``check/expected/actual/ok`` sub-check rows into one multi-check `GateResult`.

    Shared by the M2 multi-check gates (ING-094, ING-103, ING-111): the gate
    passes iff every sub-check passes; the evidence frame always lists all of
    them so a reviewer sees what passed as well as what failed.

    Implements: ING-094, ING-103, ING-111 (multi-check aggregation).
    """
    evidence = pd.DataFrame(checks)
    ok_mask = evidence["ok"].astype(bool)
    all_ok = bool(ok_mask.all())
    summary = (
        pass_summary
        if all_ok
        else f"{int((~ok_mask).sum())} {gate_id} check(s) failed (see evidence)"
    )
    return GateResult(gate_id, all_ok, summary, evidence)


def _geosphere_coverage_check(
    geosphere_daily: pd.DataFrame, window: tuple[date, date] | None
) -> dict[str, object]:
    """ING-094 coverage sub-check: share of expected days that carry a non-null ``tl_mittel_c``.

    With ``window`` (the ING-093 ``2019-01-01 -> latest`` analysis window), the
    denominator is every calendar day of that window, so a pull that stops
    early (e.g. at 2023-12 while prices run into 2024) FAILS instead of passing
    against its own truncated span. Without ``window`` the denominator falls
    back to the days the data itself spans. Days whose value is NULL (the API
    returned the day but no measurement, A-2 -- never filled) do not count as
    covered.

    Implements: ING-094 (coverage), ING-093 (window).
    """
    dates = pd.to_datetime(geosphere_daily["date"]).dt.normalize()
    has_value = geosphere_daily["tl_mittel_c"].notna().to_numpy()
    if window is None:
        first, last = dates.min().date(), dates.max().date()
    else:
        first, last = window
    in_window = ((dates >= pd.Timestamp(first)) & (dates <= pd.Timestamp(last))).to_numpy()
    n_actual = int(dates[in_window & has_value].nunique())
    span_days = (last - first).days + 1
    coverage = (n_actual / span_days) if span_days > 0 else 0.0
    return {
        "check": "coverage",
        "expected": f">={_GEOSPHERE_COVERAGE_MIN:.0%} of {first}..{last}",
        "actual": f"{coverage:.4f} ({n_actual}/{span_days} days)",
        "ok": coverage >= _GEOSPHERE_COVERAGE_MIN,
    }


def _geosphere_range_check(geosphere_daily: pd.DataFrame) -> dict[str, object]:
    """ING-094 range sub-check: every non-null ``tl_mittel_c`` within -30..42 degC.

    Implements: ING-094.
    """
    temps = geosphere_daily["tl_mittel_c"]
    out_of_range = geosphere_daily.loc[(temps < _TL_MITTEL_MIN_C) | (temps > _TL_MITTEL_MAX_C)]
    return {
        "check": "range",
        "expected": f"[{_TL_MITTEL_MIN_C}, {_TL_MITTEL_MAX_C}] degC",
        "actual": f"{len(out_of_range)} row(s) out of range",
        "ok": out_of_range.empty,
    }


def _geosphere_seasonal_check(
    geosphere_daily: pd.DataFrame, month: int, name: str, bounds: tuple[float, float]
) -> dict[str, object]:
    """ING-094 seasonal-mean sub-check for one calendar month; absent month = nothing to assert.

    Implements: ING-094.
    """
    months = pd.to_datetime(geosphere_daily["date"]).dt.month
    temps = geosphere_daily["tl_mittel_c"]
    mean = float(temps.loc[months == month].mean()) if (months == month).any() else None
    return {
        "check": f"{name.lower()}_mean",
        "expected": str(bounds),
        "actual": f"n/a (no {name} data)" if mean is None else f"{mean:.2f}",
        "ok": mean is None or (bounds[0] <= mean <= bounds[1]),
    }


def gate_ing_094(
    geosphere_daily: pd.DataFrame, *, window: tuple[date, date] | None = None
) -> GateResult:
    """ING-094: GeoSphere coverage >=99%; -30<=tl_mittel<=42; Jul/Jan seasonal means.

    Implements: ING-094 (coverage measured against the ING-093 window).

    Args:
        geosphere_daily: the §7 GeoSphere frame (``date``, ``station_id``,
            ``tl_mittel_c``, ``parameter_raw``, + ING-004 provenance).
        window: inclusive ``(first_day, last_day)`` the data must cover --
            `run_gates` passes ING-093's ``settings.window.start_date ->
            latest complete month`` (ING-042). ``None`` falls back to the
            days the data itself spans (``min(date)..max(date)``), which
            cannot detect a pull that simply stops early.

    Coverage's denominator is CALENDAR DAYS (not an hours-based constant
    copied from the ENTSO-E gates), and only days with a non-null
    ``tl_mittel_c`` count as covered. Empty input returns ``passed=False``
    (A-2 -- no vacuous pass). A missing July or January in the data does not
    fail those specific checks (nothing to assert yet), but never counts
    toward a false "all passed" if coverage or range still fail.
    """
    if geosphere_daily.empty:
        return GateResult("ING-094", False, "no GeoSphere data supplied to ING-094", None)
    checks = [
        _geosphere_coverage_check(geosphere_daily, window),
        _geosphere_range_check(geosphere_daily),
        _geosphere_seasonal_check(geosphere_daily, 7, "July", _JULY_MEAN_RANGE_C),
        _geosphere_seasonal_check(geosphere_daily, 1, "January", _JANUARY_MEAN_RANGE_C),
    ]
    return _checks_result("ING-094", checks, "coverage/range/seasonal-mean checks all pass")


def _oespi_continuity_check(months: pd.PeriodIndex) -> dict[str, object]:
    """ING-103 continuity: every month between min and max present (never interpolated, A-2).

    Implements: ING-103.
    """
    expected_months = pd.period_range(months.min(), months.max(), freq="M")
    missing_months = sorted(str(m) for m in set(expected_months) - set(months))
    return {
        "check": "continuity",
        "expected": "no gaps",
        "actual": f"missing={missing_months}" if missing_months else "none",
        "ok": not missing_months,
    }


def _oespi_positivity_check(oespi: pd.DataFrame) -> dict[str, object]:
    """ING-103 positivity: base always > 0; peak > 0 only where present (ING-104 fallback).

    Implements: ING-103, ING-104.
    """
    base, peak = oespi["oespi_base"], oespi["oespi_peak"]
    n_non_positive = int((base <= 0).sum()) + int((peak.notna() & (peak <= 0)).sum())
    return {
        "check": "positivity",
        "expected": "> 0",
        "actual": f"{n_non_positive} non-positive row(s)",
        "ok": n_non_positive == 0,
    }


def _oespi_crisis_check(base: pd.Series, months: pd.PeriodIndex) -> dict[str, object]:
    """ING-103 crisis visibility: 2022 max base >= 3x the 2019 mean base.

    Implements: ING-103.
    """
    year = months.year
    base_2019 = base.loc[year == 2019]
    base_2022 = base.loc[year == 2022]
    if base_2019.empty or base_2022.empty:
        ok = False
        detail = "2019 and/or 2022 not present in series -- cannot assert crisis visibility"
    else:
        mean_2019 = float(base_2019.mean())
        max_2022 = float(base_2022.max())
        ok = max_2022 >= _OESPI_CRISIS_MULTIPLIER * mean_2019
        detail = (
            f"2022 max={max_2022:.2f} vs 2019 mean={mean_2019:.2f} "
            f"(need >= {_OESPI_CRISIS_MULTIPLIER}x)"
        )
    return {
        "check": "crisis_visibility",
        "expected": f">= {_OESPI_CRISIS_MULTIPLIER}x 2019 mean",
        "actual": detail,
        "ok": ok,
    }


def _oespi_mom_check(base: pd.Series) -> dict[str, object]:
    """ING-103 month-over-month: |relative change| of base between consecutive months <= 60%.

    Implements: ING-103.
    """
    pct_change = base.sort_index().pct_change().abs()
    mom_violations = pct_change.loc[pct_change > _OESPI_MOM_MAX_ABS_CHANGE]
    return {
        "check": "mom_change",
        "expected": f"<= {_OESPI_MOM_MAX_ABS_CHANGE:.0%}",
        "actual": f"{len(mom_violations)} month(s) exceeding threshold",
        "ok": mom_violations.empty,
    }


def gate_ing_103(oespi: pd.DataFrame) -> GateResult:
    """ING-103: ÖSPI series gates -- continuity, positivity, crisis visibility, MoM stability.

    Implements: ING-103 (base-only aware per ING-104).

    Args:
        oespi: the ING-100 month-indexed frame from
            `epra.ingest.oespi.load_oespi` (a `PeriodIndex` named ``month``,
            plus ``oespi_base``/``oespi_peak`` columns -- ``oespi_peak`` may
            be all-NaN under the ING-104 base-only fallback).

    Four independent sub-checks, aggregated into one `GateResult` (mirrors
    `gate_ing_094`'s multi-check style):

    - continuity: every month between the series' min and max is present
      (a gap fails, A-2 -- never silently interpolated).
    - positivity: ``oespi_base`` (and ``oespi_peak`` where present) strictly
      positive throughout.
    - crisis visibility: the max ``oespi_base`` value in 2022 is
      >= 3x the mean ``oespi_base`` value in 2019 -- the crisis must be
      visible in the series a downstream simulator would use.
    - month-over-month change: ``oespi_base``'s relative change between
      consecutive months stays within +/-60% (a bigger jump signals a
      transcription error or a spliced methodology, ING-102/ADR-008).

    Empty input returns ``passed=False`` (A-2 -- no vacuous pass).
    """
    if oespi.empty:
        return GateResult("ING-103", False, "no ÖSPI data supplied to ING-103", None)
    months = pd.PeriodIndex(oespi.index)
    base = oespi["oespi_base"]
    checks = [
        _oespi_continuity_check(months),
        _oespi_positivity_check(oespi),
        _oespi_crisis_check(base, months),
        _oespi_mom_check(base),
    ]
    return _checks_result(
        "ING-103", checks, "continuity/positivity/crisis-visibility/MoM checks all pass"
    )


def _calendar_holiday_checks(calendar_frame: pd.DataFrame) -> list[dict[str, object]]:
    """ING-111 holiday sub-checks: 2024 Styrian holiday set, and Jan 1 / May 1 / Dec 25 flagged.

    Implements: ING-111.
    """
    frame_2024 = calendar_frame.loc[calendar_frame["year_local"] == 2024]
    holiday_dates_2024 = set(frame_2024.loc[frame_2024["is_holiday_at"], "date_local"])
    expected_holidays_2024 = set(Austria(subdiv="6", years=2024).keys())
    fixed_holidays = {date(2024, 1, 1), date(2024, 5, 1), date(2024, 12, 25)}
    return [
        {
            "check": "holiday_count_2024",
            "expected": len(expected_holidays_2024),
            "actual": len(holiday_dates_2024),
            "ok": holiday_dates_2024 == expected_holidays_2024,
        },
        {
            "check": "fixed_holidays",
            "expected": sorted(str(d) for d in fixed_holidays),
            "actual": sorted(str(d) for d in (holiday_dates_2024 & fixed_holidays)),
            "ok": fixed_holidays.issubset(holiday_dates_2024),
        },
    ]


def _calendar_peak_check(calendar_frame: pd.DataFrame) -> dict[str, object]:
    """ING-111 peak sub-check: non-holiday Monday 10:00 local is peak; Sunday 10:00 is not.

    Implements: ING-111.
    """

    def _peak_at(target_date: date, hour: int) -> bool | None:
        match = calendar_frame.loc[
            (calendar_frame["date_local"] == target_date) & (calendar_frame["hour_local"] == hour)
        ]
        return None if match.empty else bool(match.iloc[0]["is_peak_hour"])

    monday_peak = _peak_at(date(2024, 1, 8), 10)  # non-holiday Monday
    sunday_peak = _peak_at(date(2024, 1, 7), 10)  # Sunday
    return {
        "check": "peak_hour_mon_sun",
        "expected": "Mon 2024-01-08 10:00 local=peak; Sun 2024-01-07 10:00 local=off-peak",
        "actual": f"monday_peak={monday_peak}, sunday_peak={sunday_peak}",
        "ok": (monday_peak is True) and (sunday_peak is False),
    }


def gate_ing_111(calendar_frame: pd.DataFrame) -> GateResult:
    """ING-111: calendar spine assertions -- thin wrapper for the aggregate report.

    Implements: ING-111.

    Args:
        calendar_frame: the ING-110 hourly spine from
            :func:`epra.ingest.calendar.build_calendar` (``ts_utc,
            date_local, hour_local, dow_local, is_weekend, is_holiday_at,
            is_peak_hour, year_local, month_local``).

    Reuses the exact assertions already validated for ``build_calendar``
    (``tests/unit/test_calendar.py``) -- this function does not re-derive
    holiday or peak-hour logic (ADR-011), it only surfaces the same checks as
    one ``GateResult`` so ``make validate-ingest`` renders ING-111 alongside
    every other gate.

    Three independent sub-checks, aggregated (mirrors `gate_ing_094`'s style):

    - holiday_count_2024: the set of ``is_holiday_at`` dates in 2024 matches
      ``holidays.Austria(subdiv='6', years=2024)`` exactly.
    - fixed_holidays: Jan 1, May 1, Dec 25 (2024) are all flagged
      ``is_holiday_at``.
    - peak_hour_mon_sun: a known non-holiday Monday 10:00 local is
      ``is_peak_hour`` True; a known Sunday 10:00 local is False.

    Empty input returns ``passed=False`` (A-2 -- no vacuous pass).
    """
    if calendar_frame.empty:
        return GateResult("ING-111", False, "no calendar data supplied to ING-111", None)
    checks = [*_calendar_holiday_checks(calendar_frame), _calendar_peak_check(calendar_frame)]
    return _checks_result(
        "ING-111", checks, "holiday-count/fixed-holiday/peak-hour checks all pass"
    )


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

    Implements: ING-080, ING-081, ING-082, ING-083, ING-084, ING-085 (gate inputs).
    """
    root = dataset_root(dataset, settings)
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


#: SPEC-01 §7 GeoSphere date-keyed columns (ING-004 provenance columns excluded
#: -- gate_ing_094 never needs them, same read-only-what's-needed pattern as
#: `_load_hourly`).
_GEOSPHERE_COLUMNS = ("date", "station_id", "tl_mittel_c", "parameter_raw")


def _load_geosphere(settings: Settings) -> pd.DataFrame:
    """Glob-read every monthly ``geosphere_graz_daily`` raw parquet (ING-094 input).

    Mirrors `_load_hourly`'s missing-directory/no-files -> typed-empty-frame
    behavior (never raises): the real live GeoSphere pull is the 03-06 human
    checkpoint (D-06/D-07), so a fresh checkout with no GeoSphere data yet
    must produce a genuine (non-crashing) ING-094 gate failure, not a
    traceback.

    Implements: ING-094 (gate input).
    """
    root = dataset_root("geosphere_graz_daily", settings)
    empty = pd.DataFrame({col: pd.Series([], dtype="object") for col in _GEOSPHERE_COLUMNS})
    if not root.exists():
        return empty
    paths = sorted(root.glob("*/*.parquet"))
    if not paths:
        return empty
    frames = [pd.read_parquet(path, columns=list(_GEOSPHERE_COLUMNS)) for path in paths]
    return pd.concat(frames, ignore_index=True)


#: ING-110 calendar spine columns -- mirrors `epra.ingest.calendar.build_calendar`'s
#: output exactly, used only as the typed-empty fallback in `_load_calendar`.
_CALENDAR_COLUMNS = (
    "ts_utc",
    "date_local",
    "hour_local",
    "dow_local",
    "is_weekend",
    "is_holiday_at",
    "is_peak_hour",
    "year_local",
    "month_local",
)


def _load_calendar(settings: Settings) -> pd.DataFrame:
    """Build the ING-110 calendar spine for the ING-111 gate.

    `build_calendar`'s dynamic default `end` calls
    `entsoe.latest_complete_month`, which raises `NoDataError` when no
    complete ENTSO-E price month has been backfilled yet. That is a genuine
    "nothing to check" state, not a crash: this degrades to a typed-empty
    frame so `gate_ing_111` reports a real (non-vacuous) failure instead of
    an uncaught exception propagating out of `run_gates` (EN-061 -- `run_gates`
    only ever raises `GateFailure`).

    Implements: ING-111 (gate input), EN-061.
    """
    try:
        return build_calendar(settings)
    except NoDataError:
        return pd.DataFrame({col: pd.Series([], dtype="object") for col in _CALENDAR_COLUMNS})


def _geosphere_window(settings: Settings) -> tuple[date, date] | None:
    """ING-093 window the GeoSphere series must cover: ``window.start_date`` -> latest month.

    "Latest" is the ING-042 latest complete price month, so the weather series
    is held to the same horizon as the price data it will be joined with.
    Without any complete ENTSO-E month (`NoDataError`) there is no horizon to
    assert against; `gate_ing_094` then falls back to the data's own span (the
    ENTSO-E gates fail loudly on that state anyway).

    Implements: ING-093, ING-042.
    """
    try:
        latest = latest_complete_month(settings)
    except NoDataError:
        return None
    return settings.window.start_date, next_month(latest) - timedelta(days=1)


def _oespi_gate_result(settings: Settings) -> GateResult:
    """Load the reconciled ÖSPI CSV and run `gate_ing_103`; degrade gracefully.

    Deferred (function-local) import of `epra.ingest.oespi`: `oespi.py`
    imports `gate_ing_103` from this module at its own top level, so a
    top-level import here would be a circular import (this module would need
    `oespi` fully loaded before its own `gate_ing_103` definition exists,
    which `oespi` itself depends on).

    A missing real `data/manual/oespi_monthly.csv` (the ING-101 double-entry
    reconciled file, 03-06's human checkpoint) is expected pre-checkpoint
    state, not a failure: D-06 explicitly excludes it from being a CI/local
    blocker, so this renders a non-fatal informational `GateResult` instead
    of calling `gate_ing_103` (which would otherwise vacuously fail on the
    empty-input path, A-2 -- that A-2 rule governs `gate_ing_103` itself when
    given real-but-empty data, not this "not transcribed yet" carve-out).

    Implements: ING-103.
    """
    from epra.ingest.oespi import load_oespi

    path = resolve_repo_path(settings.paths.data_manual) / "oespi_monthly.csv"
    try:
        oespi_frame = load_oespi(settings)
    except FileNotFoundError:
        return GateResult(
            "ING-103",
            True,
            f"real ÖSPI data not yet transcribed ({path} absent) -- ING-101 double-entry "
            "human checkpoint pending (D-06), not a gate failure",
            None,
        )
    return gate_ing_103(oespi_frame)


def _write_report(report: ValidationReport, settings: Settings) -> Path:
    """Write ``reports/ingestion/validation_<Vienna run-date>.md`` (SPEC-01 §8)."""
    run_date = today_local()
    ingestion_dir = resolve_repo_path(settings.paths.reports) / "ingestion"
    ingestion_dir.mkdir(parents=True, exist_ok=True)
    report_path = ingestion_dir / f"validation_{run_date:%Y-%m-%d}.md"
    report_path.write_text(report.render_markdown(run_date=run_date), encoding="utf-8")
    return report_path


def run_gates(settings: Settings) -> None:
    """Run all M1+M2 gates (ING-080..085, 094, 103, 111); write report; raise on failure (EN-061).

    Loads every monthly raw parquet for the three hourly ENTSO-E datasets and
    the GeoSphere daily dataset under ``settings.paths.data_raw``, the
    reconciled ÖSPI CSV under ``settings.paths.data_manual``, and the ING-110
    calendar spine, runs every M1+M2 gate exactly once, writes
    ``reports/ingestion/validation_<date>.md`` listing every registered gate
    exactly once (T-02-13), then raises ``GateFailure`` if any gate failed
    (A-2 -- never warn-and-continue). ``run_gates`` never raises anything
    other than ``GateFailure``: a missing/incomplete M2 input degrades to a
    genuine (non-crashing) gate result -- see ``_load_geosphere``,
    ``_load_calendar``, ``_oespi_gate_result``.

    Implements: ING-080, ING-081, ING-082, ING-083, ING-084, ING-085, ING-094,
    ING-103, ING-111 (aggregate run), EN-061 (fail-fast).
    """
    hourly = {
        dataset: _load_hourly(dataset, value_col, settings)
        for dataset, value_col in _HOURLY_DATASETS
    }
    at_prices = hourly["entsoe_prices_at"]
    at_load = hourly["entsoe_load_at"]
    geosphere_daily = _load_geosphere(settings)
    calendar_frame = _load_calendar(settings)

    report = ValidationReport()
    report.add(gate_ing_080(hourly))
    report.add(gate_ing_081(at_prices))
    report.add(gate_ing_082(at_prices))
    report.add(gate_ing_083(at_prices))
    report.add(gate_ing_084(at_load))
    report.add(gate_ing_085(at_prices, at_load))
    report.add(gate_ing_094(geosphere_daily, window=_geosphere_window(settings)))
    report.add(_oespi_gate_result(settings))
    report.add(gate_ing_111(calendar_frame))

    for result in report.results:
        logger.info("gate=%s passed=%s summary=%s", result.check_id, result.passed, result.summary)

    report_path = _write_report(report, settings)
    logger.info("validation report written to %s", report_path)

    report.raise_if_failed()


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.validate`` -- run all M1+M2 gates, write the report.

    Returns 0 if every gate passed, 1 if any gate failed (``GateFailure``).
    The logfile lands under the REPO_ROOT-anchored ``reports/ingestion/``
    regardless of the caller's cwd.

    Implements: ING-002 (CLI entrypoint), EN-060 (logfile), EN-061 (non-zero exit on
    gate failure).
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.ingest.validate",
        description="Run all M1+M2 ingestion validation gates (ING-080..085, 094, 103, 111) "
        "and write the report.",
    )
    parser.parse_args(argv)

    settings = load_settings()
    logfile = (
        resolve_repo_path(settings.paths.reports)
        / "ingestion"
        / f"validate_{today_local():%Y-%m-%d}.log"
    )
    common_logging.setup(logfile=logfile)

    try:
        run_gates(settings)
    except GateFailure as exc:
        logger.error("validation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
