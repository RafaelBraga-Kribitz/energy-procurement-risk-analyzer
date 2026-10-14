"""A4 — Weather and system-load sensitivity (SPEC-04 A4, deliberately small).

Daily AT system load (mean MW) against HDD_18 with month fixed effects and a
weekend dummy, OLS with HC1 robust standard errors. Degree-days come from the
marts (``fct_price_daily`` ← ``dim_calendar``) and are never recomputed here
(SPEC-04 §5). Artifacts: ``a4_load_vs_hdd.png``, ``a4_load_weather.md``.

Implements: AN-401, AN-402.
"""

from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf

from epra.analytics._shared import analytics_dir, query, write_markdown
from epra.common.config import Settings
from epra.common.provenance import is_fixture_run
from epra.report.figure import new_figure, save_figure
from epra.report.format import md_table
from epra.report.style import OKABE_ITO

DAILY_LOAD_SQL = """
with daily_load as (
    select
        fph.date_local,
        avg(fph.load_at_mw) as load_mean_mw,
        bool_or(fph.is_weekend or fph.is_holiday_at) as is_weekend_or_holiday,
        min(fph.month_local) as month_local
    from marts.fct_price_hourly as fph
    where fph.load_at_mw is not null
    group by fph.date_local
)

select
    daily_load.date_local,
    daily_load.load_mean_mw,
    daily_load.is_weekend_or_holiday,
    daily_load.month_local,
    fpd.hdd_18
from daily_load
inner join marts.fct_price_daily as fpd
    on daily_load.date_local = fpd.date_local
where fpd.hdd_18 is not null
order by daily_load.date_local
"""


def fit(daily: pd.DataFrame) -> object:
    """OLS load ~ HDD_18 + weekend + month FE, HC1 robust SE (AN-401)."""
    data = daily.assign(weekend=daily["is_weekend_or_holiday"].astype(int))
    model = smf.ols("load_mean_mw ~ hdd_18 + weekend + C(month_local)", data=data)
    return model.fit(cov_type="HC1")


def _chart(daily: pd.DataFrame, slope: float, settings: Settings) -> None:
    fig, ax = new_figure()
    for flag, color, label in (
        (False, OKABE_ITO["blue"], "Working day"),
        (True, OKABE_ITO["orange"], "Weekend / holiday"),
    ):
        part = daily[daily["is_weekend_or_holiday"] == flag]
        ax.scatter(part["hdd_18"], part["load_mean_mw"], s=6, alpha=0.4, color=color, label=label)
    ax.set_xlabel("Heating degree days, base 18 °C (K·day)")
    ax.set_ylabel("AT system load, daily mean (MW)")
    ax.legend(frameon=False, markerscale=3)
    save_figure(
        fig,
        analytics_dir(settings) / "a4_load_vs_hdd.png",
        title=f"Each extra heating degree day adds about {slope:.0f} MW of Austrian system load",
        subtitle="Daily mean AT load vs HDD_18 (Graz); slope from OLS with month fixed effects",
        fixture=is_fixture_run(settings),
        source="Source: ENTSO-E Transparency / GeoSphere Austria / own calculations",
    )


def interpretation(slope: float, ci: tuple[float, float], weekend: float) -> str:
    """AN-402 paragraph; states that the reference consumer is weather-invariant."""
    return (
        "## Interpretation\n\n"
        f"Holding month and day type fixed, one additional heating degree day raises the "
        f"Austrian system load by about {slope:.0f} MW (95% interval {ci[0]:.0f} to "
        f"{ci[1]:.0f} MW, HC1 robust), while weekends and holidays sit about "
        f"{abs(weekend):.0f} MW {'below' if weekend < 0 else 'above'} working days. This is a "
        f"property of the SYSTEM: cold spells raise demand across the country and tend to "
        f"lift prices in exactly the winter hours a manufacturer cannot avoid. It is not a "
        f"property of the reference consumer, whose load profile is weather-invariant by "
        f"construction (SPEC-03 uses calendar rules and fixed seasonal factors only), so "
        f"temperature reaches the procurement result only through the price, never through "
        f"the plant's own volume. Reviewers should not read the A4 slope as a statement "
        f"about StyriaMetal's consumption."
    )


def run(settings: Settings) -> pd.DataFrame:
    """Produce ``a4_load_vs_hdd.png`` + ``a4_load_weather.md`` from marts.

    Implements: AN-401, AN-402.
    """
    daily = query(settings, DAILY_LOAD_SQL)
    result = fit(daily)
    params = result.params  # type: ignore[attr-defined]
    conf = result.conf_int()  # type: ignore[attr-defined]
    slope = float(params["hdd_18"])
    ci = (float(conf.loc["hdd_18", 0]), float(conf.loc["hdd_18", 1]))
    _chart(daily, slope, settings)
    coef = pd.DataFrame(
        {
            "term": ["hdd_18 (MW per K·day)", "weekend (MW)"],
            "estimate": [slope, float(params["weekend"])],
            "ci_low": [ci[0], float(conf.loc["weekend", 0])],
            "ci_high": [ci[1], float(conf.loc["weekend", 1])],
        }
    )
    write_markdown(
        settings,
        "a4_load_weather.md",
        "A4 — Weather and system-load sensitivity",
        [
            f"OLS of daily mean AT load (MW) on HDD_18, a weekend/holiday dummy and month fixed "
            f"effects; HC1 robust standard errors; n = {int(result.nobs)} days, "  # type: ignore[attr-defined]
            f"R² = {result.rsquared:.3f}.",  # type: ignore[attr-defined]
            "",
            md_table(coef),
            "",
            interpretation(slope, ci, float(params["weekend"])),
        ],
    )
    return coef
