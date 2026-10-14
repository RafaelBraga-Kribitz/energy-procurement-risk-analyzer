"""A1 — Descriptive market structure of the AT day-ahead market (SPEC-04 A1).

Artifacts in ``reports/analytics/``: ``a1_annual_summary.md`` (+ CSV),
``a1_heatmap_hour_month.png``, ``a1_duration_curves.png``,
``a1_negative_hours.png``. SSOT rows ``annual_mean_price_<year>``,
``neg_hours_<year>`` (VERIFIED, complete years only) and ``data_last_month``.
The summary ends with the "So what for a procurement manager" paragraph
(AN-105), written from the computed numbers so it stays true on new data.

Implements: AN-101..105.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from epra.analytics._shared import (
    analytics_dir,
    by_year,
    complete_years,
    md_table,
    query,
    write_markdown,
)
from epra.common.config import Settings
from epra.common.provenance import is_fixture_run
from epra.common.ssot import SsotRow, write_ssot_rows
from epra.report.figure import new_figure, save_figure

HOURLY_SQL = """
select
    fph.year_local,
    fph.month_local,
    fph.hour_local,
    fph.is_peak_hour,
    fph.price_at_eur_mwh
from marts.fct_price_hourly as fph
where fph.price_at_eur_mwh is not null
order by fph.ts_utc
"""

SPIKE_EUR_MWH = 500.0  # AN-101 threshold
HEATMAP_YEARS = range(2021, 2026)  # AN-102 panels
SOLAR_MONTHS = range(4, 10)  # AN-104: Apr-Sep
SOLAR_HOURS = range(10, 17)  # AN-104: 10-16 local


def annual_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    """AN-101 per-year table (AT, EUR/MWh, hours).

    Implements: AN-101, AN-104 (negative-hour columns).
    """
    rows = []
    for year in sorted(hourly["year_local"].unique()):
        g = hourly[hourly["year_local"] == year]
        price = g["price_at_eur_mwh"]
        neg = price[price < 0]
        solar = g["month_local"].isin(SOLAR_MONTHS) & g["hour_local"].isin(SOLAR_HOURS)
        peak = price[g["is_peak_hour"]].mean()
        offpeak = price[~g["is_peak_hour"]].mean()
        rows.append(
            {
                "year": year,
                "hours": len(g),
                "mean": price.mean(),
                "median": price.median(),
                "std": price.std(),
                "min": price.min(),
                "max": price.max(),
                "base": price.mean(),
                "peak": peak,
                "offpeak": offpeak,
                "peak_minus_offpeak": peak - offpeak,
                "neg_hours": len(neg),
                "neg_share_pct": 100.0 * len(neg) / len(g),
                "neg_mean_depth": -neg.mean() if len(neg) else 0.0,
                "neg_share_solar_pct": (
                    100.0 * (solar & (price < 0)).sum() / len(neg) if len(neg) else 0.0
                ),
                "hours_above_500": int((price > SPIKE_EUR_MWH).sum()),
            }
        )
    return pd.DataFrame(rows)


def _heatmap(hourly: pd.DataFrame, settings: Settings) -> None:
    years = [y for y in HEATMAP_YEARS if y in set(hourly["year_local"])]
    if not years:
        return
    grids = {
        y: hourly[hourly["year_local"] == y]
        .pivot_table(index="hour_local", columns="month_local", values="price_at_eur_mwh")
        .reindex(index=range(24), columns=range(1, 13))
        for y in years
    }
    vmax = float(
        np.nanpercentile(np.concatenate([g.to_numpy().ravel() for g in grids.values()]), 99)
    )
    vmin = float(min(0.0, np.nanmin([np.nanmin(g.to_numpy()) for g in grids.values()])))
    fig, axes = new_figure(1, len(years), sharey=True)
    axes = np.atleast_1d(axes)
    image: Any = None
    for ax, year in zip(axes, years, strict=True):
        image = ax.imshow(
            grids[year].to_numpy(),
            aspect="auto",
            origin="lower",
            cmap="magma",
            vmin=vmin,
            vmax=vmax,
            extent=(0.5, 12.5, -0.5, 23.5),
        )
        ax.set_title(str(year))
        ax.set_xlabel("Month")
        ax.set_xticks([1, 4, 7, 10])
    axes[0].set_ylabel("Hour of day (local)")
    cax = fig.add_axes((0.93, 0.13, 0.015, 0.72))
    fig.colorbar(image, cax=cax, label="Mean price (EUR/MWh)")
    save_figure(
        fig,
        analytics_dir(settings) / "a1_heatmap_hour_month.png",
        title="The crisis lifted every hour; since then solar hollows out summer middays",
        subtitle="Mean AT day-ahead price by hour of day × month, shared colour scale",
        fixture=is_fixture_run(settings),
        colorbar_room=0.09,
    )


def _duration_curves(hourly: pd.DataFrame, settings: Settings) -> None:
    fig, ax = new_figure()
    crisis = {2022, 2023}
    for year, g in hourly.groupby("year_local", sort=True):
        prices = np.sort(g["price_at_eur_mwh"].to_numpy())[::-1]
        x = np.linspace(0, 100, len(prices))
        style = {"lw": 2.4, "ls": "-"} if year in crisis else {"lw": 1.2, "ls": "--"}
        ax.plot(x, prices, label=str(year), **style)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Share of hours in the year (%)")
    ax.set_ylabel("Price (EUR/MWh)")
    ax.legend(ncol=4, frameon=False)
    save_figure(
        fig,
        analytics_dir(settings) / "a1_duration_curves.png",
        title="Crisis years (bold) sit far above every other year across the whole curve",
        subtitle="Price duration curves: hourly AT prices sorted high to low, one line per year",
        fixture=is_fixture_run(settings),
    )


def _negative_hours(hourly: pd.DataFrame, summary: pd.DataFrame, settings: Settings) -> None:
    fig, (left, right) = new_figure(1, 2)
    left.bar(summary["year"], summary["neg_hours"], color="#0072B2")
    left.set_xticks(summary["year"])
    left.set_xlabel("Year")
    left.set_ylabel("Negative-price hours (count)")
    left.set_title("Negative hours per year")
    neg = hourly[hourly["price_at_eur_mwh"] < 0]
    by_hour = neg.groupby("hour_local").size().reindex(range(24), fill_value=0)
    right.bar(by_hour.index, by_hour.to_numpy(), color="#009E73")
    right.set_xlabel("Hour of day (local)")
    right.set_ylabel("Negative-price hours, all years (count)")
    right.set_title("When they occur")
    save_figure(
        fig,
        analytics_dir(settings) / "a1_negative_hours.png",
        title="Negative prices are a recent, midday phenomenon",
        subtitle="Count of AT hours with a day-ahead price below 0 EUR/MWh",
        fixture=is_fixture_run(settings),
    )


def so_what(summary: pd.DataFrame) -> str:
    """AN-105 interpretation paragraph, built from the computed table.

    Implements: AN-105.
    """
    stats = by_year(summary)
    first = min(stats)
    last_full = max(y for y, row in stats.items() if row["hours"] >= 8700)
    crisis = stats[2022]["mean"] if 2022 in stats else max(r["mean"] for r in stats.values())
    calm = stats[first]["mean"]
    neg_recent = int(stats[last_full]["neg_hours"])
    solar_share = stats[last_full]["neg_share_solar_pct"]
    return (
        "## So what for a procurement manager\n\n"
        f"The Austrian day-ahead market is not one market but several regimes stacked in "
        f"time. In 2022 the average hour cost {crisis:.1f} EUR/MWh, about "
        f"{crisis / calm:.1f} times the {first} level of {calm:.1f} EUR/MWh, and the price "
        f"duration curves show that the crisis lifted every hour of the year rather than "
        f"adding a few extreme spikes. Since then the shape has changed as much as the "
        f"level: solar generation now hollows out the midday hours from April to "
        f"September, which is visible in the heatmap as a dark summer band around noon. "
        f"In {last_full} the market saw {neg_recent} hours with negative prices, and "
        f"{solar_share:.0f}% of them fell in the spring and summer daylight window of "
        f"10:00 to 16:00. For a consumer that can move load, those hours are paid "
        f"consumption; for an inflexible three-shift plant like the reference consumer "
        f"they are a modest discount that does not offset winter evening peaks. Buying "
        f"decisions should therefore be judged against the hourly shape the plant "
        f"actually consumes, not against the headline annual average."
    )


def run(settings: Settings) -> pd.DataFrame:
    """Produce all A1 artifacts from marts; deterministic (AN-705).

    Implements: AN-101..105, AN-703.
    """
    hourly = query(settings, HOURLY_SQL)
    summary = annual_summary(hourly)
    out = analytics_dir(settings)
    summary.round(4).to_csv(out / "a1_annual_summary.csv", index=False)
    _heatmap(hourly, settings)
    _duration_curves(hourly, settings)
    _negative_hours(hourly, summary, settings)
    shown = summary[
        [
            "year",
            "hours",
            "mean",
            "median",
            "std",
            "min",
            "max",
            "peak",
            "offpeak",
            "peak_minus_offpeak",
            "neg_hours",
            "neg_share_pct",
            "neg_mean_depth",
            "neg_share_solar_pct",
            "hours_above_500",
        ]
    ]
    write_markdown(
        settings,
        "a1_annual_summary.md",
        "A1 — AT day-ahead market: annual summary",
        [
            "Hourly AT day-ahead prices in EUR/MWh, per local calendar year (VERIFIED). "
            "`neg_share_solar_pct` is the share of negative hours falling in Apr-Sep "
            "10:00-16:00 local; years with fewer than 8,700 priced hours are partial.",
            "",
            md_table(shown),
            "",
            so_what(summary),
        ],
    )
    years = complete_years(hourly)
    stats = by_year(summary)
    last_year, last_month = (int(v) for v in hourly[["year_local", "month_local"]].iloc[-1])
    rows = (
        [
            SsotRow(
                f"annual_mean_price_{y}",
                round(stats[y]["mean"], 4),
                "EUR/MWh",
                "VERIFIED",
                "analytics/descriptive.py",
            )
            for y in years
        ]
        + [
            SsotRow(
                f"neg_hours_{y}",
                int(stats[y]["neg_hours"]),
                "hours",
                "VERIFIED",
                "analytics/descriptive.py",
            )
            for y in years
        ]
        + [
            SsotRow(
                "data_last_month",
                f"{last_year}-{last_month:02d}",
                "month",
                "VERIFIED",
                "analytics/descriptive.py",
            )
        ]
    )
    write_ssot_rows(rows, "analytics_a1", settings)
    return summary
