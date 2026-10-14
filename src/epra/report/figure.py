"""Shared figure scaffolding so every PNG obeys the chart standards (SPEC-06 §7).

``new_figure`` gives the RP-701 size/dpi on the Agg backend; ``save_figure``
adds the message title, units-bearing subtitle, the source note bottom-left and
the epistemic tag bottom-right (RP-702), plus the fixture banner when the run
is synthetic (ADR-018).

Implements: RP-701, RP-702.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from epra.report.style import DPI, FIGSIZE, SOURCE_NOTE

_FIXTURE_STAMP = "FIXTURE RUN — synthetic prices, not results (ADR-018)"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "svg.hashsalt": "epra",
    }
)


def new_figure(nrows: int = 1, ncols: int = 1, **kwargs: Any) -> tuple[Figure, Any]:
    """RP-701 figure (12×6 in) with ``nrows × ncols`` axes.

    Implements: RP-701.
    """
    fig, axes = plt.subplots(nrows, ncols, figsize=FIGSIZE, **kwargs)
    return fig, axes


def save_figure(
    fig: Figure,
    path: Path,
    *,
    title: str,
    subtitle: str = "",
    tag: str | None = None,
    fixture: bool = False,
    colorbar_room: float = 0.0,
    source: str = SOURCE_NOTE,
) -> Path:
    """Title, footer notes, tight layout, deterministic PNG write.

    ``tag`` is the CALIBRATED/SIMULATED caption (RP-702); omit for VERIFIED-only
    charts. ``colorbar_room`` (figure fraction) switches from tight_layout to a
    fixed layout that leaves the right edge free for a shared colorbar axis.
    PNG metadata is stripped so reruns are byte-stable (AN-705).

    Implements: RP-701, RP-702.
    """
    # Plain figure texts, not suptitle: tight_layout reserves extra room for a
    # suptitle, which left a dead band under the title.
    fig.text(0.01, 0.975, title, ha="left", va="top", fontsize=14, fontweight="bold")
    top = 0.92
    if subtitle:
        fig.text(0.01, 0.925, subtitle, ha="left", va="top", fontsize=10, color="#444444")
        top = 0.89
    fig.text(0.01, 0.01, source, ha="left", va="bottom", fontsize=8, color="#555555")
    if tag:
        fig.text(0.99, 0.01, tag, ha="right", va="bottom", fontsize=8, color="#555555")
    if fixture:
        fig.text(
            0.5,
            0.5,
            _FIXTURE_STAMP,
            ha="center",
            va="center",
            fontsize=22,
            color="#CC0000",
            alpha=0.18,
            rotation=20,
        )
    if colorbar_room:
        fig.subplots_adjust(
            left=0.05, right=1.0 - colorbar_room, top=top - 0.04, bottom=0.13, wspace=0.12
        )
    else:
        fig.tight_layout(rect=(0.0, 0.04, 1.0, top))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, metadata={"Software": None})
    plt.close(fig)
    return path
