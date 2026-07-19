"""Chart style constants — colors defined ONCE, stable across every chart (RP-704).

Palette: Okabe-Ito (colorblind-safe). Strategy → color mapping is fixed for the
whole repo: S1 red family (vermillion), S3 blue family, S2 orange, hybrids
interpolated between the S1 and S3 endpoints by their hedge ratio.

Figure standards (RP-701): matplotlib Agg backend, 12×6 in, dpi 150, no seaborn
for executive charts. Every chart carries the source note (bottom-left) and,
when CALIBRATED/SIMULATED data is shown, the epistemic tag bottom-right (RP-702).

Implements: RP-701 (constants), RP-704; supports RP-702.
"""

from __future__ import annotations

# Okabe-Ito reference palette
OKABE_ITO = {
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
    "black": "#000000",
}

FIGSIZE = (12.0, 6.0)  # inches (RP-701)
DPI = 150  # (RP-701)
SOURCE_NOTE = "Source: ENTSO-E Transparency / AEA ÖSPI / own calculations"  # RP-702


def _interpolate_hex(color_a: str, color_b: str, t: float) -> str:
    """Linear RGB interpolation between two hex colors, t ∈ [0, 1]."""
    if not 0.0 <= t <= 1.0:
        raise ValueError(f"interpolation factor must be in [0, 1], got {t}")
    a = [int(color_a[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(x + (y - x) * t) for x, y in zip(a, b, strict=True)]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def hybrid_color(hedge_ratio: float) -> str:
    """Color for HYBRID_h: interpolate S1 (spot, ratio 0) → S3 (fixed, ratio 1)."""
    return _interpolate_hex(OKABE_ITO["vermillion"], OKABE_ITO["blue"], hedge_ratio)


#: strategy_id → hex color, identical across ALL charts (RP-704).
STRATEGY_COLORS: dict[str, str] = {
    "S1": OKABE_ITO["vermillion"],  # FULL_SPOT — red family
    "S2": OKABE_ITO["orange"],  # OESPI_INDEXED
    "S3": OKABE_ITO["blue"],  # FIXED_ANNUAL — blue family
    "S4_30": hybrid_color(0.30),
    "S4_50": hybrid_color(0.50),
    "S4_70": hybrid_color(0.70),
}
