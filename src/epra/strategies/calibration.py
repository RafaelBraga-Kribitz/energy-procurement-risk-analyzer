"""Calibration anchors — 2019 reference prices and ÖSPI base values (M6).

Binding contract: SPEC-05 §4 (ST-201..204). The four anchors (CALIBRATED):

- ``p_ref_base``  = cost_S1(2019) / volume(2019) — the consumer's
  volume-weighted average spot cost per MWh in 2019 (ST-201).
- ``p_ref_peak``  = mean AT hourly price over 2019 peak hours × (p_ref_base ÷
  mean AT hourly price over ALL 2019 hours) — the 2019 peak price rescaled by
  the consumer's realized-vs-base ratio, keeping the base/peak anchor pair
  internally consistent (ST-202; this sentence must stay in the docstring of
  the implementing function).
- ``oespi_base_ref`` / ``oespi_peak_ref`` = arithmetic mean of the respective
  ÖSPI series over calendar 2019 (ST-203).

Trap T-5: ÖSPI is an INDEX (2006=100), not EUR/MWh — every contract price runs
through these anchors. If S3 costs come out ~10× spot, the index was multiplied
by volume directly somewhere.

Implements: ST-201..204, T-5, D-06.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from epra.common.config import Settings, StrategyCfg
from epra.strategies.align import (
    AlignedVolumes,
    align_hourly,
    load_consumer_load,
    load_price_hourly,
    load_price_monthly,
)


class IncompleteReferenceYearError(ValueError):
    """Reference year coverage is incomplete — callers skip, CLI fail-closed.

    Implements: D-06.
    """


@dataclass(frozen=True)
class Anchors:
    """Four CALIBRATED translation anchors. All must be > 0.

    Implements: ST-201..204.
    """

    p_ref_base: float
    p_ref_peak: float
    oespi_base_ref: float
    oespi_peak_ref: float

    def validate(self) -> None:
        """Positive anchors; peak at least base (2019 peak power costs more)."""
        values = (self.p_ref_base, self.p_ref_peak, self.oespi_base_ref, self.oespi_peak_ref)
        if any(v <= 0 for v in values):
            raise ValueError(f"anchors must be > 0, got {self}")
        if self.p_ref_peak < self.p_ref_base:
            raise AssertionError(
                f"p_ref_peak ({self.p_ref_peak}) < p_ref_base ({self.p_ref_base}); "
                "STOP and investigate 2019 peak vs base (03_MODULES)"
            )


def _year_hours(hourly: pd.DataFrame, year: int) -> pd.DataFrame:
    slice_ = hourly.loc[hourly["year_local"] == year]
    if slice_.empty:
        raise IncompleteReferenceYearError(f"no aligned hourly rows for reference year {year}")
    return slice_


def p_ref_base(hourly: pd.DataFrame, year: int) -> float:
    """Volume-weighted spot cost per MWh in ``year`` (ST-201).

    Implements: ST-201.
    """
    rows = _year_hours(hourly, year)
    volume = float(rows["load_mwh"].sum())
    if volume <= 0:
        raise IncompleteReferenceYearError(f"zero aligned volume in {year}")
    cost = float((rows["load_mwh"] * rows["price_at_eur_mwh"]).sum())
    return cost / volume


def p_ref_peak(hourly: pd.DataFrame, year: int, *, p_ref_base_value: float) -> float:
    """2019 peak price rescaled by the consumer's realized-vs-base ratio.

    p_ref_peak = mean AT hourly price over peak hours of 2019 × (p_ref_base ÷
    mean AT hourly price over all hours of 2019) — i.e., the 2019 peak price
    rescaled by the consumer's realized-vs-base ratio, keeping the base/peak
    anchor pair internally consistent.

    Implements: ST-202.
    """
    rows = _year_hours(hourly, year)
    if "is_peak_hour" not in rows.columns:
        raise ValueError("aligned hourly is missing is_peak_hour (ST-202)")
    mean_all = float(rows["price_at_eur_mwh"].mean())
    if mean_all == 0:
        raise IncompleteReferenceYearError(f"mean AT hourly price in {year} is 0")
    peak = rows.loc[rows["is_peak_hour"].astype(bool), "price_at_eur_mwh"]
    if peak.empty:
        raise IncompleteReferenceYearError(f"no peak hours in aligned {year}")
    mean_peak = float(peak.mean())
    return mean_peak * (p_ref_base_value / mean_all)


def oespi_refs(monthly: pd.DataFrame, year: int) -> tuple[float, float]:
    """Arithmetic mean of ÖSPI base/peak over calendar ``year`` (ST-203).

    Implements: ST-203.
    """
    rows = monthly.loc[monthly["year_local"] == year]
    if rows.empty:
        raise IncompleteReferenceYearError(f"no ÖSPI rows for reference year {year}")
    for col in ("oespi_base", "oespi_peak"):
        if col not in rows.columns:
            raise ValueError(f"monthly ÖSPI frame missing {col}")
        if rows[col].isna().any():
            raise IncompleteReferenceYearError(f"NULL {col} in reference year {year}")
    return float(rows["oespi_base"].mean()), float(rows["oespi_peak"].mean())


def anchors_from_frames(
    hourly: pd.DataFrame, monthly_oespi: pd.DataFrame, *, reference_year: int
) -> Anchors:
    """Pure ST-201..203 from aligned hourly + monthly ÖSPI.

    Implements: ST-201..203.
    """
    base = p_ref_base(hourly, reference_year)
    peak = p_ref_peak(hourly, reference_year, p_ref_base_value=base)
    o_base, o_peak = oespi_refs(monthly_oespi, reference_year)
    out = Anchors(
        p_ref_base=base, p_ref_peak=peak, oespi_base_ref=o_base, oespi_peak_ref=o_peak
    )
    out.validate()
    return out


def anchors_to_frame(anchors: Anchors) -> pd.DataFrame:
    """One-row wide frame for persistence (ST-204).

    Implements: ST-204.
    """
    return pd.DataFrame(
        [
            {
                "p_ref_base": anchors.p_ref_base,
                "p_ref_peak": anchors.p_ref_peak,
                "oespi_base_ref": anchors.oespi_base_ref,
                "oespi_peak_ref": anchors.oespi_peak_ref,
            }
        ]
    )


def compute_anchors(
    settings: Settings,
    cfg: StrategyCfg,
    *,
    aligned: AlignedVolumes | None = None,
    monthly_oespi: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return the four anchors as a one-row frame; persisted for SSOT (ST-204).

    Inject ``aligned`` / ``monthly_oespi`` in tests. Incomplete reference-year
    coverage raises ``IncompleteReferenceYearError`` (D-06 skip-if-incomplete).

    Implements: ST-201..204, D-06.
    """
    if aligned is None:
        aligned = align_hourly(load_consumer_load(settings), load_price_hourly(settings))
    if monthly_oespi is None:
        monthly_oespi = load_price_monthly(settings)
    anchors = anchors_from_frames(
        aligned.hourly, monthly_oespi, reference_year=cfg.reference_year
    )
    return anchors_to_frame(anchors)
