"""ÖSPI loader — hand-curated monthly index CSV (M2).

Binding contract: SPEC-01 §10. Key points:

- There is NO machine API. The human transcribes the Austrian Energy Agency's
  published monthly values (Base + Peak, index base 2006 = 100) into
  ``data/manual/oespi_monthly.csv`` — TWICE (double-entry, ING-101), reconciled
  by ``scripts/oespi_reconcile.py`` (already implemented).
- Schema (ING-100): ``month,oespi_base,oespi_peak,source_url,retrieved_at``
  with ``month`` = YYYY-MM. Values are transcribed real data — never invented
  (A-2, P-1).
- Methodology break warning (ING-102): use ONE consistent series (D-01,
  ADR-008); ``load_oespi`` asserts ``source_url`` is constant across the whole
  series and raises rather than silently splicing two methods/pages.
- Gates (ING-103, in ``epra.ingest.validate.gate_ing_103``): continuous
  months, positive values, 2022 peak >= 3x the 2019 mean, month-over-month
  change within +/-60%.
- Peak unavailability triggers ING-104 base-only fallback: ``load_oespi``
  signals this via ``frame.attrs["peak_available"]`` rather than raising.

Implements: ING-100, ING-102, ING-103 (CLI wiring), ING-104 (ING-101 lives in
scripts/oespi_reconcile.py).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from epra.common.config import Settings
from epra.ingest.exceptions import ContractError

logger = logging.getLogger(__name__)

_MSG = "M2 not implemented yet — build per SPEC-01 §10 (see module docstring)"

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


def load_oespi(settings: Settings, *, csv_path: Path | None = None) -> pd.DataFrame:
    """Load + validate the ÖSPI monthly CSV (ING-100/102/104).

    Args:
        settings: injected config; never re-read YAML here (EN-040).
        csv_path: override for the CSV path — the default is
            ``settings.paths.data_manual / "oespi_monthly.csv"`` (the
            reconciled double-entry file, ING-101). Tests inject the
            committed synthetic fixture instead (D-05/D-06 — the real
            reconciled file is the 03-06 human checkpoint, never required
            for this loader or its gates to ship).

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
            across the series (D-01, ING-102 — never splice methodologies);
            ``month`` is not parseable as YYYY-MM; ``oespi_base`` (or
            ``oespi_peak``, when present) has a non-numeric/blank value; or
            ``oespi_peak`` is blank for some but not all months.
    """
    path = csv_path if csv_path is not None else settings.paths.data_manual / "oespi_monthly.csv"
    # dtype=str + keep_default_na=False: every cell stays the literal string
    # from the file (blank -> "", never pandas' own NA sniffing) so numeric
    # coercion below is the ONLY place a bad value can be detected/raised.
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)

    if tuple(raw.columns) != _EXPECTED_COLUMNS:
        raise ContractError(
            "oespi_monthly",
            expected=f"columns {list(_EXPECTED_COLUMNS)} (ING-100)",
            actual=f"{list(raw.columns)}",
        )
    if raw.empty:
        raise ContractError("oespi_monthly", expected="at least one data row", actual="0 rows")

    # Single-series invariant (D-01, ING-102) -- never splice methodologies.
    urls = raw["source_url"]
    if urls.nunique() != 1:
        splice_months = sorted(raw.loc[urls != urls.iloc[0], "month"])
        raise ContractError(
            "oespi_monthly",
            expected="a single constant source_url across the whole series (D-01, ING-102)",
            actual=f"{urls.nunique()} distinct source_url value(s); differing month(s)="
            f"{splice_months}",
        )

    try:
        month_index = pd.PeriodIndex(raw["month"], freq="M")
    except ValueError as exc:
        raise ContractError(
            "oespi_monthly",
            expected="month formatted YYYY-MM",
            actual=f"{raw['month'].tolist()}",
        ) from exc

    base = _coerce_numeric(raw["oespi_base"], raw["month"], "oespi_base")

    peak_blank = raw["oespi_peak"].str.strip() == ""
    if peak_blank.all():
        peak_available = False
        peak = pd.Series([float("nan")] * len(raw), dtype="float64")
    elif peak_blank.any():
        blank_months = sorted(raw.loc[peak_blank, "month"])
        raise ContractError(
            "oespi_monthly",
            expected="oespi_peak present for every month, or blank for every month (ING-104)",
            actual=f"blank for {len(blank_months)} month(s) but present elsewhere: {blank_months}",
        )
    else:
        peak_available = True
        peak = _coerce_numeric(raw["oespi_peak"], raw["month"], "oespi_peak")

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
    """CLI: ``python -m epra.ingest.oespi`` — validate the committed CSV (ING-103).

    Not yet implemented — wired in 03-05 Task 3 (loads settings, calls
    `load_oespi`, runs `epra.ingest.validate.gate_ing_103`).
    """
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
