"""Euro / unit formatting — the ONE shared formatter module (RP-703).

Conventions (SPEC-06 §7): thousands separator, "€1.42 M" style for millions,
EUR/MWh with 1 decimal, English number conventions everywhere in charts and
exports (RP-705 — German appears only in Power BI subtitles).

Implements: RP-703.
"""

from __future__ import annotations

MILLION = 1_000_000.0


def format_eur(value: float) -> str:
    """Whole euros with thousands separators: 1234567.8 → ``€1,234,568``."""
    return f"€{value:,.0f}"


def format_eur_millions(value: float, decimals: int = 2) -> str:
    """Millions of euros: 1_420_000 → ``€1.42 M``."""
    return f"€{value / MILLION:,.{decimals}f} M"


def format_eur_mwh(value: float) -> str:
    """Unit price with 1 decimal: 123.456 → ``123.5 EUR/MWh``."""
    return f"{value:,.1f} EUR/MWh"


def format_pct(value: float, decimals: int = 1) -> str:
    """Fraction → percent string: 0.4231 → ``42.3%``."""
    return f"{value * 100:,.{decimals}f}%"
