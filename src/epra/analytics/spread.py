"""A2 — AT vs DE-LU day-ahead spread (SPEC-04 A2).

Artifacts: ``a2_spread_monthly.png``, ``a2_spread_summary.md``; SSOT rows
``spread_mean_<year>`` (VERIFIED, complete years). The interpretation is the
"you are not in Germany" localization point (AN-203).

Implements: AN-201..203.
"""

from __future__ import annotations

import pandas as pd

from epra.analytics._shared import (
    analytics_dir,
    by_year,
    complete_years,
    query,
    write_markdown,
)
from epra.common.config import Settings
from epra.common.provenance import is_fixture_run
from epra.common.ssot import SsotRow, write_ssot_rows
from epra.report.figure import new_figure, save_figure
from epra.report.format import md_table
from epra.report.style import OKABE_ITO

HOURLY_SPREAD_SQL = """
select
    fph.year_local,
    fph.month_local,
    fph.is_peak_hour,
    fph.spread_at_delu_eur_mwh
from marts.fct_price_hourly as fph
where fph.spread_at_delu_eur_mwh is not null
order by fph.ts_utc
"""


def spread_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    """AN-202 per-year spread statistics (EUR/MWh; share in %).

    Implements: AN-202.
    """
    grouped = hourly.groupby("year_local", sort=True)
    spread = grouped["spread_at_delu_eur_mwh"]
    peak = hourly[hourly["is_peak_hour"]].groupby("year_local")["spread_at_delu_eur_mwh"].mean()
    off = hourly[~hourly["is_peak_hour"]].groupby("year_local")["spread_at_delu_eur_mwh"].mean()
    return pd.DataFrame(
        {
            "year": spread.mean().index.astype(int),
            "hours": grouped.size().to_numpy(),
            "mean": spread.mean().to_numpy(),
            "median": spread.median().to_numpy(),
            "std": spread.std().to_numpy(),
            "share_at_above_de_pct": (
                100.0 * grouped["spread_at_delu_eur_mwh"].apply(lambda s: (s > 0).mean())
            ).to_numpy(),
            "mean_peak": peak.reindex(spread.mean().index).to_numpy(),
            "mean_offpeak": off.reindex(spread.mean().index).to_numpy(),
        }
    )


def _chart(hourly: pd.DataFrame, settings: Settings) -> None:
    monthly = hourly.groupby(["year_local", "month_local"])["spread_at_delu_eur_mwh"].mean()
    x = pd.to_datetime([f"{y}-{m:02d}-01" for y, m in monthly.index])
    share_up = float((monthly > 0).mean())
    fig, ax = new_figure()
    ax.plot(x, monthly.to_numpy(), color=OKABE_ITO["vermillion"], lw=1.8)
    ax.fill_between(
        x,
        monthly.to_numpy(),
        0,
        where=monthly.to_numpy() > 0,
        color=OKABE_ITO["vermillion"],
        alpha=0.15,
    )
    ax.axhline(0, color="black", lw=0.9)
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean spread AT − DE-LU (EUR/MWh)")
    save_figure(
        fig,
        analytics_dir(settings) / "a2_spread_monthly.png",
        title=(
            f"Austria was dearer than Germany in {share_up:.0%} of months"
            if share_up >= 0.5
            else f"Austria was cheaper than Germany in {1 - share_up:.0%} of months"
        ),
        subtitle="Monthly mean of hourly day-ahead spread AT minus DE-LU; above zero = AT dearer",
        fixture=is_fixture_run(settings),
    )


def interpretation(summary: pd.DataFrame) -> str:
    """AN-203 paragraph from the computed numbers.

    Implements: AN-203.
    """
    full = {y: r for y, r in by_year(summary).items() if r["hours"] >= 8700}
    widest_year = max(full, key=lambda y: full[y]["mean"])
    widest = full[widest_year]["mean"]
    share = sum(r["share_at_above_de_pct"] for r in full.values()) / len(full)
    mean_all = sum(r["mean"] for r in full.values()) / len(full)
    direction = "premium" if mean_all > 0 else "discount"
    return (
        "## Interpretation — you are not in Germany\n\n"
        f"Across the complete years in the window the Austrian price sat above the German "
        f"one in {share:.0f}% of hours on average, and the annual mean spread was widest in "
        f"{widest_year} at {widest:.1f} EUR/MWh. Since the 2018 bidding-zone "
        f"split, cross-border capacity is limited, so when it binds the Austrian zone clears "
        f"on its own, typically at a {direction} to Germany. For an Austrian buyer this "
        f"means that German price reporting, German index products and German benchmarks "
        f"systematically misstate what an Austrian plant pays: a supplier quote that looks "
        f"cheap against a German reference can still be expensive for Austria, and a hedge "
        f"bought on a German product leaves the spread unhedged. Procurement benchmarks and "
        f"contract indexation for this consumer should therefore reference the Austrian "
        f"zone, and the spread itself is a risk that needs to be budgeted."
    )


def run(settings: Settings) -> pd.DataFrame:
    """Produce all A2 artifacts from marts; deterministic (AN-705).

    Implements: AN-201..203, AN-703.
    """
    hourly = query(settings, HOURLY_SPREAD_SQL)
    summary = spread_summary(hourly)
    summary.round(4).to_csv(analytics_dir(settings) / "a2_spread_summary.csv", index=False)
    _chart(hourly, settings)
    write_markdown(
        settings,
        "a2_spread_summary.md",
        "A2 — AT vs DE-LU day-ahead spread",
        [
            "Hourly spread = AT price − DE-LU price, EUR/MWh, per local year (VERIFIED). "
            "Peak = Mon-Fri 08-20 local, non-holiday.",
            "",
            md_table(summary),
            "",
            interpretation(summary),
        ],
    )
    stats = by_year(summary)
    rows = [
        SsotRow(
            f"spread_mean_{y}",
            round(stats[y]["mean"], 4),
            "EUR/MWh",
            "VERIFIED",
            "analytics/spread.py",
        )
        for y in complete_years(hourly)
    ]
    write_ssot_rows(rows, "analytics_a2", settings)
    return summary
