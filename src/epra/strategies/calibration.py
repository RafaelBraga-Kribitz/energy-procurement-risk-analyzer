"""Calibration anchors translating ÖSPI index points into EUR/MWh (SPEC-05 §4).

The ÖSPI is an index (base 2006 = 100), not a price (trap T-5). Contract
prices are therefore anchored on the reference year:

- ST-201 ``p_ref_base`` = the reference consumer's volume-weighted average spot
  cost per MWh in the reference year: ``cost_S1(ref) / volume(ref)``.
- ST-202 ``p_ref_peak`` = mean AT hourly price over the peak hours of the
  reference year × (``p_ref_base`` ÷ mean AT hourly price over all hours of the
  reference year) — i.e. the reference-year peak price rescaled by the
  consumer's realized-vs-base ratio, keeping the base/peak anchor pair
  internally consistent.
- ST-203 ``oespi_base_ref`` / ``oespi_peak_ref`` = arithmetic mean of the
  respective ÖSPI series over the reference year.

All four are CALIBRATED and published to the SSOT (ST-204).

Implements: ST-201, ST-202, ST-203, ST-204.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from epra.common.config import Settings, StrategyCfg
from epra.strategies.inputs import (
    MAIN_PROFILE,
    ReferenceStats,
    oespi_monthly,
    reference_stats,
)


@dataclass(frozen=True)
class Anchors:
    """ST-201..203 anchor set (EUR/MWh and ÖSPI index points)."""

    p_ref_base: float
    p_ref_peak: float
    oespi_base_ref: float
    oespi_peak_ref: float


def anchors_from_inputs(ref: ReferenceStats, oespi: pd.DataFrame, reference_year: int) -> Anchors:
    """Pure ST-201..203 computation from reference-year aggregates and ÖSPI.

    ``p_ref_peak`` = mean AT hourly price over peak hours of the reference year
    × (``p_ref_base`` ÷ mean AT hourly price over all hours of that year).

    Implements: ST-201, ST-202, ST-203.
    """
    p_ref_base = ref.consumer_cost_eur / ref.consumer_volume_mwh
    p_ref_peak = ref.mean_price_peak_eur_mwh * (p_ref_base / ref.mean_price_all_hours_eur_mwh)
    year_rows = oespi[oespi["year_local"] == reference_year]
    if len(year_rows) != 12:
        raise ValueError(f"ÖSPI reference year {reference_year} has {len(year_rows)}/12 months")
    return Anchors(
        p_ref_base=p_ref_base,
        p_ref_peak=p_ref_peak,
        oespi_base_ref=float(year_rows["oespi_base"].mean()),
        oespi_peak_ref=float(year_rows["oespi_peak"].mean()),
    )


def compute_anchors(
    settings: Settings, cfg: StrategyCfg, profile_name: str = MAIN_PROFILE
) -> Anchors:
    """Anchors for ``profile_name`` read from the warehouse (ST-201..204).

    Implements: ST-201, ST-202, ST-203.
    """
    ref = reference_stats(settings, profile_name, cfg.reference_year)
    return anchors_from_inputs(ref, oespi_monthly(settings), cfg.reference_year)
