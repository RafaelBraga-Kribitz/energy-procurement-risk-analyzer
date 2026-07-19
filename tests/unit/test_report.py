"""Formatter (RP-703) and style (RP-704) tests."""

import pytest

from epra.report import format as fmt
from epra.report import style


def test_eur_formatting() -> None:
    assert fmt.format_eur(1234567.8) == "€1,234,568"
    assert fmt.format_eur_millions(1_420_000) == "€1.42 M"
    assert fmt.format_eur_millions(12_300_000, decimals=1) == "€12.3 M"
    assert fmt.format_eur_mwh(123.456) == "123.5 EUR/MWh"
    assert fmt.format_pct(0.4231) == "42.3%"


def test_strategy_colors_cover_dim_strategy_and_are_distinct() -> None:
    # Must match dim_strategy seed ids (SPEC-02 §4); colors stable repo-wide (RP-704).
    assert set(style.STRATEGY_COLORS) == {"S1", "S2", "S3", "S4_30", "S4_50", "S4_70"}
    assert len(set(style.STRATEGY_COLORS.values())) == 6


def test_hybrid_colors_interpolate_between_s1_and_s3() -> None:
    assert style.hybrid_color(0.0) == style.STRATEGY_COLORS["S1"]
    assert style.hybrid_color(1.0) == style.STRATEGY_COLORS["S3"]
    mid = style.hybrid_color(0.5)
    assert mid not in (style.STRATEGY_COLORS["S1"], style.STRATEGY_COLORS["S3"])
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        style.hybrid_color(1.5)


def test_figure_standards() -> None:
    assert style.FIGSIZE == (12.0, 6.0)  # RP-701
    assert style.DPI == 150  # RP-701
    assert "ENTSO-E" in style.SOURCE_NOTE  # RP-702
