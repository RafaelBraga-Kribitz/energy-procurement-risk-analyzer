"""Shared figure scaffolding so every PNG obeys the chart standards (SPEC-06 §7).

``new_figure`` gives the RP-701 size/dpi on the Agg backend; ``save_figure``
adds the message title, units-bearing subtitle, the source note bottom-left and
the epistemic tag bottom-right (RP-702), plus the fixture banner when the run
is synthetic (ADR-018). Type, colour and the provenance strip come from the
Braga design system v2.1 through ``bk-viz`` (D-053).

Implements: RP-701, RP-702.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import bk_theme as bk
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from epra.report.style import DPI, FIGSIZE, SOURCE_NOTE

_FIXTURE_STAMP = "▲ FIXTURE RUN — synthetic prices, not results (ADR-018)"
_MARGIN = 0.02  # left/right edge of title, subtitle and footer (figure fraction)

# bk.apply("light") (in epra.report.style) installs the design system; this only
# keeps SVG ids deterministic and sets subplot titles to body size.
plt.rcParams.update({"svg.hashsalt": "epra", "axes.titlesize": bk.SIZE["body"]})


def new_figure(nrows: int = 1, ncols: int = 1, **kwargs: Any) -> tuple[Figure, Any]:
    """RP-701 figure (12×6 in) with ``nrows × ncols`` axes.

    Implements: RP-701.
    """
    fig, axes = plt.subplots(nrows, ncols, figsize=FIGSIZE, **kwargs)
    return fig, axes


def panel_title(ax: Any, text: str) -> None:
    """Subplot heading: BKribitz 700 at body size, ink, left-aligned."""
    ax.set_title(
        text, loc="left", color=bk.c("ink"), fontproperties=bk.font("display", 700, "body")
    )


def _frac(points: float, fig: Figure) -> float:
    """Height in points as a fraction of the figure height."""
    return points / 72 / float(fig.get_size_inches()[1])


def _header(fig: Figure, title: str, subtitle: str, fixture: bool) -> float:
    """Fixture kicker, finding title and context line; returns the axes' top edge."""
    span_px = (1 - 2 * _MARGIN) * float(fig.get_size_inches()[0]) * bk.PX_PER_IN
    y = 0.975
    if fixture:
        fig.text(
            _MARGIN,
            y,
            _FIXTURE_STAMP.upper(),
            ha="left",
            va="top",
            color=bk.c("ink"),
            fontproperties=bk.font("mono", "bold", "mono"),
        )
        y -= _frac(bk.SIZE["mono"] * 1.6, fig)
    title_fp = bk.font("display", "bold", "lead")
    wrapped = bk.wrap_to_px(title, title_fp, span_px)
    fig.text(
        _MARGIN,
        y,
        wrapped,
        ha="left",
        va="top",
        color=bk.c("ink"),
        linespacing=bk.LINE_HEIGHT["snug"],
        fontproperties=title_fp,
    )
    y -= _frac(bk.SIZE["lead"] * bk.LINE_HEIGHT["snug"] * (wrapped.count("\n") + 1), fig)
    if subtitle:
        ctx_fp = bk.font("display", "regular", "body")
        lines = bk.wrap_to_px(subtitle, ctx_fp, span_px)
        y -= _frac(4, fig)
        fig.text(
            _MARGIN,
            y,
            lines,
            ha="left",
            va="top",
            color=bk.c("ink-2"),
            linespacing=1.15,
            fontproperties=ctx_fp,
        )
        y -= _frac(bk.SIZE["body"] * 1.15 * (lines.count("\n") + 1), fig)
    return y - _frac(8, fig)


def _footer(fig: Figure, source: str, tag: str | None) -> float:
    """Provenance strip (bk.footer); returns the bottom edge left for the axes.

    The tag's first word (VERIFIED / CALIBRATED / SIMULATED) stands bottom-right;
    the rest of the tag is the note under the source line (RP-702).
    """
    word, _, rest = (tag or "").partition(" · ")
    note = rest[:1].upper() + rest[1:] if rest else None
    fig_h_px = float(fig.get_size_inches()[1]) * bk.PX_PER_IN
    y = 0.055
    if note:
        span_px = (1 - 2 * _MARGIN) * float(fig.get_size_inches()[0]) * bk.PX_PER_IN
        n_lines = (
            bk.wrap_to_px(note, bk.font("display", "regular", "body"), span_px).count("\n") + 1
        )
        note_h_px = bk.SIZE["body"] * bk.PX_PER_IN / 72 * 1.15 * n_lines
        # the y bk.footer would move the strip to so the note stays on the canvas
        y = (
            bk.SPACE_PX[1] + note_h_px + bk.SIZE["mono"] * bk.PX_PER_IN / 72 + bk.SPACE_PX[1]
        ) / fig_h_px
    bk.footer(
        fig,
        source=source.removeprefix("Source: "),
        tag=word or None,
        note=note,
        left=_MARGIN,
        right=_MARGIN,
        y=y,
    )
    return y + 0.028 + _frac(6, fig)


def _fit_ylabels(fig: Figure, band: float) -> None:
    """Wrap a y-axis label that would run past the plot band into the header."""
    max_px = band * float(fig.get_size_inches()[1]) * bk.PX_PER_IN - 72
    fp = bk.font("mono", "regular", "mono")
    for ax in fig.axes:
        label = ax.yaxis.label
        text = label.get_text()
        if text and "\n" not in text and bk.text_width_px(text, fp) > max_px:
            label.set_text(bk.wrap_to_px(text, fp, max_px))


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
    top = _header(fig, title, subtitle, fixture)
    bottom = _footer(fig, source, tag)
    _fit_ylabels(fig, top - bottom)
    if colorbar_room:
        plot_bottom = bottom + 0.09
        fig.subplots_adjust(
            left=0.05, right=1.0 - colorbar_room, top=top - 0.04, bottom=plot_bottom, wspace=0.12
        )
        for ax in fig.axes:
            if ax.get_label() == "<colorbar>":
                x0, _, width, _ = ax.get_position().bounds
                ax.set_position((x0, plot_bottom, width, top - 0.04 - plot_bottom))
    else:
        fig.tight_layout(rect=(0.0, bottom, 1.0, top))
    bk.check_glyphs(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, metadata={"Software": None})
    plt.close(fig)
    return path
