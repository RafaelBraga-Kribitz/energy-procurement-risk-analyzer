"""A2 — AT versus DE-LU spread (SPEC-04 AN-201..203).

Drop hours where either AT or DE-LU price is NULL. Spread is AT minus DE-LU.
SSOT keys ``spread_mean_<year>`` are VERIFIED.

Implements: AN-201, AN-202, AN-203, AN-704.
"""

from __future__ import annotations

import logging
from typing import Any, Final, cast

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
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

PRODUCED_BY: Final = "epra.analytics.spread"
AT_COL: Final = "price_at_eur_mwh"
DELU_COL: Final = "price_delu_eur_mwh"
SPREAD_COL: Final = "spread_at_minus_delu"
ZERO_LINE_LABEL: Final = "zero"

AN202_COLUMNS: Final[tuple[str, ...]] = (
    "year_local",
    "n_hours",
    "spread_mean",
    "spread_median",
    "spread_std",
    "share_at_gt_delu",
    "spread_mean_peak",
    "spread_mean_offpeak",
)


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _as_float(value: object) -> float:
    return float(cast(Any, value))


def _both_priced(hourly: pd.DataFrame) -> pd.DataFrame:
    """Hours with both AT and DE-LU prices (NULL is not zero).

    Implements: AN-201, AN-202.
    """
    needed = (AT_COL, DELU_COL, "year_local", "month_local", "is_peak_hour")
    missing = [c for c in needed if c not in hourly.columns]
    if missing:
        raise ValueError(f"hourly frame missing columns: {missing}")
    out = hourly.dropna(subset=[AT_COL, DELU_COL]).copy()
    out[SPREAD_COL] = out[AT_COL].astype("float64") - out[DELU_COL].astype("float64")
    return out


def count_dropped_spread_hours(hourly: pd.DataFrame) -> int:
    """Rows dropped because AT or DE-LU price is NULL.

    Implements: AN-202.
    """
    if AT_COL not in hourly.columns or DELU_COL not in hourly.columns:
        raise ValueError("hourly frame missing AT or DE-LU price column")
    return int(hourly[[AT_COL, DELU_COL]].isna().any(axis=1).sum())


def spread_stats(hourly: pd.DataFrame) -> pd.DataFrame:
    """Per-year AT minus DE-LU statistics.

    Implements: AN-202.
    """
    priced = _both_priced(hourly)
    if priced.empty:
        return pd.DataFrame(columns=list(AN202_COLUMNS))
    rows: list[dict[str, object]] = []
    for year, grp in priced.groupby("year_local", sort=True):
        spread = grp[SPREAD_COL].astype("float64")
        peak_mask = grp["is_peak_hour"].astype(bool)
        n = len(spread)
        peak = spread[peak_mask]
        off = spread[~peak_mask]
        rows.append(
            {
                "year_local": _as_int(year),
                "n_hours": n,
                "spread_mean": float(spread.mean()),
                "spread_median": float(spread.median()),
                "spread_std": float(spread.std(ddof=1)) if n > 1 else float("nan"),
                "share_at_gt_delu": float((spread > 0).mean()),
                "spread_mean_peak": float(peak.mean()) if len(peak) else float("nan"),
                "spread_mean_offpeak": float(off.mean()) if len(off) else float("nan"),
            }
        )
    return pd.DataFrame(rows, columns=list(AN202_COLUMNS))


def monthly_mean_spread(hourly: pd.DataFrame) -> pd.DataFrame:
    """Year-month mean AT minus DE-LU spread.

    Implements: AN-201.
    """
    priced = _both_priced(hourly)
    if priced.empty:
        return pd.DataFrame(columns=["year_local", "month_local", "spread_mean"])
    grouped = (
        priced.groupby(["year_local", "month_local"], sort=True)[SPREAD_COL]
        .mean()
        .reset_index(name="spread_mean")
    )
    return grouped


def figure_spread_monthly(hourly: pd.DataFrame) -> Figure:
    """Monthly mean spread line with a zero reference.

    Implements: AN-201.
    """
    monthly = monthly_mean_spread(hourly)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    if not monthly.empty:
        stamps = np.array(
            [
                np.datetime64(f"{_as_int(row.year_local):04d}-{_as_int(row.month_local):02d}-01")
                for row in monthly.itertuples(index=False)
            ],
            dtype="datetime64[D]",
        )
        ax.plot(
            stamps,
            monthly["spread_mean"].to_numpy(dtype=np.float64),
            color=OKABE_ITO["blue"],
            label="monthly mean AT-DE-LU",
        )
    ax.axhline(0.0, color=OKABE_ITO["black"], linestyle="--", linewidth=1.0, label=ZERO_LINE_LABEL)
    ax.set_xlabel("month")
    ax.set_ylabel("EUR/MWh")
    ax.legend()
    fig.subplots_adjust(bottom=0.18)
    return fig


def zero_line_present(fig: Figure) -> bool:
    """True when the monthly chart has an ``axhline(0)`` labeled zero."""
    ax = fig.axes[0]
    for line in ax.get_lines():
        if line.get_label() != ZERO_LINE_LABEL:
            continue
        y = np.asarray(line.get_ydata(), dtype=np.float64)
        if y.size and np.allclose(y, 0.0):
            return True
    return False


def _format_stats_md(stats: pd.DataFrame) -> pd.DataFrame:
    if stats.empty:
        return pd.DataFrame(columns=list(AN202_COLUMNS))
    out = stats.copy()
    for col in (
        "spread_mean",
        "spread_median",
        "spread_std",
        "spread_mean_peak",
        "spread_mean_offpeak",
    ):
        out[col] = [format_eur_mwh(_as_float(v)) if pd.notna(v) else "" for v in out[col]]
    out["share_at_gt_delu"] = [
        format_pct(_as_float(v)) if pd.notna(v) else "" for v in out["share_at_gt_delu"]
    ]
    out["year_local"] = [str(_as_int(v)) for v in out["year_local"]]
    out["n_hours"] = [str(_as_int(v)) for v in out["n_hours"]]
    return out


def so_what_paragraph(stats: pd.DataFrame, *, n_dropped: int) -> str:
    """AN-203 localization: an Austrian buyer is not in Germany.

    Implements: AN-203, AN-704, RP-703.
    """
    if stats.empty:
        mean_txt = "not computed (no overlapping AT and DE-LU hours)"
        share_txt = format_pct(0.0)
        peak_txt = "not computed"
    else:
        overall_mean = float(
            np.average(stats["spread_mean"].astype("float64"), weights=stats["n_hours"])
        )
        mean_txt = format_eur_mwh(overall_mean)
        share_txt = format_pct(
            float(np.average(stats["share_at_gt_delu"].astype("float64"), weights=stats["n_hours"]))
        )
        last = stats.iloc[-1]
        peak_txt = (
            f"year {_as_int(last['year_local'])} peak-hour mean spread "
            f"{format_eur_mwh(_as_float(last['spread_mean_peak']))} versus off-peak "
            f"{format_eur_mwh(_as_float(last['spread_mean_offpeak']))}"
        )
    return (
        "So what for a procurement manager. You are not in Germany: a persistent "
        "positive AT premium means Austrian day-ahead hours clear above DE-LU, so a "
        "buyer who benchmarks invoices against German price reporting will understate "
        f"the locked-in euro cost of consuming in Austria. The sample mean AT minus "
        f"DE-LU spread is {mean_txt}, and AT is strictly above DE-LU in {share_txt} of "
        "overlapping priced hours. That gap is a localization residual, not a data "
        "error: congestion, reserve mix, and Austrian load shape can keep AT expensive "
        f"relative to the German-Luxembourg zone even when headlines quote DE. {peak_txt}. "
        "Peak-hour premia compound the miss if the plant cannot shift load, while a "
        "negative spread (AT cheaper than DE-LU) is a credit that German-index hedges "
        "would not automatically pass through. Dropped hours with a NULL on either "
        f"side ({n_dropped}) are missing market prints, not zero spread, and are "
        "excluded from every statistic above. Contract design that copies a German "
        "forward or a DE-LU TTF-style narrative without an AT basis will mis-rank "
        "spot versus indexed products for this consumer. Treat the zero line on the "
        "monthly chart as the Germany-equivalence test: time spent above it is the "
        "Austrian premium you actually pay."
    )


def render_spread_summary_md(stats: pd.DataFrame, *, n_dropped: int) -> str:
    """Markdown table plus AN-203 paragraph.

    Implements: AN-202, AN-203, AN-704.
    """
    table = frame_to_markdown(_format_stats_md(stats))
    prose = so_what_paragraph(stats, n_dropped=n_dropped)
    return (
        "# A2 AT minus DE-LU spread (AN-202)\n\n"
        f"Dropped hours with NULL AT or DE-LU price: {n_dropped} (not treated as 0).\n\n"
        f"{table}\n\n"
        f"{prose}\n"
    )


def ssot_rows_from_stats(stats: pd.DataFrame) -> list[dict[str, object]]:
    """``spread_mean_<year>`` VERIFIED rows.

    Implements: AN-202, AN-703, D-03.
    """
    rows: list[dict[str, object]] = []
    for rec in stats.itertuples(index=False):
        rows.append(
            {
                "key": f"spread_mean_{_as_int(rec.year_local)}",
                "value": _as_float(rec.spread_mean),
                "unit": "EUR/MWh",
                "tag": "VERIFIED",
                "produced_by": PRODUCED_BY,
            }
        )
    return rows


def run(settings: Settings, *, hourly: pd.DataFrame | None = None) -> None:
    """Write A2 artifacts and upsert analytics SSOT rows.

    Implements: AN-201, AN-202, AN-203, D-01.
    """
    frame = hourly if hourly is not None else load_price_hourly(settings)
    n_dropped = count_dropped_spread_hours(frame)
    logger.info("A2 dropped %s hours with NULL AT or DE-LU price", n_dropped)
    stats = spread_stats(frame)
    out = analytics_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    write_markdown(
        out / "a2_spread_summary.md", render_spread_summary_md(stats, n_dropped=n_dropped)
    )
    save_png(figure_spread_monthly(frame), out / "a2_spread_monthly.png")
    write_ssot_rows(ssot_rows_from_stats(stats), settings)
    logger.info("A2 wrote artifacts under %s", out)
