"""A1 — Descriptive market structure (SPEC-04 AN-101..105).

Reads hourly AT prices from marts (or an injected frame). NULL
``price_at_eur_mwh`` hours are dropped, never treated as zero. Charts go
through the shared kit (RP-701/702). SSOT keys are VERIFIED.

Implements: AN-101, AN-102, AN-103, AN-104, AN-105, AN-704, D-07, D-08.
"""

from __future__ import annotations

import logging
from typing import Any, Final, cast

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import to_hex
from matplotlib.figure import Figure

from epra.analytics._kit import (
    analytics_dir,
    frame_to_markdown,
    load_price_hourly,
    save_png,
    write_markdown,
    write_ssot_rows,
)
from epra.common.config import Settings
from epra.report.format import format_eur_mwh, format_pct
from epra.report.style import FIGSIZE, OKABE_ITO

logger = logging.getLogger(__name__)

PRODUCED_BY: Final = "epra.analytics.descriptive"
HEATMAP_YEARS: Final[tuple[int, ...]] = (2021, 2022, 2023, 2024, 2025)
EMPTY_PANEL_TITLE: Final = "{year} - no complete data"
PRICE_COL: Final = "price_at_eur_mwh"

AN101_COLUMNS: Final[tuple[str, ...]] = (
    "year_local",
    "n_hours",
    "hourly_mean",
    "hourly_median",
    "hourly_std",
    "hourly_min",
    "hourly_max",
    "base_mean",
    "base_median",
    "base_std",
    "base_min",
    "base_max",
    "peak_mean",
    "peak_median",
    "peak_std",
    "peak_min",
    "peak_max",
    "offpeak_mean",
    "offpeak_median",
    "offpeak_std",
    "offpeak_min",
    "offpeak_max",
    "peak_offpeak_spread",
    "n_negative",
    "share_negative",
    "n_gt_500",
)

_EUR_STAT_COLS: Final[tuple[str, ...]] = tuple(
    c
    for c in AN101_COLUMNS
    if c not in {"year_local", "n_hours", "n_negative", "share_negative", "n_gt_500"}
)


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _as_float(value: object) -> float:
    return float(cast(Any, value))


_NON_CRISIS_COLORS: Final[tuple[str, ...]] = (
    OKABE_ITO["orange"],
    OKABE_ITO["sky_blue"],
    OKABE_ITO["bluish_green"],
    OKABE_ITO["yellow"],
    OKABE_ITO["blue"],
    OKABE_ITO["reddish_purple"],
    OKABE_ITO["black"],
)


def _priced_hours(hourly: pd.DataFrame) -> pd.DataFrame:
    """Drop NULL AT prices (calendar spine hours are not zeros).

    Implements: AN-101.
    """
    if PRICE_COL not in hourly.columns:
        raise ValueError(f"hourly frame missing {PRICE_COL}")
    needed = ("year_local", "month_local", "hour_local", "is_peak_hour", PRICE_COL)
    missing = [c for c in needed if c not in hourly.columns]
    if missing:
        raise ValueError(f"hourly frame missing columns: {missing}")
    return hourly.dropna(subset=[PRICE_COL]).copy()


def count_dropped_price_hours(hourly: pd.DataFrame) -> int:
    """How many rows were dropped for NULL ``price_at_eur_mwh``.

    Implements: AN-101.
    """
    if PRICE_COL not in hourly.columns:
        raise ValueError(f"hourly frame missing {PRICE_COL}")
    return int(hourly[PRICE_COL].isna().sum())


def _moments(series: pd.Series) -> dict[str, float]:
    values = series.astype("float64")
    if values.empty:
        nan = float("nan")
        return {"mean": nan, "median": nan, "std": nan, "min": nan, "max": nan}
    return {
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std(ddof=1)) if len(values) > 1 else float("nan"),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def _year_row(year: int, grp: pd.DataFrame) -> dict[str, object]:
    prices = grp[PRICE_COL].astype("float64")
    peak_mask = grp["is_peak_hour"].astype(bool)
    peak = _moments(prices[peak_mask])
    off = _moments(prices[~peak_mask])
    hourly = _moments(prices)
    n = len(prices)
    n_neg = int((prices < 0).sum())
    spread = (
        peak["mean"] - off["mean"]
        if np.isfinite(peak["mean"]) and np.isfinite(off["mean"])
        else float("nan")
    )
    return {
        "year_local": year,
        "n_hours": n,
        "hourly_mean": hourly["mean"],
        "hourly_median": hourly["median"],
        "hourly_std": hourly["std"],
        "hourly_min": hourly["min"],
        "hourly_max": hourly["max"],
        "base_mean": hourly["mean"],
        "base_median": hourly["median"],
        "base_std": hourly["std"],
        "base_min": hourly["min"],
        "base_max": hourly["max"],
        "peak_mean": peak["mean"],
        "peak_median": peak["median"],
        "peak_std": peak["std"],
        "peak_min": peak["min"],
        "peak_max": peak["max"],
        "offpeak_mean": off["mean"],
        "offpeak_median": off["median"],
        "offpeak_std": off["std"],
        "offpeak_min": off["min"],
        "offpeak_max": off["max"],
        "peak_offpeak_spread": spread,
        "n_negative": n_neg,
        "share_negative": (n_neg / n) if n else float("nan"),
        "n_gt_500": int((prices > 500.0).sum()),
    }


def annual_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    """AN-101 columns per ``year_local``. Peak = ``is_peak_hour``; base = all hours.

    Implements: AN-101.
    """
    priced = _priced_hours(hourly)
    if priced.empty:
        return pd.DataFrame(columns=list(AN101_COLUMNS))
    rows = [_year_row(_as_int(year), grp) for year, grp in priced.groupby("year_local", sort=True)]
    return pd.DataFrame(rows, columns=list(AN101_COLUMNS))


def year_is_complete(year_df: pd.DataFrame) -> bool:
    """True when all 12 local months have at least one priced hour.

    Implements: AN-102, D-07.
    """
    months = {_as_int(m) for m in year_df["month_local"].dropna().unique()}
    return set(range(1, 13)) <= months


def month_hour_grid(year_df: pd.DataFrame) -> np.ndarray:
    """12 x 24 mean AT price (month 1-12, hour 0-23).

    Implements: AN-102.
    """
    grid = np.full((12, 24), np.nan, dtype=np.float64)
    agg = year_df.groupby(["month_local", "hour_local"], sort=False)[PRICE_COL].mean().reset_index()
    for rec in agg.itertuples(index=False):
        m_i = _as_int(rec.month_local)
        h_i = _as_int(rec.hour_local)
        if 1 <= m_i <= 12 and 0 <= h_i <= 23:
            grid[m_i - 1, h_i] = _as_float(getattr(rec, PRICE_COL))
    return grid


def _shared_clim(grids: dict[int, np.ndarray]) -> tuple[float, float] | None:
    stacked = [g for g in grids.values() if g is not None]
    if not stacked:
        return None
    finite = np.concatenate([g[np.isfinite(g)] for g in stacked])
    if finite.size == 0:
        return None
    vmin = float(np.min(finite))
    vmax = float(np.max(finite))
    if vmin == vmax:
        vmax = vmin + 1.0
    return vmin, vmax


def figure_heatmap(hourly: pd.DataFrame) -> Figure:
    """Five panels 2021-2025; incomplete years are empty axes.

    Implements: AN-102, D-07, RP-701.
    """
    priced = _priced_hours(hourly)
    grids: dict[int, np.ndarray] = {}
    for year in HEATMAP_YEARS:
        sl = priced.loc[priced["year_local"] == year]
        if not sl.empty and year_is_complete(sl):
            grids[year] = month_hour_grid(sl)
    clim = _shared_clim(grids)
    fig, axes = plt.subplots(1, 5, figsize=FIGSIZE, sharey=True)
    last_im = None
    for ax, year in zip(np.ravel(axes), HEATMAP_YEARS, strict=True):
        ax.set_xlabel("hour_local")
        if year in grids and clim is not None:
            last_im = ax.imshow(
                grids[year],
                origin="lower",
                aspect="auto",
                vmin=clim[0],
                vmax=clim[1],
                cmap="cividis",
            )
            ax.set_title(str(year))
            ax.set_yticks(range(12))
            ax.set_yticklabels([str(m) for m in range(1, 13)])
            ax.set_ylabel("month_local")
        else:
            ax.set_title(EMPTY_PANEL_TITLE.format(year=year))
            ax.set_xticks([])
            ax.set_yticks([])
    if last_im is not None:
        fig.colorbar(last_im, ax=list(np.ravel(axes)), fraction=0.02, pad=0.02, label="EUR/MWh")
    fig.subplots_adjust(bottom=0.18)
    return fig


def _year_color(year: int, other_years: list[int]) -> str:
    if year == 2022:
        return OKABE_ITO["vermillion"]
    idx = other_years.index(year)
    return _NON_CRISIS_COLORS[idx % len(_NON_CRISIS_COLORS)]


def figure_duration_curves(hourly: pd.DataFrame) -> Figure:
    """One line per year; 2022 vermillion; linear EUR/MWh vs 0-100% of hours.

    Implements: AN-103, D-08.
    """
    priced = _priced_hours(hourly)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    years = sorted(_as_int(y) for y in priced["year_local"].unique())
    others = [y for y in years if y != 2022]
    for year in years:
        prices = priced.loc[priced["year_local"] == year, PRICE_COL].astype("float64")
        y = np.sort(prices.to_numpy())[::-1]
        n = y.size
        x = (np.arange(n, dtype=np.float64) / max(n - 1, 1)) * 100.0 if n > 1 else np.array([0.0])
        color = _year_color(year, others)
        zorder = 5 if year == 2022 else 2
        ax.plot(x, y, color=color, label=str(year), zorder=zorder)
    ax.set_yscale("linear")
    ax.set_xlabel("fraction of hours (%)")
    ax.set_ylabel("EUR/MWh")
    ax.set_xlim(0.0, 100.0)
    if years:
        ax.legend(title="year_local")
    fig.subplots_adjust(bottom=0.18)
    return fig


def negative_hour_stats(hourly: pd.DataFrame) -> pd.DataFrame:
    """Per-year negative count, mean depth below zero, Apr-Sep 10-16 share.

    Implements: AN-104.
    """
    priced = _priced_hours(hourly)
    rows: list[dict[str, object]] = []
    for year, grp in priced.groupby("year_local", sort=True):
        neg = grp.loc[grp[PRICE_COL].astype("float64") < 0]
        n = len(neg)
        if n:
            depth = float((-neg[PRICE_COL].astype("float64")).mean())
            daylight = neg["month_local"].between(4, 9) & neg["hour_local"].between(10, 16)
            share = float(daylight.mean())
        else:
            depth = float("nan")
            share = 0.0
        rows.append(
            {
                "year_local": _as_int(year),
                "n_negative": n,
                "mean_depth_eur_mwh": depth,
                "daylight_apr_sep_share": share,
            }
        )
    return pd.DataFrame(rows)


def figure_negative_hours(hourly: pd.DataFrame) -> Figure:
    """Bar chart of negative-hour counts by ``hour_local``.

    Implements: AN-104.
    """
    priced = _priced_hours(hourly)
    neg = priced.loc[priced[PRICE_COL].astype("float64") < 0]
    counts = neg.groupby("hour_local").size() if not neg.empty else pd.Series(dtype="int64")
    hours = np.arange(24)
    values = [_as_int(counts.get(h, 0)) for h in hours]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.bar(hours, values, color=OKABE_ITO["sky_blue"], width=0.8)
    ax.set_xlabel("hour_local")
    ax.set_ylabel("negative hours (count)")
    ax.set_xticks(hours)
    fig.subplots_adjust(bottom=0.18)
    return fig


def _row_for_year(summary: pd.DataFrame, year: int) -> pd.Series | None:
    sl = summary.loc[summary["year_local"] == year]
    if sl.empty:
        return None
    return sl.iloc[0]


def _crisis_clause(summary: pd.DataFrame) -> str:
    crisis = _row_for_year(summary, 2022)
    if crisis is not None:
        return (
            "The 2022 crisis level in this table is a mean hourly AT price of "
            f"{format_eur_mwh(_as_float(crisis['hourly_mean']))} "
            f"(median {format_eur_mwh(_as_float(crisis['hourly_median']))})."
        )
    if summary.empty:
        return "The 2022 crisis level cannot be quoted because this frame has no priced hours."
    top = summary.loc[summary["hourly_mean"].idxmax()]
    return (
        "The 2022 crisis level is not in this warehouse window, so no 2022 "
        "EUR/MWh figure is quoted; the highest sample mean is "
        f"year {_as_int(top['year_local'])} at "
        f"{format_eur_mwh(_as_float(top['hourly_mean']))}."
    )


def _depth_and_daylight(neg_stats: pd.DataFrame) -> tuple[str, str]:
    if neg_stats.empty or int(neg_stats["n_negative"].sum()) == 0:
        return "not defined (no negative hours)", format_pct(0.0)
    weighted = neg_stats.loc[neg_stats["n_negative"] > 0]
    depth = float(
        np.average(
            weighted["mean_depth_eur_mwh"].astype("float64"),
            weights=weighted["n_negative"],
        )
    )
    daylight = float(
        np.average(
            weighted["daylight_apr_sep_share"].astype("float64"),
            weights=weighted["n_negative"],
        )
    )
    return format_eur_mwh(depth), format_pct(daylight)


def _spread_clause(summary: pd.DataFrame) -> str:
    recent = summary.loc[summary["year_local"] >= 2021]
    if recent.empty:
        return "the peak versus off-peak spread is not computed here"
    last = recent.iloc[-1]
    return (
        f"year {_as_int(last['year_local'])} shows a peak minus off-peak spread of "
        f"{format_eur_mwh(_as_float(last['peak_offpeak_spread']))}"
    )


def so_what_paragraph(
    summary: pd.DataFrame,
    neg_stats: pd.DataFrame,
    *,
    n_dropped: int,
) -> str:
    """Plain-prose AN-105 paragraph; numbers come from the computed tables.

    Implements: AN-105, AN-704, RP-703, D-08.
    """
    n_neg = int(summary["n_negative"].sum()) if not summary.empty else 0
    n_hours = int(summary["n_hours"].sum()) if not summary.empty else 0
    share = (n_neg / n_hours) if n_hours else 0.0
    n_500 = int(summary["n_gt_500"].sum()) if not summary.empty else 0
    depth_txt, daylight_txt = _depth_and_daylight(neg_stats)
    return (
        "So what for a procurement manager. Solar-driven midday depression in recent "
        "years is the structural pattern a buyer should plan around: cheap hours "
        "cluster around local midday in summer as PV generation presses the "
        f"day-ahead stack, and {_spread_clause(summary)}. {_crisis_clause(summary)} "
        f"Negative hours total {n_neg} ({format_pct(share)} of priced hours) with "
        f"mean depth below zero {depth_txt}. For a flexible consumer those hours "
        "are a credit, not a curiosity: shifting load into April-September daylight "
        f"hours 10-16 local ({daylight_txt} of negatives in that window) captures "
        "the solar trough that a flat baseload profile would miss. Hours above "
        f"500 EUR/MWh ({n_500} in this sample) are the opposite tail and dominate "
        "bill risk for an inflexible plant. Dropped NULL spine hours "
        f"({n_dropped}) are missing market data, not zero prices, and are excluded "
        "from every statistic above. Duration curves use linear EUR/MWh (not log) "
        "so the 2022 crisis year can be compared on the same scale as later solar-"
        "heavy years. Procurement that ignores midday depression, crisis levels, "
        "and negative-hour optionality will mis-rank spot versus contract products."
    )


def _format_summary_md(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=list(AN101_COLUMNS))
    out = summary.copy()
    for col in _EUR_STAT_COLS:
        out[col] = [format_eur_mwh(_as_float(v)) if pd.notna(v) else "" for v in out[col]]
    out["share_negative"] = [
        format_pct(_as_float(v)) if pd.notna(v) else "" for v in out["share_negative"]
    ]
    out["year_local"] = [str(_as_int(v)) for v in out["year_local"]]
    out["n_hours"] = [str(_as_int(v)) for v in out["n_hours"]]
    out["n_negative"] = [str(_as_int(v)) for v in out["n_negative"]]
    out["n_gt_500"] = [str(_as_int(v)) for v in out["n_gt_500"]]
    return out


def render_annual_summary_md(
    summary: pd.DataFrame,
    neg_stats: pd.DataFrame,
    *,
    n_dropped: int,
) -> str:
    """Markdown table plus AN-105 paragraph.

    Implements: AN-101, AN-105, AN-704.
    """
    table = frame_to_markdown(_format_summary_md(summary))
    prose = so_what_paragraph(summary, neg_stats, n_dropped=n_dropped)
    return (
        "# A1 annual summary (AN-101)\n\n"
        f"Dropped NULL price_at_eur_mwh hours: {n_dropped} (not treated as 0).\n\n"
        f"{table}\n\n"
        f"{prose}\n"
    )


def ssot_rows_from_summary(summary: pd.DataFrame) -> list[dict[str, object]]:
    """``annual_mean_price_<year>`` and ``neg_hours_<year>`` VERIFIED rows.

    Implements: AN-104, AN-703, D-03.
    """
    rows: list[dict[str, object]] = []
    for rec in summary.itertuples(index=False):
        year = _as_int(rec.year_local)
        rows.append(
            {
                "key": f"annual_mean_price_{year}",
                "value": _as_float(rec.hourly_mean),
                "unit": "EUR/MWh",
                "tag": "VERIFIED",
                "produced_by": PRODUCED_BY,
            }
        )
        rows.append(
            {
                "key": f"neg_hours_{year}",
                "value": _as_float(rec.n_negative),
                "unit": "hours",
                "tag": "VERIFIED",
                "produced_by": PRODUCED_BY,
            }
        )
    return rows


def duration_line_hex(fig: Figure, year: int) -> str | None:
    """Hex color of the duration-curve line labeled ``year`` (tests / D-08)."""
    ax = fig.axes[0]
    for line in ax.get_lines():
        if line.get_label() == str(year):
            return to_hex(line.get_color()).lower()
    return None


def run(settings: Settings, *, hourly: pd.DataFrame | None = None) -> None:
    """Write A1 artifacts and upsert analytics SSOT rows.

    Implements: AN-101, AN-102, AN-103, AN-104, AN-105, D-01.
    """
    frame = hourly if hourly is not None else load_price_hourly(settings)
    n_dropped = count_dropped_price_hours(frame)
    logger.info("A1 dropped %s NULL price_at_eur_mwh hours (not zeros)", n_dropped)
    summary = annual_summary(frame)
    neg_stats = negative_hour_stats(frame)
    out = analytics_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "a1_annual_summary.md"
    write_markdown(md_path, render_annual_summary_md(summary, neg_stats, n_dropped=n_dropped))
    summary.to_csv(out / "a1_annual_summary.csv", index=False)
    save_png(figure_heatmap(frame), out / "a1_heatmap_hour_month.png")
    save_png(figure_duration_curves(frame), out / "a1_duration_curves.png")
    save_png(figure_negative_hours(frame), out / "a1_negative_hours.png")
    write_ssot_rows(ssot_rows_from_summary(summary), settings)
    logger.info("A1 wrote artifacts under %s", out)
