"""Consumer load profile construction — "StyriaMetal GmbH" (M4).

Not yet implemented. Binding contract: SPEC-03 §2 (algorithm — implement the
five steps EXACTLY in order), §3 (parameters, YAML wins), §7 (golden +
property tests). Epistemic tag of all outputs: CALIBRATED.

Non-negotiables for the implementing agent:

- Zero randomness (LP-001); zero hardcoded numerics (LP-002) — everything from
  ``config/consumer_profile.yaml`` via ``load_consumer_profile()``.
- day_type precedence (Step 2): shutdown window > holiday→weekend > Sat/Sun →
  weekend > weekday. Maintenance days KEEP their day_type (factor applies on
  top); Christmas shutdown OVERRIDES day_type with no double dampening (§3.3).
- Per-LOCAL-year normalization to exactly annual_consumption_mwh ± 0.01
  (LP-004); partial years normalize against the full hypothetical-year shape
  sum (LP-034) — unit-tested with a 6-month fixture.
- Output ``data/processed/consumer_load_hourly.parquet``: ``ts_utc, load_mwh``
  covering the analysis window INCLUDING the forward-risk window (LP-003).
- Also export monthly volumes (LP-021) and write ``consumer_peak_share`` into
  the SSOT inputs (LP-020) — never retyped anywhere.
- Second profile ``flat_baseload`` (all weights 1.0) via the same function
  (LP-030); golden checksum test per LP-040/042.

Implements (when built): LP-001..004, LP-020..021, LP-030, LP-034, LP-040..042.
"""

from __future__ import annotations

import pandas as pd

from epra.common.config import ConsumerProfileCfg

_MSG = "M4 not implemented yet — build per SPEC-03 §2 (see module docstring)"


def build_profile(calendar_df: pd.DataFrame, cfg: ConsumerProfileCfg) -> pd.DataFrame:
    """SPEC-03 §2 entrypoint: hourly ``ts_utc, load_mwh`` frame, deterministic."""
    raise NotImplementedError(_MSG)


def monthly_volumes(profile_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to ``year_local, month_local, volume_mwh`` (LP-021)."""
    raise NotImplementedError(_MSG)
