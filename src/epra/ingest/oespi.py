"""ÖSPI loader — hand-curated monthly index CSV (M2).

Binding contract: SPEC-01 §10. Key points:

- There is NO machine API. The human transcribes the Austrian Energy Agency's
  published monthly values (Base + Peak, index base 2006 = 100) into
  ``data/manual/oespi_monthly.csv`` — TWICE (double-entry, ING-101), reconciled
  by ``scripts/oespi_reconcile.py`` (already implemented).
- Schema (ING-100): ``month,oespi_base,oespi_peak,source_url,retrieved_at``
  with ``month`` = YYYY-MM. Values are transcribed real data — never invented
  (A-2, P-1).
- Methodology break warning (ING-102): use ONE consistent series
  (ADR-008); ``load_oespi`` asserts ``source_url`` is constant across the
  whole series and raises rather than silently splicing two methods/pages.
- Gates (ING-103, in ``epra.ingest.validate.gate_ing_103``): continuous
  months, positive values, 2022 peak >= 3x the 2019 mean, month-over-month
  change within +/-60%.
- Peak unavailability triggers ING-104 base-only fallback: ``load_oespi``
  signals this via ``frame.attrs["peak_available"]`` rather than raising.

Implements: ING-100, ING-102, ING-103 (CLI wiring), ING-104 (ING-101 lives in
scripts/oespi_reconcile.py).
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from epra.common import logging as common_logging
from epra.common.config import Settings, load_settings, resolve_repo_path
from epra.common.timeutil import today_local
from epra.ingest.exceptions import ContractError
from epra.ingest.validate import gate_ing_103

logger = logging.getLogger(__name__)

#: ING-100 schema, in order. Mirrors `scripts/oespi_reconcile.EXPECTED_COLUMNS`
#: (that script's own source of truth) — duplicated rather than imported
#: because `scripts/` is a standalone operator tool, not part of the
#: installed `epra` package (`pyproject.toml` `packages = ["src/epra"]`).
_EXPECTED_COLUMNS = ("month", "oespi_base", "oespi_peak", "source_url", "retrieved_at")


def _coerce_numeric(values: pd.Series, months: pd.Series, column: str) -> pd.Series:
    """Coerce `values` to float64, raising on ANY non-numeric/blank entry (P-3).

    Never silently fills a malformed value with NaN — `pandas.to_numeric`'s
    `errors="coerce"` is used only to *detect* which rows are bad, and every
    bad row is named in the raised `ContractError` (never swallowed).
    """
    numeric = pd.to_numeric(values, errors="coerce")
    bad = numeric.isna()
    if bad.any():
        bad_months = sorted(months.loc[bad])
        raise ContractError(
            "oespi_monthly",
            expected=f"{column} numeric for every month",
            actual=f"non-numeric/blank {column} for month(s): {bad_months}",
        )
    return numeric.astype("float64")


def _read_raw_csv(path: Path) -> pd.DataFrame:
    """Read the ÖSPI CSV verbatim and enforce the ING-100 schema + non-empty invariant.

    ``dtype=str`` + ``keep_default_na=False``: every cell stays the literal
    string from the file (blank -> "", never pandas' own NA sniffing) so numeric
    coercion is the ONLY place a bad value can be detected/raised.

    Implements: ING-100.
    """
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    if tuple(raw.columns) != _EXPECTED_COLUMNS:
        raise ContractError(
            "oespi_monthly",
            expected=f"columns {list(_EXPECTED_COLUMNS)} (ING-100)",
            actual=f"{list(raw.columns)}",
        )
    if raw.empty:
        raise ContractError("oespi_monthly", expected="at least one data row", actual="0 rows")
    return raw


def _assert_single_source(raw: pd.DataFrame) -> None:
    """ING-102 / ADR-008 single-series invariant: one constant ``source_url`` -- never splice.

    Implements: ING-102.
    """
    urls = raw["source_url"]
    if urls.nunique() != 1:
        splice_months = sorted(raw.loc[urls != urls.iloc[0], "month"])
        raise ContractError(
            "oespi_monthly",
            expected="a single constant source_url across the whole series (ING-102, ADR-008)",
            actual=f"{urls.nunique()} distinct source_url value(s); differing month(s)="
            f"{splice_months}",
        )


def _parse_months(raw: pd.DataFrame) -> pd.PeriodIndex:
    """Parse the ``month`` column (YYYY-MM) into a monthly `PeriodIndex` (ING-100).

    Implements: ING-100.
    """
    try:
        return pd.PeriodIndex(raw["month"], freq="M")
    except ValueError as exc:
        raise ContractError(
            "oespi_monthly",
            expected="month formatted YYYY-MM",
            actual=f"{raw['month'].tolist()}",
        ) from exc


def _parse_peak(raw: pd.DataFrame) -> tuple[pd.Series, bool]:
    """Return ``(oespi_peak float series, peak_available)`` under the ING-104 all-or-nothing rule.

    All blank -> base-only fallback (all-NaN, ``False``); all present ->
    numeric (``True``); a mix is malformed and raises (P-3).

    Implements: ING-104.
    """
    peak_blank = raw["oespi_peak"].str.strip() == ""
    if peak_blank.all():
        return pd.Series([float("nan")] * len(raw), dtype="float64"), False
    if peak_blank.any():
        blank_months = sorted(raw.loc[peak_blank, "month"])
        raise ContractError(
            "oespi_monthly",
            expected="oespi_peak present for every month, or blank for every month (ING-104)",
            actual=f"blank for {len(blank_months)} month(s) but present elsewhere: {blank_months}",
        )
    return _coerce_numeric(raw["oespi_peak"], raw["month"], "oespi_peak"), True


def load_oespi(settings: Settings, *, csv_path: Path | None = None) -> pd.DataFrame:
    """Load + validate the ÖSPI monthly CSV (ING-100/102/104).

    Implements: ING-100, ING-102, ING-104.

    Args:
        settings: injected config; never re-read YAML here (EN-040).
        csv_path: override for the CSV path — the default is the
            REPO_ROOT-anchored ``settings.paths.data_manual /
            "oespi_monthly.csv"`` (the reconciled double-entry file, ING-101).
            Tests inject the committed synthetic fixture instead.

    Returns:
        A frame indexed by a monthly `PeriodIndex` named ``month``, with
        columns ``oespi_base``, ``oespi_peak`` (float64; all-NaN under the
        ING-104 base-only fallback), ``source_url``, ``retrieved_at``.
        ``frame.attrs["peak_available"]`` is `True` when every month has a
        Peak value, `False` when Peak is absent for the whole series
        (ING-104) — never a mix of the two (a partial gap is malformed, P-3).

    Raises:
        ContractError: the CSV's columns don't exactly match the ING-100
            schema; the CSV has no data rows; ``source_url`` is not constant
            across the series (ING-102 — never splice methodologies);
            ``month`` is not parseable as YYYY-MM; ``oespi_base`` (or
            ``oespi_peak``, when present) has a non-numeric/blank value; or
            ``oespi_peak`` is blank for some but not all months.
    """
    path = (
        csv_path
        if csv_path is not None
        else resolve_repo_path(settings.paths.data_manual) / "oespi_monthly.csv"
    )
    raw = _read_raw_csv(path)
    _assert_single_source(raw)
    month_index = _parse_months(raw)
    base = _coerce_numeric(raw["oespi_base"], raw["month"], "oespi_base")
    peak, peak_available = _parse_peak(raw)

    frame = pd.DataFrame(
        {
            "oespi_base": base.to_numpy(),
            "oespi_peak": peak.to_numpy(),
            "source_url": raw["source_url"].to_numpy(),
            "retrieved_at": raw["retrieved_at"].to_numpy(),
        },
        index=month_index,
    )
    frame.attrs["peak_available"] = peak_available
    logger.info(
        "source=oespi_monthly status=loaded rows=%d peak_available=%s",
        len(frame),
        peak_available,
    )
    return frame


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.oespi`` — load + validate the committed CSV (ING-103).

    Loads ``settings.paths.data_manual / "oespi_monthly.csv"`` (the reconciled
    double-entry file, ING-101), then runs `gate_ing_103` and logs the
    rendered result (stdout + the REPO_ROOT-anchored logfile, EN-060). Returns
    0 if the CSV loads and the gate passes, 1 on a load error
    (`ContractError`/`FileNotFoundError` — e.g. the real reconciled CSV isn't
    committed yet) or a failed gate.

    Implements: ING-002 (CLI entrypoint), ING-103 (gate wiring), EN-060 (logging).
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.ingest.oespi",
        description="Load + validate the committed ÖSPI monthly CSV (ING-100/102/103/104).",
    )
    parser.parse_args(argv)

    settings = load_settings()
    logfile = (
        resolve_repo_path(settings.paths.reports)
        / "ingestion"
        / f"oespi_{today_local():%Y-%m-%d}.log"
    )
    common_logging.setup(logfile=logfile)

    try:
        frame = load_oespi(settings)
    except (ContractError, FileNotFoundError) as exc:
        logger.error("ÖSPI load failed: %s", exc)
        return 1

    result = gate_ing_103(frame)
    log = logger.info if result.passed else logger.error
    log("gate=%s passed=%s summary=%s", result.gate_id, result.passed, result.summary)
    log("ING-103 result:\n%s", result.render_markdown())

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
