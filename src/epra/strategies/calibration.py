"""Calibration anchors — 2019 reference prices and ÖSPI base values (M6).

Not yet implemented. Binding contract: SPEC-05 §4 (ST-201..204). The four
anchors (CALIBRATED, written to SSOT and quoted in LIMITATIONS):

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

Implements (when built): ST-201..204.
"""

from __future__ import annotations

import pandas as pd

from epra.common.config import Settings, StrategyCfg

_MSG = "M6 not implemented yet — build per SPEC-05 §4 (see module docstring)"


def compute_anchors(settings: Settings, cfg: StrategyCfg) -> pd.DataFrame:
    """Return the four anchors as a one-row frame; persisted for SSOT (ST-204)."""
    raise NotImplementedError(_MSG)
