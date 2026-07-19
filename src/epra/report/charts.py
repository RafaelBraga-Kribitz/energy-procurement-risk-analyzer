"""Executive + module charts (M5/M7).

Not yet implemented. Binding contracts: SPEC-06 §2 (the four executive charts
RP-201..204), §3 (RP-301: every visible number reproducible from exports/
CSVs — a pytest recomputes chart #1's bars from strategy_annual_summary.csv),
§7 (style rules; use :mod:`epra.report.style` and :mod:`epra.report.format`).
Also renders the SPEC-05 ST-304 strategy charts and SPEC-04 analytics charts
share these helpers.

Implements (when built): RP-201..204, RP-301, ST-304 chart outputs.
"""

from __future__ import annotations

from epra.common.config import Settings

_MSG = "M7 not implemented yet — build per SPEC-06 §§2-3, §7 (see module docstring)"


def render_executive_charts(settings: Settings) -> None:
    """Write the four executive PNGs to reports/executive_charts/."""
    raise NotImplementedError(_MSG)
