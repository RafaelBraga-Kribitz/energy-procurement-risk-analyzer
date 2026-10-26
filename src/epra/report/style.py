"""Chart style constants — colours defined ONCE, stable across every chart (RP-704).

Colours come from the Braga design system v2.1 through ``bk-viz`` roles (D-053);
no hex value lives in this repository. Strategy → colour mapping is fixed for the
whole repo: S3 (fixed) categorical slot 1, S1 (spot) slot 2, S2 (ÖSPI-indexed)
slot 3, hybrids interpolated between the S1 and S3 endpoints by their hedge ratio.

Figure standards (RP-701): matplotlib Agg backend, 12×6 in, dpi 150, no seaborn
for executive charts. Every chart carries the source note (bottom-left) and,
when CALIBRATED/SIMULATED data is shown, the epistemic tag bottom-right (RP-702).

Implements: RP-701 (constants), RP-704 as amended by ADR-021; supports RP-702.
"""

from __future__ import annotations

import bk_theme as bk

bk.apply("light")

FIGSIZE = (12.0, 6.0)  # inches (RP-701)
DPI = 150  # (RP-701)
SOURCE_NOTE = "Source: ENTSO-E Transparency / AEA ÖSPI / own calculations"  # RP-702

#: Endpoints of the spot ↔ fixed continuum, as design-system roles.
S1_ROLE = "cat-2"  # FULL_SPOT
S3_ROLE = "cat-1"  # FIXED_ANNUAL
S2_ROLE = "cat-3"  # OESPI_INDEXED


def _interpolate_hex(color_a: str, color_b: str, t: float) -> str:
    """Linear RGB interpolation between two hex colors, t ∈ [0, 1]."""
    if not 0.0 <= t <= 1.0:
        raise ValueError(f"interpolation factor must be in [0, 1], got {t}")
    a = [int(color_a[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(x + (y - x) * t) for x, y in zip(a, b, strict=True)]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def hybrid_color(hedge_ratio: float) -> str:
    """Color for HYBRID_h: interpolate S1 (spot, ratio 0) → S3 (fixed, ratio 1).

    Implements: RP-704 (hybrids interpolated between the S1 and S3 colors).
    """
    return _interpolate_hex(bk.c(S1_ROLE), bk.c(S3_ROLE), hedge_ratio)


#: strategy_id → hex color, identical across ALL charts (RP-704).
STRATEGY_COLORS: dict[str, str] = {
    "S1": bk.c(S1_ROLE),  # FULL_SPOT — ochre
    "S2": bk.c(S2_ROLE),  # OESPI_INDEXED — teal
    "S3": bk.c(S3_ROLE),  # FIXED_ANNUAL — ultramarine
    "S4_30": hybrid_color(0.30),
    "S4_50": hybrid_color(0.50),
    "S4_70": hybrid_color(0.70),
}

#: HMM volatility regimes (A3) as opaque background bands: the diverging scale's
#: good tint, its neutral midpoint and its bad tint (calm → crisis).
REGIME_COLORS: dict[str, str] = {
    "calm": bk.c("var-pos-tint"),
    "elevated": bk.c("surface-3"),
    "crisis": bk.c("var-neg-tint"),
}

#: strategy_id → reader-facing label, identical across charts and tables.
STRATEGY_LABELS: dict[str, str] = {
    "S1": "Full spot",
    "S2": "ÖSPI-indexed",
    "S3": "Fixed annual",
    "S4_30": "Hybrid 30% fixed",
    "S4_50": "Hybrid 50% fixed",
    "S4_70": "Hybrid 70% fixed",
}

#: Caption sentences required on strategy outputs (ST-502, LP-050).
ST502_CAPTION = (
    "Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated "
    "assumptions — see LIMITATIONS."
)
LP050_CAPTION = (
    "Reference load profile is constructed (CALIBRATED), not measured; construction "
    "rules in SPEC-03."
)
CALIBRATED_TAG = "CALIBRATED · constructed load profile (SPEC-03) · contract prices via ÖSPI proxy"
SIMULATED_TAG = "SIMULATED · seeded block bootstrap of 2019→latest months · CALIBRATED inputs"
