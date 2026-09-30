"""Euro / unit formatting — the ONE shared formatter module (RP-703).

Conventions (SPEC-06 §7): thousands separator, "€1.42 M" style for millions,
EUR/MWh with 1 decimal, English number conventions everywhere in charts and
exports (RP-705 — German appears only in Power BI subtitles).

Not yet imported by production code: M7's executive charts/exports
(SPEC-06 §7, RP-701..705) are the intended callers; tests pin the formats now.

Implements: RP-703, RP-705.
"""

from __future__ import annotations

MILLION = 1_000_000.0


def format_eur(value: float) -> str:
    """Whole euros with thousands separators: 1234567.8 → ``€1,234,568``.

    Implements: RP-703 (thousands separator), RP-705 (English conventions).
    """
    return f"€{value:,.0f}"


def format_eur_millions(value: float, decimals: int = 2) -> str:
    """Millions of euros: 1_420_000 → ``€1.42 M``.

    Implements: RP-703 ("€1.42 M" style for millions).
    """
    return f"€{value / MILLION:,.{decimals}f} M"


def format_eur_mwh(value: float) -> str:
    """Unit price with 1 decimal: 123.456 → ``123.5 EUR/MWh``.

    Implements: RP-703 (EUR/MWh with 1 decimal).
    """
    return f"{value:,.1f} EUR/MWh"


def format_pct(value: float, decimals: int = 1) -> str:
    """Fraction → percent string: 0.4231 → ``42.3%``.

    Implements: RP-703 (shared formatter), RP-705 (English dot-decimal conventions).
    """
    return f"{value * 100:,.{decimals}f}%"
