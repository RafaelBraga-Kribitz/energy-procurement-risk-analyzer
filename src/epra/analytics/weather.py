"""A4 — Weather and system-load sensitivity (SPEC-04 AN-401..402).

Daily mean AT system load versus mart ``hdd_18``. Degree-days are never
recomputed here. The StyriaMetal reference profile is weather-invariant;
this module measures the SYSTEM, not the constructed consumer.

Implements: AN-401, AN-402, AN-704, SPEC-04 §5.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Final, cast

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from epra.analytics._kit import (
    analytics_dir,
    frame_to_markdown,
    load_price_hourly,
    save_png,
    write_markdown,
)
from epra.common.config import Settings
from epra.report.style import FIGSIZE, OKABE_ITO

logger = logging.getLogger(__name__)

PRODUCED_BY: Final = "epra.analytics.weather"
FORMULA: Final = "load_mw ~ hdd_18 + C(month_local)"
COV_TYPE: Final = "HC1"
LOAD_COL: Final = "load_at_mw"
HDD_COL: Final = "hdd_18"
INVARIANCE_SENTENCE: Final = (
    "The StyriaMetal reference consumer profile is weather-invariant by "
    "construction: its hourly weights do not depend on temperature, so this "
    "OLS describes Austrian SYSTEM load, not the bill of the constructed plant."
)


@dataclass(frozen=True)
class OlsSummary:
    """Month-FE OLS of daily system load on mart HDD_18.

    Implements: AN-401.
    """

    hdd_coef: float
    hdd_se: float
    n_obs: int
    rsquared: float
    formula: str
    cov_type: str
    summary_text: str


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _as_float(value: object) -> float:
    return float(cast(Any, value))


def daily_system_load(hourly: pd.DataFrame) -> pd.DataFrame:
    """Mean MW and mart HDD per local date (HDD is not recomputed).

    Implements: AN-401, SPEC-04 §5.
    """
    needed = (LOAD_COL, HDD_COL, "date_local", "month_local", "is_weekend")
    missing = [c for c in needed if c not in hourly.columns]
    if missing:
        raise ValueError(f"hourly frame missing columns: {missing}")
    priced = hourly.dropna(subset=[LOAD_COL, HDD_COL]).copy()
    if priced.empty:
        return pd.DataFrame(columns=["date_local", "load_mw", HDD_COL, "month_local", "is_weekend"])
    grouped = priced.groupby("date_local", sort=True)
    return grouped.agg(
        load_mw=(LOAD_COL, "mean"),
        hdd_18=(HDD_COL, "max"),
        month_local=("month_local", "first"),
        is_weekend=("is_weekend", "first"),
    ).reset_index()


def fit_load_hdd(daily: pd.DataFrame) -> OlsSummary:
    """Month fixed effects, HC1 robust SE. Uses column ``hdd_18`` as given.

    Implements: AN-401.
    """
    frame = daily.dropna(subset=["load_mw", HDD_COL, "month_local"]).copy()
    if len(frame) < 3:
        raise ValueError("need at least 3 daily rows for OLS")
    model = smf.ols(FORMULA, data=frame).fit(cov_type=COV_TYPE)
    params = model.params
    bse = model.bse
    return OlsSummary(
        hdd_coef=_as_float(params["hdd_18"]),
        hdd_se=_as_float(bse["hdd_18"]),
        n_obs=int(model.nobs),
        rsquared=_as_float(model.rsquared),
        formula=FORMULA,
        cov_type=COV_TYPE,
        summary_text=str(model.summary()),
    )


def figure_load_vs_hdd(daily: pd.DataFrame, fit: OlsSummary) -> Figure:
    """Scatter of daily load vs mart HDD, colored by weekend.

    Implements: AN-401.
    """
    fig, ax = plt.subplots(figsize=FIGSIZE)
    weekend = daily["is_weekend"].astype(bool)
    hdd = daily[HDD_COL].astype("float64")
    load = daily["load_mw"].astype("float64")
    ax.scatter(
        hdd.loc[~weekend],
        load.loc[~weekend],
        color=OKABE_ITO["orange"],
        label="weekday",
        alpha=0.8,
    )
    ax.scatter(
        hdd.loc[weekend],
        load.loc[weekend],
        color=OKABE_ITO["sky_blue"],
        label="weekend",
        alpha=0.8,
    )
    if hdd.notna().sum() >= 2:
        grid = np.linspace(float(hdd.min()), float(hdd.max()), 50)
        intercept = float(load.mean() - fit.hdd_coef * float(hdd.mean()))
        ax.plot(
            grid,
            intercept + fit.hdd_coef * grid,
            color=OKABE_ITO["black"],
            linestyle="--",
            label="HDD slope (month-FE coef, mean-centered intercept)",
        )
    ax.set_xlabel("HDD_18 (mart column, C-day)")
    ax.set_ylabel("AT system load (mean MW)")
    ax.legend()
    fig.subplots_adjust(bottom=0.18)
    return fig


def so_what_paragraph(fit: OlsSummary, *, n_days: int, n_dropped: int) -> str:
    """AN-402: system sensitivity; constructed consumer is invariant.

    Implements: AN-402, AN-704, RP-703.
    """
    direction = "positive" if fit.hdd_coef > 0 else "non-positive"
    coef_txt = f"{fit.hdd_coef:.3f} MW per HDD_18 unit"
    se_txt = f"{fit.hdd_se:.3f}"
    return (
        "So what for a procurement manager. Austrian SYSTEM load moves with heating "
        f"demand: the month-fixed-effects OLS ({fit.formula}, {fit.cov_type} robust "
        f"standard errors) estimates a {direction} HDD coefficient of {coef_txt} "
        f"(SE {se_txt}) on {fit.n_obs} local days (R-squared {fit.rsquared:.3f}). "
        f"{INVARIANCE_SENTENCE} Do not read this scatter as StyriaMetal consuming more "
        "on cold days; the plant profile is a calendar-weight construct and is "
        "explicitly weather-invariant. HDD_18 is taken from the warehouse mart "
        "(dim_calendar via fct_price_hourly), never recomputed from tavg in this "
        f"module. {n_days} daily points after dropping {n_dropped} hourly rows that "
        "lacked load or HDD. A buyer hedging with weather-linked products is hedging "
        "system residual volume, not the reference profile used in the strategy "
        "simulator. Treat the weekend coloring as a load-shape check, not a second "
        "regression: official inference is the month-FE HC1 table above."
    )


def _coef_table(fit: OlsSummary) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "term": "hdd_18",
                "coef_mw_per_hdd": f"{fit.hdd_coef:.6f}",
                "se_hc1": f"{fit.hdd_se:.6f}",
                "n_obs": str(fit.n_obs),
                "rsquared": f"{fit.rsquared:.4f}",
                "cov_type": fit.cov_type,
            }
        ]
    )


def render_load_weather_md(fit: OlsSummary, *, n_days: int, n_dropped: int) -> str:
    """OLS coefficient table plus AN-402 paragraph.

    Implements: AN-401, AN-402, AN-704.
    """
    table = frame_to_markdown(_coef_table(fit))
    prose = so_what_paragraph(fit, n_days=n_days, n_dropped=n_dropped)
    return (
        "# A4 system load vs HDD_18 (AN-401)\n\n"
        f"Formula: `{fit.formula}` with {fit.cov_type} robust SE. "
        "HDD_18 is the mart column; this module does not recompute degree-days.\n\n"
        f"{table}\n\n"
        f"{prose}\n"
    )


def count_dropped_load_hdd_hours(hourly: pd.DataFrame) -> int:
    """Hourly rows missing system load or mart HDD.

    Implements: AN-401.
    """
    return int(hourly[[LOAD_COL, HDD_COL]].isna().any(axis=1).sum())


def run(settings: Settings, *, hourly: pd.DataFrame | None = None) -> None:
    """Write A4 artifacts from hourly marts (or an injected frame).

    Implements: AN-401, AN-402, D-01.
    """
    frame = hourly if hourly is not None else load_price_hourly(settings)
    n_dropped = count_dropped_load_hdd_hours(frame)
    daily = daily_system_load(frame)
    fit = fit_load_hdd(daily)
    if fit.hdd_coef <= 0:
        logger.warning("A4 HDD coefficient is not positive: %s", fit.hdd_coef)
    out = analytics_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    write_markdown(
        out / "a4_load_weather.md",
        render_load_weather_md(fit, n_days=len(daily), n_dropped=n_dropped),
    )
    save_png(figure_load_vs_hdd(daily, fit), out / "a4_load_vs_hdd.png")
    logger.info("A4 wrote artifacts under %s produced_by=%s", out, PRODUCED_BY)
