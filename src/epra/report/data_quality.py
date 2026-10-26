"""Data-quality report — the visible Datenqualität layer (ADR-020 §3).

Turns the ``fct_data_quality_monthly`` mart and the last dbt run into
``reports/data_quality/DATA_QUALITY.md`` (+ ``data_quality_annual.csv`` and
``dq_coverage.png``): coverage per year, DST 23/25-hour days, PT15M vs PT60M
resolution mix, negative prices, weather and ÖSPI completeness, freshness
against the DM-066 40-day rule, and the dbt test tally. Every figure is
computed from the warehouse; nothing is typed in.

Implements: ADR-020 §3, supports DM-050, DM-066, ING-080, ING-083, R-2.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import bk_theme as bk
import pandas as pd

from epra.common.config import Settings, resolve_repo_path
from epra.common.db import read_sql
from epra.common.provenance import banner_lines, is_fixture_run
from epra.report.figure import new_figure, save_figure
from epra.report.format import md_table
from epra.warehouse.report import DBT_RUN_RESULTS, load_run_results

ANNUAL_DQ_SQL = """
select
    dq.year_local as year,
    sum(dq.expected_hours) as expected_hours,
    sum(dq.priced_hours_at) as priced_hours_at,
    round(100.0 * sum(dq.priced_hours_at) / sum(dq.expected_hours), 2) as coverage_at_pct,
    round(100.0 * sum(dq.priced_hours_delu) / sum(dq.expected_hours), 2) as coverage_delu_pct,
    round(100.0 * sum(dq.load_hours) / sum(dq.expected_hours), 2) as coverage_load_pct,
    round(100.0 * sum(dq.weather_days) / sum(dq.days_in_month), 2) as coverage_weather_pct,
    sum(dq.n_dst_days) as dst_days,
    sum(dq.n_hours_from_pt15m) as hours_from_pt15m,
    sum(dq.n_negative_hours) as negative_hours,
    count(*) filter (where dq.has_oespi) as oespi_months,
    count(*) as months
from marts.fct_data_quality_monthly as dq
group by dq.year_local
order by dq.year_local
"""

MONTHLY_DQ_SQL = """
select
    dq.year_local,
    dq.month_local,
    dq.coverage_at_pct,
    dq.resolution,
    dq.n_hours_from_pt15m,
    dq.priced_hours_at
from marts.fct_data_quality_monthly as dq
order by dq.year_local, dq.month_local
"""

FRESHNESS_LIMIT_DAYS = 40  # DM-066
TRANSFORM_RESULTS = "run_results_transform.json"


def dq_dir(settings: Settings) -> Path:
    """``reports/data_quality/``."""
    path = resolve_repo_path(settings.paths.reports) / "data_quality"
    path.mkdir(parents=True, exist_ok=True)
    return path


def freshness_days(monthly: pd.DataFrame, today: date) -> int:
    """Days between the end of the last priced month and ``today`` (DM-066)."""
    last = monthly.iloc[-1]
    month_end = pd.Timestamp(
        int(last["year_local"]), int(last["month_local"]), 1
    ) + pd.offsets.MonthEnd(0)
    return int((pd.Timestamp(today) - month_end).days)


def kpis(annual: pd.DataFrame, monthly: pd.DataFrame, today: date) -> pd.DataFrame:
    """Headline Kennzahlen for the report and the dashboard card row."""
    last = monthly.iloc[-1]
    fresh = freshness_days(monthly, today)
    rows = [
        (
            "Priced window",
            f"{int(monthly.iloc[0]['year_local'])}-"
            f"{int(monthly.iloc[0]['month_local']):02d} → {int(last['year_local'])}-"
            f"{int(last['month_local']):02d}",
        ),
        (
            "AT price coverage, all months",
            f"{100 * annual['priced_hours_at'].sum() / annual['expected_hours'].sum():.2f}%",
        ),
        ("Months below 100% AT coverage", str(int((monthly["coverage_at_pct"] < 100).sum()))),
        ("DST transition days (23/25 h)", str(int(annual["dst_days"].sum()))),
        ("Months on 15-minute MTU (PT15M)", str(int((monthly["resolution"] != "PT60M").sum()))),
        ("Negative-price hours, all years", str(int(annual["negative_hours"].sum()))),
        (
            "Days since last data month ended",
            f"{fresh} ({'OK' if fresh < FRESHNESS_LIMIT_DAYS else 'STALE'}, DM-066 < "
            f"{FRESHNESS_LIMIT_DAYS})",
        ),
    ]
    return pd.DataFrame(rows, columns=["indicator", "value"])


def _chart(monthly: pd.DataFrame, settings: Settings) -> None:
    x = pd.to_datetime(
        [
            f"{y}-{m:02d}-01"
            for y, m in zip(monthly["year_local"], monthly["month_local"], strict=True)
        ]
    )
    pt15m_share = 100 * monthly["n_hours_from_pt15m"] / monthly["priced_hours_at"].clip(lower=1)
    fig, ax = new_figure()
    ax.bar(
        x,
        pt15m_share,
        width=25,
        color=bk.neutral_ramp(3)[2],
        label="Share of hours built from 15-min quarters (PT15M)",
    )
    ax.plot(x, monthly["coverage_at_pct"], color=bk.c("hl"), lw=2, label="AT price coverage")
    ax.set_ylim(0, 105)
    ax.set_xlabel("Month")
    ax.set_ylabel("Percent of hours in month (%)")
    ax.legend(frameon=False, loc="lower left")
    low = int((monthly["coverage_at_pct"] < 100).sum())
    save_figure(
        fig,
        dq_dir(settings) / "dq_coverage.png",
        title=f"Price coverage per month: {len(monthly) - low} of {len(monthly)} months complete",
        subtitle="Hourly AT day-ahead prices present vs calendar hours (DST-aware), and the "
        "move to the 15-minute market time unit",
        fixture=is_fixture_run(settings),
    )


def dbt_tally() -> str:
    """Both dbt invocations of ``make all``: the warehouse build (``make transform``,
    saved as ``run_results_transform.json``) and the cost-mart build in ``make simulate``
    (the latest ``run_results.json``)."""
    sections = []
    for label, path in (
        ("Warehouse build (`make transform`)", DBT_RUN_RESULTS.with_name(TRANSFORM_RESULTS)),
        ("Cost-mart build (`make simulate`)", DBT_RUN_RESULTS),
    ):
        summary = load_run_results(resolve_repo_path(path))
        body = summary.render_markdown() if summary else "run_results not found — run dbt."
        sections.append(f"**{label}**\n\n{body}")
    return "\n\n".join(sections)


def run(settings: Settings, today: date | None = None) -> Path:
    """Write the data-quality report, CSV and chart; returns the markdown path.

    Implements: ADR-020 §3.
    """
    annual = read_sql(settings, ANNUAL_DQ_SQL)
    monthly = read_sql(settings, MONTHLY_DQ_SQL)
    out = dq_dir(settings)
    annual.to_csv(out / "data_quality_annual.csv", index=False)
    _chart(monthly, settings)
    dbt_text = dbt_tally()
    gaps = monthly[monthly["coverage_at_pct"] < 100]
    lines = [
        "# Data quality report (Datenqualität)",
        "",
        *banner_lines(settings),
        "Generated by `make report` from `marts.fct_data_quality_monthly` (SQL, dbt-tested) "
        "and the last dbt run. Gates behind these numbers: SPEC-01 ingestion gates "
        "(`reports/ingestion/`), SPEC-02 dbt tests, AN-304 and ST-602 (see the analytics "
        "and strategy reports).",
        "",
        "## Kennzahlen",
        "",
        md_table(kpis(annual, monthly, today or date.today())),
        "",
        "## Coverage and cleanliness per year",
        "",
        md_table(annual.astype({c: float for c in annual.columns if "pct" in c}), ".2f"),
        "",
        "![Coverage chart](dq_coverage.png)",
        "",
        "## Months below full AT price coverage",
        "",
        md_table(gaps) if len(gaps) else "None — every priced month is complete.",
        "",
        "## dbt tests",
        "",
        dbt_text,
        "",
        "## How to read this",
        "",
        "Coverage compares priced hours with the DST-aware calendar (a March month has one "
        "hour less, an October month one more), so 100% means no hour is missing. Hours "
        "after the 15-minute switch are the mean of four quarter-hour prices, never their "
        "sum. Negative-price hours are real market outcomes, not errors, and are kept. Any "
        "gap stays NULL: no price is ever invented to fill it (Charter P-1).",
        "",
    ]
    path = out / "DATA_QUALITY.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
