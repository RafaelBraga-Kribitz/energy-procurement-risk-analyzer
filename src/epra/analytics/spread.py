"""A2 — AT vs DE-LU spread (M5).

Not yet implemented. Binding contract: SPEC-04 A2 (AN-201..203). Artifacts:
``a2_spread_monthly.png``, ``a2_spread_summary.md``; SSOT rows
``spread_mean_<year>`` (VERIFIED). Interpretation paragraph = the
"you are not in Germany" localization point (AN-203).

Implements (when built): AN-201..203.
"""

from __future__ import annotations

from epra.common.config import Settings

_MSG = "M5 not implemented yet — build per SPEC-04 A2 (see module docstring)"


def run(settings: Settings) -> None:
    """Produce all A2 artifacts from marts; deterministic (AN-705)."""
    raise NotImplementedError(_MSG)
