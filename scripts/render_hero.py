"""Render the README hero banner (docs/assets/hero.png) and its layout record.

The status label is derived from data provenance, never typed: a fixture run
(ADR-018) can only ever say "PIPELINE COMPLETE · REAL DATA PENDING".
Fonts: Inter if installed, else DejaVu (the original hero used licensed Söhne
files that are not in this repository).

Usage: ``uv run python scripts/render_hero.py``  (``make hero``)

Implements: SPEC-06 §6 (README front door), A-2 (no status overclaim).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

from epra.common.config import REPO_ROOT, load_settings
from epra.common.provenance import is_fixture_run

OUT = REPO_ROOT / "docs" / "assets" / "hero.png"
LAYOUT = REPO_ROOT / "docs" / "assets" / "hero.layout.json"
WIDTH, HEIGHT = 1600, 640
KIND = "BRAGA · ANALYTICAL PROJECT"
TITLE = ["Energy Procurement Risk", "Analyzer"]
DESCRIPTOR = [
    "What the wrong electricity procurement strategy costs a 50 GWh Styrian",
    "manufacturer — backtested on Austrian day-ahead prices, P95 risk ahead.",
]
FACTS = "SQL · PYTHON · DBT · DUCKDB · POWER BI · AZURE-READY  ·  LICENSE MIT  ·  CI GITHUB ACTIONS"


def _family(preferred: str, fallback: str) -> str:
    names = {f.name for f in font_manager.fontManager.ttflist}
    return preferred if preferred in names else fallback


def status_label() -> str:
    """Provenance-driven status (no overclaim)."""
    if is_fixture_run(load_settings()):
        return "PIPELINE COMPLETE · REAL DATA PENDING"
    return "COMPLETE · REAL DATA"


def render(status: str) -> None:
    """Draw the 1600×640 light banner."""
    sans = _family("Inter", "DejaVu Sans")
    mono = _family("DejaVu Sans Mono", "monospace")
    fig = plt.figure(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100)
    fig.patch.set_facecolor("#E6E6E6")
    ink, muted = "#262626", "#4A4A4A"
    fig.text(72 / WIDTH, 1 - 88 / HEIGHT, KIND, family=mono, size=17, color=muted, va="center")
    label = fig.text(
        1 - 72 / WIDTH,
        1 - 88 / HEIGHT,
        status,
        family=mono,
        size=17,
        color=muted,
        va="center",
        ha="right",
    )
    left_px = label.get_window_extent().x0
    fig.text(
        (left_px - 14) / WIDTH,
        1 - 88 / HEIGHT,
        "●",
        size=14,
        color="#E8590C",
        va="center",
        ha="right",
    )
    for i, line in enumerate(TITLE):
        fig.text(
            72 / WIDTH,
            1 - (205 + i * 112) / HEIGHT,
            line,
            family=sans,
            weight="heavy",
            size=76,
            color=ink,
            va="center",
        )
    for i, line in enumerate(DESCRIPTOR):
        fig.text(
            72 / WIDTH,
            1 - (418 + i * 44) / HEIGHT,
            line,
            family=sans,
            size=23,
            color=ink,
            va="center",
        )
    fig.add_artist(
        Line2D([72 / WIDTH, 1 - 72 / WIDTH], [1 - 520 / HEIGHT] * 2, color="#9A9A9A", lw=1)
    )
    fig.text(72 / WIDTH, 1 - 557 / HEIGHT, FACTS, family=mono, size=15, color=muted, va="center")
    fig.savefig(OUT, dpi=100, facecolor=fig.get_facecolor(), metadata={"Software": None})
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> int:
    """Render hero.png and rewrite hero.layout.json to match."""
    del argv
    status = status_label()
    render(status)
    layout = {
        "output": "docs/assets/hero.png",
        "width": WIDTH,
        "height": HEIGHT,
        "mode": "light",
        "fonts": f"{_family('Inter', 'DejaVu Sans')} / DejaVu Sans Mono (scripts/render_hero.py)",
        "blocks": {
            "kind": {"lines": [KIND]},
            "status": {"lines": [status]},
            "title": {"lines": TITLE},
            "descriptor": {"lines": DESCRIPTOR},
            "facts": {"lines": [FACTS]},
        },
    }
    LAYOUT.write_text(json.dumps(layout, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: {OUT} ({status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
