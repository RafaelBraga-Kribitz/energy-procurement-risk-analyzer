"""A1 — Descriptive market structure (M5).

Not yet implemented. Binding contract: SPEC-04 A1 (AN-101..105). Artifacts:
``a1_annual_summary.md`` (+CSV), ``a1_heatmap_hour_month.png``,
``a1_duration_curves.png``, ``a1_negative_hours.png``; SSOT rows
``annual_mean_price_<year>``, ``neg_hours_<year>`` (VERIFIED). The summary md
must end with the "So what for a procurement manager" prose paragraph
(AN-105; length gated by AN-704).

Implements (when built): AN-101..105.
"""

from __future__ import annotations

from epra.common.config import Settings

_MSG = "M5 not implemented yet — build per SPEC-04 A1 (see module docstring)"


def run(settings: Settings) -> None:
    """Produce all A1 artifacts from marts; deterministic (AN-705)."""
    raise NotImplementedError(_MSG)
