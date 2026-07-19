"""A4 — Weather & load sensitivity (M5, deliberately small).

Not yet implemented. Binding contract: SPEC-04 A4 (AN-401..402). Scatter + OLS
(month fixed effects, HC1 robust SE) of daily AT system load vs HDD_18;
degree-days come from ``dim_calendar`` (SPEC-04 §5) and are never recomputed
here. The interpretation must state explicitly that the REFERENCE consumer's
profile is weather-invariant by construction (AN-402).

Implements (when built): AN-401..402.
"""

from __future__ import annotations

from epra.common.config import Settings

_MSG = "M5 not implemented yet — build per SPEC-04 A4 (see module docstring)"


def run(settings: Settings) -> None:
    """Produce a4_load_vs_hdd.png + a4_load_weather.md from marts."""
    raise NotImplementedError(_MSG)
