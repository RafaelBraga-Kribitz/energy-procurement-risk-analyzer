"""Executive charts (SPEC-06 §2) and the shared strategy chart drawers.

- RP-201 ``01_wrong_strategy_cost.png`` — the money chart: per year, the gap
  between the dearest and cheapest strategy (EUR million), annotated with the
  dearest strategy. Its bar values come from :func:`wrong_cost_bars`, which a
  test recomputes from ``exports/strategy_annual_summary.csv`` (RP-301).
- RP-202 ``02_annual_costs_by_strategy.png`` — :func:`annual_cost_chart`.
- RP-203 ``03_forward_risk.png`` — :func:`forward_fan_chart`.
- RP-204 ``04_market_context.png`` — monthly AT base price with HMM regime
  bands and the ÖSPI on an indexed right axis.

All read marts / processed outputs only (RP-301); style per SPEC-06 §7.

Implements: RP-201..204, RP-301, ST-304, ST-403.
"""

from __future__ import annotations

from pathlib import Path

import bk_theme as bk
import numpy as np
import pandas as pd

from epra.common.config import Settings, resolve_repo_path
from epra.common.db import read_sql
from epra.common.frames import scalar
from epra.common.provenance import is_fixture_run
from epra.common.ssot import read_ssot_rows
from epra.report.figure import new_figure, save_figure
from epra.report.format import format_eur_millions
from epra.report.style import (
    CALIBRATED_TAG,
    LP050_CAPTION,
    REGIME_COLORS,
    SIMULATED_TAG,
    ST502_CAPTION,
    STRATEGY_COLORS,
    STRATEGY_LABELS,
)

MARKET_SQL = """
select
    fpm.year_local,
    fpm.month_local,
    fpm.price_base_eur_mwh,
    fpm.oespi_base
from marts.fct_price_monthly as fpm
order by fpm.year_local, fpm.month_local
"""


def annual_cost_chart(annual: pd.DataFrame, path: Path, *, fixture: bool) -> Path:
    """Grouped bars: annual cost per strategy per year — ST-304 #1 / RP-202.

    Implements: ST-304, RP-202.
    """
    years = sorted(annual["year"].unique())
    ids = list(dict.fromkeys(annual["strategy_id"]))
    width = 0.8 / len(ids)
    fig, ax = new_figure()
    for i, sid in enumerate(ids):
        part = annual[annual["strategy_id"] == sid].set_index("year").reindex(years)
        x = np.arange(len(years)) + (i - (len(ids) - 1) / 2) * width
        ax.bar(
            x, part["cost_eur"] / 1e6, width, color=STRATEGY_COLORS[sid], label=STRATEGY_LABELS[sid]
        )
    ax.set_xticks(np.arange(len(years)), [str(y) for y in years])
    ax.set_xlabel("Delivery year")
    ax.set_ylabel("Annual energy cost (EUR million)")
    ax.legend(ncol=3, frameon=False)
    return save_figure(
        fig,
        path,
        title="The same 50 GWh cost very different amounts depending on how it was bought",
        subtitle=f"Annual energy cost per procurement strategy, reference consumer. "
        f"{ST502_CAPTION}",
        tag=CALIBRATED_TAG,
        fixture=fixture,
    )


def forward_fan_chart(
    paths: pd.DataFrame, summary: pd.DataFrame, window: str, path: Path, *, fixture: bool
) -> Path:
    """Box per strategy (P25-P75, whiskers P5-P95, P95 diamond) — ST-403 / RP-203.

    Implements: ST-403, RP-203.
    """
    ids = list(paths.columns)
    fig, ax = new_figure()
    data = [paths[sid].to_numpy() / 1e6 for sid in ids]
    box = ax.boxplot(
        data,
        orientation="horizontal",
        whis=(5, 95),
        showfliers=False,
        patch_artist=True,
        widths=0.55,
        medianprops={"color": bk.c("surface"), "linewidth": 1.5},
        boxprops={"linewidth": 0},
        whiskerprops={"color": bk.c("ink-2")},
        capprops={"color": bk.c("ink-2")},
    )
    for patch, sid in zip(box["boxes"], ids, strict=True):
        patch.set_facecolor(STRATEGY_COLORS[sid])
    base = summary[summary["variant"] == "unconditional"].set_index("strategy_id")
    for i, sid in enumerate(ids, start=1):
        p95 = scalar(base, sid, "p95") / 1e6
        ax.plot(p95, i, marker="D", color=bk.c("ink"), ms=6)
        ax.annotate(
            f"P95 {format_eur_millions(p95 * 1e6)}",
            (p95, i),
            xytext=(8, -3),
            textcoords="offset points",
            fontsize=bk.SIZE["mono-sm"],
            color=bk.c("ink"),
        )
    ax.set_yticks(range(1, len(ids) + 1), [STRATEGY_LABELS[s] for s in ids])
    ax.set_xlabel(f"Total energy cost {window} (EUR million)")
    return save_figure(
        fig,
        path,
        title=f"{STRATEGY_LABELS[str(base['p95'].idxmax())]} carries the fattest cost tail, "
        f"{STRATEGY_LABELS[str(base['p95'].idxmin())]} the thinnest, over the next 12 months",
        subtitle=f"Bootstrap distribution, {len(paths):,} paths: box = P25-P75, whiskers = "
        f"P5-P95, diamond = P95. {ST502_CAPTION}",
        tag=SIMULATED_TAG,
        fixture=fixture,
    )


def wrong_cost_bars(annual: pd.DataFrame) -> pd.DataFrame:
    """RP-201 bar data: ``year, gap_eur, worst, best`` from the annual summary.

    Implements: RP-201, RP-301 (the same numbers a test rebuilds from the CSV).
    """
    rows = []
    for year in sorted(annual["year"].unique()):
        by = annual[annual["year"] == year].set_index("strategy_id")["cost_eur"]
        rows.append(
            {
                "year": int(year),
                "gap_eur": float(by.max() - by.min()),
                "worst": str(by.idxmax()),
                "best": str(by.idxmin()),
            }
        )
    return pd.DataFrame(rows)


def wrong_cost_chart(annual: pd.DataFrame, path: Path, *, fixture: bool) -> Path:
    """RP-201 — the money chart.

    Implements: RP-201.
    """
    bars = wrong_cost_bars(annual)
    fig, ax = new_figure()
    # The gap is money lost to the wrong choice: an adverse variance (IBCS var-neg, ▲).
    ax.bar(
        bars["year"].astype(str),
        bars["gap_eur"] / 1e6,
        color=[bk.variance_color(-gap) for gap in bars["gap_eur"]],
        width=0.6,
    )
    for rec in bars.to_dict("records"):
        amount = bk.variance_label(format_eur_millions(rec["gap_eur"]), -rec["gap_eur"])
        ax.annotate(
            f"{amount}\nworst: {STRATEGY_LABELS[rec['worst']]}",
            (str(rec["year"]), rec["gap_eur"] / 1e6),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=bk.SIZE["mono-sm"],
            color=bk.c("ink"),
        )
    ax.set_ylim(0, float(bars["gap_eur"].max()) / 1e6 * 1.25)
    ax.set_xlabel("Delivery year")
    ax.set_ylabel("Worst minus best strategy (EUR million)")
    total = format_eur_millions(float(bars["gap_eur"].sum()))
    return save_figure(
        fig,
        path,
        title="What the wrong electricity procurement strategy cost a 50 GWh Styrian manufacturer",
        subtitle=f"Gap between the dearest and cheapest of the four strategies, per year; "
        f"{total} over five years. {LP050_CAPTION} {ST502_CAPTION}",
        tag=CALIBRATED_TAG,
        fixture=fixture,
    )


def _monthly_regimes(settings: Settings) -> pd.Series:
    path = resolve_repo_path(settings.paths.data_processed) / "regimes_daily.parquet"
    daily = pd.read_parquet(path)
    month = pd.to_datetime(daily["date_local"]).dt.to_period("M")
    return daily.groupby(month)["regime"].agg(lambda s: s.mode().sort_values().iloc[0])


def market_context_chart(settings: Settings, path: Path) -> Path:
    """RP-204 — monthly base price, regime bands, ÖSPI on an indexed right axis.

    Implements: RP-204.
    """
    market = read_sql(settings, MARKET_SQL)
    month = pd.PeriodIndex(
        [f"{y}-{m:02d}" for y, m in zip(market["year_local"], market["month_local"], strict=True)],
        freq="M",
    )
    x = month.to_timestamp()
    regimes = _monthly_regimes(settings).reindex(month)
    fig, ax = new_figure()
    top = float(market["price_base_eur_mwh"].max()) * 1.1
    for label, color in REGIME_COLORS.items():
        ax.fill_between(
            x,
            0,
            top,
            where=(regimes == label).to_numpy(),
            step="mid",
            color=color,
            lw=0,
            label=f"{label} regime (A3)",
        )
    ax.plot(
        x, market["price_base_eur_mwh"], color=bk.c("sc-ac"), lw=2, label="AT monthly base price"
    )
    ax.set_ylim(0, top)
    ax.set_xlabel("Month")
    ax.set_ylabel("AT day-ahead base price (EUR/MWh)")
    right = ax.twinx()
    first = float(market["oespi_base"].dropna().iloc[0])
    right.plot(
        x,
        100 * market["oespi_base"] / first,
        color=bk.c("hl"),
        lw=1.6,
        ls="--",
        label="ÖSPI base (first month = 100)",
    )
    right.set_ylabel("ÖSPI base, indexed (first month = 100)")
    right.spines["right"].set_visible(True)
    right.grid(False)
    handles = ax.get_legend_handles_labels()
    extra = right.get_legend_handles_labels()
    ax.legend(handles[0] + extra[0], handles[1] + extra[1], frameon=False, loc="upper left", ncol=2)
    return save_figure(
        fig,
        path,
        title="The market you are buying in: one crisis, three regimes, a lagging index",
        subtitle="Monthly AT base price with HMM volatility regimes; the futures-based ÖSPI "
        "follows spot with a delay",
        fixture=is_fixture_run(settings),
    )


def _forward_window(settings: Settings) -> str:
    rows = read_ssot_rows(settings)
    return str(rows.loc[rows["key"] == "forward_window", "value"].iloc[0])


def executive_dir(settings: Settings) -> Path:
    """``reports/executive_charts/`` (SPEC-06 §1)."""
    path = resolve_repo_path(settings.paths.reports) / "executive_charts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_executive_charts(settings: Settings) -> list[Path]:
    """Write the four executive PNGs to ``reports/executive_charts/``.

    Implements: RP-201..204.
    """
    processed = resolve_repo_path(settings.paths.data_processed)
    annual = pd.read_parquet(processed / "strategy_annual_summary.parquet")
    summary = pd.read_parquet(processed / "forward_risk_summary.parquet")
    long_paths = pd.read_parquet(processed / "forward_paths.parquet")
    paths = long_paths[long_paths["variant"] == "unconditional"].pivot(
        index="path", columns="strategy_id", values="cost_eur"
    )[list(dict.fromkeys(annual["strategy_id"]))]
    window = _forward_window(settings)
    out = executive_dir(settings)
    fixture = is_fixture_run(settings)
    return [
        wrong_cost_chart(annual, out / "01_wrong_strategy_cost.png", fixture=fixture),
        annual_cost_chart(annual, out / "02_annual_costs_by_strategy.png", fixture=fixture),
        forward_fan_chart(paths, summary, window, out / "03_forward_risk.png", fixture=fixture),
        market_context_chart(settings, out / "04_market_context.png"),
    ]
