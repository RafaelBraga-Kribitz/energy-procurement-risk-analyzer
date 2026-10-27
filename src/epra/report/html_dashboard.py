"""Static HTML twin of the Power BI report: one self-contained file (ADR-022).

Reads the SAME ``exports/*.csv`` the PBIP semantic model loads (DM-070) and writes
``dashboards/html/index.html``: the five SPEC-06 §4 pages as accessible tabs, KPI
cards, inline-SVG charts drawn by vanilla JS from embedded JSON, a data table under
every chart, the RP-702 source note and epistemic tag on every page, and the
FIXTURE banner whenever ``provenance.csv`` says ``is_fixture`` (ADR-018). No CDN,
no fonts, no network, no backend (Charter O-4: a static file, not an app).

Determinism (A-4): the output depends only on the CSVs; there is no build
timestamp (the only dates shown are read from ``provenance.csv``), JSON keys are
sorted and floats rounded, so two builds on the same exports are byte-identical.

Headline cards read ``ssot.csv`` only (A-6). Chart values are aggregated from the
marts the SSOT was computed from; tests check both agree.

Implements: ADR-022, RP-401..RP-405 (HTML twin), RP-702, RP-703, RP-704, RP-705.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bk_theme as bk
import pandas as pd

from epra.common.config import load_settings, resolve_repo_path
from epra.report import dashboard_pages as dp
from epra.report.format import format_eur, format_eur_millions, format_pct
from epra.report.style import strategy_colors

ASSETS = Path(__file__).with_name("html_assets")
DEFAULT_OUT = Path("dashboards") / "html" / "index.html"
HIST_BIN_EUR = 100_000.0  # RP-404 histogram bin: 0.1 M EUR
VARIANT_LABELS = {"unconditional": "Unconditional pool", "no_crisis": "No-crisis pool"}
#: bk design-system roles exposed to the page as CSS custom properties.
CSS_ROLES = (
    "surface",
    "surface-2",
    "surface-3",
    "ink",
    "ink-2",
    "mid",
    "rule-c",
    "hl",
    "sc-ac",
    "var-pos",
    "var-neg",
    "var-pos-tint",
    "var-neg-tint",
    "on-accent",
)


@dataclass(frozen=True)
class Exports:
    """The export CSVs the twin reads (a subset of DM-070; same files as the PBIP).

    Implements: DM-070 (consumer side).
    """

    cost_monthly: pd.DataFrame
    annual: pd.DataFrame
    forward: pd.DataFrame
    paths: pd.DataFrame
    price_monthly: pd.DataFrame
    spread_monthly: pd.DataFrame
    dq_monthly: pd.DataFrame
    dim_strategy: pd.DataFrame
    ssot: dict[str, str]
    provenance: dict[str, str]


def load_exports(exports_dir: Path) -> Exports:
    """Read the export CSVs; ``ssot``/``provenance`` as text, exactly as written.

    Implements: DM-070, A-6.
    """

    def read(name: str) -> pd.DataFrame:
        return pd.read_csv(exports_dir / f"{name}.csv")

    ssot = pd.read_csv(exports_dir / "ssot.csv", dtype=str, keep_default_na=False)
    prov = pd.read_csv(exports_dir / "provenance.csv", dtype=str, keep_default_na=False)
    return Exports(
        cost_monthly=read("procurement_cost_monthly"),
        annual=read("strategy_annual_summary"),
        forward=read("forward_risk_summary"),
        paths=read("forward_paths"),
        price_monthly=read("price_monthly"),
        spread_monthly=read("spread_monthly"),
        dq_monthly=read("data_quality_monthly"),
        dim_strategy=read("dim_strategy").sort_values("sort_order"),
        ssot=dict(zip(ssot["key"], ssot["value"], strict=True)),
        provenance={str(k): str(v) for k, v in prov.iloc[0].items()},
    )


def is_fixture(ex: Exports) -> bool:
    """True when the exports come from the synthetic CI fixture (ADR-018)."""
    return str(ex.provenance.get("is_fixture", "")).strip().lower() == "true"


def _month_key(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["year_local"].astype(int).map("{:04d}".format).astype(str)
        + "-"
        + frame["month_local"].astype(int).map("{:02d}".format).astype(str)
    )


def _r(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def wrong_strategy_by_year(ex: Exports) -> list[dict[str, Any]]:
    """Per year: dearest minus cheapest strategy's annual cost (the RP-401 bars).

    Same definition as the ``Wrong Strategy Cost EUR`` measure; equals SSOT
    ``wrong_strategy_cost_<year>`` (tested).

    Implements: RP-201, RP-401.
    """
    annual = ex.cost_monthly.groupby(["year_local", "strategy_id"])["cost_eur"].sum()
    rows = []
    for year, costs in annual.groupby(level=0):
        by_id = costs.droplevel(0)
        rows.append(
            {
                "year": int(str(year)),
                "gap": _r(by_id.max() - by_id.min()),
                "worst": str(by_id.idxmax()),
                "best": str(by_id.idxmin()),
            }
        )
    return rows


def cost_matrix(ex: Exports) -> dict[str, Any]:
    """Strategy × year: cost (EUR), unit cost (EUR/MWh) and rank (RP-403 matrix).

    Implements: RP-403.
    """
    grouped = ex.cost_monthly.groupby(["strategy_id", "year_local"])[["cost_eur", "volume_mwh"]]
    sums = grouped.sum()
    rank = ex.annual.set_index(["strategy_id", "year"])["rank"]
    years = sorted(int(y) for y in ex.cost_monthly["year_local"].unique())
    out: dict[str, Any] = {"years": years, "cost": {}, "unit": {}, "rank": {}, "total": {}}
    for sid in ex.dim_strategy["strategy_id"]:
        cost, vol = sums.loc[sid, "cost_eur"], sums.loc[sid, "volume_mwh"]
        out["cost"][sid] = [_r(cost.loc[y]) for y in years]
        out["unit"][sid] = [_r(cost.loc[y] / vol.loc[y], 4) for y in years]
        out["rank"][sid] = [int(rank.loc[(sid, y)]) for y in years]
        out["total"][sid] = {"cost": _r(cost.sum()), "unit": _r(cost.sum() / vol.sum(), 4)}
    return out


def cumulative_cost(ex: Exports) -> dict[str, Any]:
    """Month-by-month running cost per strategy (RP-403 cumulative line).

    Implements: RP-403.
    """
    frame = ex.cost_monthly.assign(month=_month_key(ex.cost_monthly))
    wide = frame.pivot_table(index="month", columns="strategy_id", values="cost_eur").sort_index()
    cum = wide.cumsum()
    return {
        "months": list(cum.index),
        "series": {sid: [_r(v) for v in cum[sid]] for sid in ex.dim_strategy["strategy_id"]},
    }


def market_data(ex: Exports) -> dict[str, Any]:
    """Monthly base/peak price, AT−DE spread and negative hours per year (RP-402).

    Implements: RP-402.
    """
    pm = ex.price_monthly.assign(month=_month_key(ex.price_monthly)).sort_values("month")
    sp = ex.spread_monthly.assign(month=_month_key(ex.spread_monthly)).set_index("month")
    neg = pm.groupby("year_local")["n_negative_hours"].agg(["sum", "count"])

    def series(values: pd.Series) -> list[float | None]:
        return [None if pd.isna(v) else _r(v, 4) for v in values]

    return {
        "months": list(pm["month"]),
        "base": series(pm["price_base_eur_mwh"]),
        "peak": series(pm["price_peak_eur_mwh"]),
        "spread": series(sp.reindex(pm["month"])["spread_mean_eur_mwh"]),
        "neg_years": [int(y) for y in neg.index],
        "neg_hours": [int(v) for v in neg["sum"]],
        "neg_partial": [bool(n < 12) for n in neg["count"]],
    }


def risk_data(ex: Exports) -> dict[str, Any]:
    """Per variant: percentiles per strategy and 0.1 M EUR path histograms (RP-404).

    Implements: RP-404, ST-404 (read side).
    """
    out: dict[str, Any] = {}
    for variant, frame in ex.forward.groupby("variant"):
        stats = {
            row.strategy_id: {
                k: _r(getattr(row, k)) for k in ("mean", "p5", "p50", "p95", "cvar95")
            }
            for row in frame.itertuples()
        }
        paths = ex.paths[ex.paths["variant"] == variant]
        bins = (paths["cost_eur"] // HIST_BIN_EUR).astype(int)
        lo, hi = int(bins.min()), int(bins.max())
        hist = {
            str(sid): [int(c) for c in grp.value_counts().reindex(range(lo, hi + 1), fill_value=0)]
            for sid, grp in bins.groupby(paths["strategy_id"])
        }
        out[str(variant)] = {"stats": stats, "bin_lo": lo, "hist": hist}
    return out


def dq_data(ex: Exports) -> dict[str, Any]:
    """Monthly coverage and 15-minute share (ADR-020 §3 page 5).

    Implements: ADR-020 §3.
    """
    dq = ex.dq_monthly.assign(month=_month_key(ex.dq_monthly)).sort_values("month")
    return {
        "months": list(dq["month"]),
        "axis_min": coverage_axis_min(dq["coverage_at_pct"]),
        "coverage": [_r(v, 4) for v in dq["coverage_at_pct"]],
        "pt15m": [int(v) for v in dq["n_hours_from_pt15m"]],
    }


def coverage_axis_min(coverage: pd.Series) -> int:
    """Lower end of the zoomed coverage axis: whole percent, at most 99 (stated on the page).

    Implements: ADR-020 §3 (coverage chart), honest axis disclosure.
    """
    return int(min(99.0, float(coverage.min())) // 1)


def build_payload(ex: Exports) -> dict[str, Any]:
    """Everything the page script draws, as one JSON-serialisable dict.

    Implements: ADR-022.
    """
    strategies = [
        {"id": row.strategy_id, "label": row.strategy_label} for row in ex.dim_strategy.itertuples()
    ]
    return {
        "strategies": strategies,
        "wrong": wrong_strategy_by_year(ex),
        "matrix": cost_matrix(ex),
        "cumulative": cumulative_cost(ex),
        "market": market_data(ex),
        "risk": risk_data(ex),
        "variants": VARIANT_LABELS,
        "dq": dq_data(ex),
    }


# ----------------------------------------------------------------------------- HTML pieces


def esc(text: object) -> str:
    """HTML-escape any value for text and attribute positions."""
    return html.escape(str(text), quote=True)


def kpi(label: str, value: str, note: str, *, key: str = "", raw: str = "") -> str:
    """One KPI card; ``data-ssot-key``/``data-value`` keep the source traceable (A-6).

    Implements: RP-401, A-6.
    """
    attrs = f' data-ssot-key="{esc(key)}" data-value="{esc(raw)}"' if key else ""
    return (
        f'<div class="kpi"{attrs}><p class="kpi-label">{esc(label)}</p>'
        f'<p class="kpi-value">{esc(value)}</p><p class="kpi-note">{esc(note)}</p></div>'
    )


def data_table(
    caption: str, headers: Sequence[str], rows: Sequence[Sequence[str]], **attrs: str
) -> str:
    """A ``<details>`` data table: the screen-reader and no-hover twin of a chart.

    Implements: ADR-022 (table view under every chart).
    """
    extra = "".join(f' {k.replace("_", "-")}="{esc(v)}"' for k, v in attrs.items())
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows)
    return (
        f'<details class="data"{extra}><summary>Data table: {esc(caption)}</summary>'
        f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></details>"
    )


def chart(chart_id: str, title: str, unit: str, table: str, *, wide: bool = False) -> str:
    """A chart figure: title, unit line, the JS-drawn plot host and its data table.

    Implements: RP-702 (axis units stated), ADR-022.
    """
    cls = "card chart wide" if wide else "card chart"
    return (
        f'<figure class="{cls}"><figcaption><h3>{esc(title)}</h3>'
        f'<p class="unit">{esc(unit)}</p></figcaption>'
        f'<div class="legend" id="legend-{chart_id}"></div>'
        f'<div class="plot" id="plot-{chart_id}" data-chart="{chart_id}"></div>{table}</figure>'
    )


def page_shell(page: dp.DashboardPage, n_paths: int, body: str, active: bool) -> str:
    """Tab panel with heading, German subtitle (RP-405) and RP-702 footer.

    Implements: RP-405, RP-702.
    """
    hidden = "" if active else " hidden"
    return (
        f'<section class="page" role="tabpanel" id="panel-{page.page_id}" '
        f'aria-labelledby="tab-{page.page_id}" tabindex="0"{hidden}>'
        f'<h2 class="page-title">{esc(page.heading)}</h2>'
        f'<p class="subtitle" lang="de">{esc(dp.subtitle(page, n_paths))}</p>{body}'
        f'<footer class="page-foot"><span>{esc(dp.SOURCE_NOTE)}</span>'
        f'<span class="tag">{esc(page.epistemic)}</span></footer></section>'
    )


def runner_up(ssot: dict[str, str], prefix: str, ids: Sequence[str]) -> tuple[str, float]:
    """Second-lowest strategy of an SSOT row family and its margin over the lowest.

    Shows how close a "best" pick is (e.g. within Monte-Carlo noise) instead of
    presenting a ranking without its margin. Reads SSOT rows only (A-6).

    Implements: A-6, ST-404 (honest ranking display).
    """
    values = sorted((float(ssot[f"{prefix}{sid}"]), sid) for sid in ids if f"{prefix}{sid}" in ssot)
    if len(values) < 2:
        return "", 0.0
    return values[1][1], values[1][0] - values[0][0]


def _margin_note(labels: dict[str, str], ssot: dict[str, str], prefix: str, what: str) -> str:
    second, margin = runner_up(ssot, prefix, list(labels))
    if not second:
        return ""
    return f"{format_eur(margin)} {what} than {labels[second]}"


def _label(ex: Exports) -> dict[str, str]:
    return dict(zip(ex.dim_strategy["strategy_id"], ex.dim_strategy["strategy_label"], strict=True))


def headline_body(ex: Exports, payload: dict[str, Any]) -> str:
    """Page 1: four SSOT cards, wrong-strategy cost per year, annual cost matrix.

    Implements: RP-401.
    """
    s, labels = ex.ssot, _label(ex)
    best = s["best_strategy_5yr"]
    cards = "".join(
        [
            kpi(
                "Wrong strategy cost 2021–2025",
                format_eur_millions(float(s["wrong_strategy_cost_total"])),
                "Dearest minus cheapest strategy, summed per year · CALIBRATED",
                key="wrong_strategy_cost_total",
                raw=s["wrong_strategy_cost_total"],
            ),
            kpi(
                "Cheapest strategy 2021–2025",
                labels.get(best, best),
                f"{format_eur_millions(float(s[f'cost5yr_{best}']))} over five years, "
                f"{_margin_note(labels, s, 'cost5yr_', 'less')} · CALIBRATED",
                key="best_strategy_5yr",
                raw=best,
            ),
            kpi(
                "P95 next 12 months · full spot",
                format_eur_millions(float(s["p95_next12m_S1"])),
                "Bad-case cost, unconditional pool · SIMULATED",
                key="p95_next12m_S1",
                raw=s["p95_next12m_S1"],
            ),
            kpi(
                "P95 next 12 months · fixed annual",
                format_eur_millions(float(s["p95_next12m_S3"])),
                "Bad-case cost, unconditional pool · SIMULATED",
                key="p95_next12m_S3",
                raw=s["p95_next12m_S3"],
            ),
        ]
    )
    wrong_rows = [
        [str(r["year"]), format_eur_millions(r["gap"]), labels[r["worst"]], labels[r["best"]]]
        for r in payload["wrong"]
    ]
    wrong = chart(
        "wrong",
        "Cost of the wrong strategy per year",
        "EUR million · dearest minus cheapest strategy; label = the dearest",
        data_table(
            "cost of the wrong strategy per year",
            ["Year", "Gap", "Dearest strategy", "Cheapest strategy"],
            wrong_rows,
        ),
    )
    matrix = (
        '<figure class="card chart"><figcaption><h3>Annual cost by strategy</h3>'
        '<p class="unit">EUR million · ▼ cheapest and ▲ dearest of each year</p></figcaption>'
        f"{matrix_table(payload['matrix'], labels, 'cost', swatches=False)}</figure>"
    )
    return f'<div class="kpis accent">{cards}</div><div class="grid two lead">{wrong}{matrix}</div>'


def matrix_table(
    m: dict[str, Any], labels: dict[str, str], metric: str, *, swatches: bool = True
) -> str:
    """Strategy × year table; cheapest/dearest cell per year marked in text AND tint.

    Implements: RP-401, RP-403 (conditional formatting, never colour alone).
    """
    years, values = m["years"], m[metric]
    head = "".join(f'<th scope="col">{y}</th>' for y in years)
    head += f'<th scope="col">{years[0]}–{years[-1]}</th>'
    body = []
    for sid, vals in values.items():
        cells = []
        for j, v in enumerate(vals):
            column = [values[k][j] for k in values]
            mark, cls = "", ""
            if v == min(column):
                mark, cls = ' <span class="mk">▼</span><span class="sr"> cheapest</span>', "lo"
            elif v == max(column):
                mark, cls = ' <span class="mk">▲</span><span class="sr"> dearest</span>', "hi"
            text = format_eur_millions(v) if metric == "cost" else f"{v:,.1f}"
            if metric == "unit":
                text += f' <span class="rank">#{m["rank"][sid][j]}</span>'
            cells.append(f'<td class="{cls}">{text}{mark}</td>')
        total = m["total"][sid][metric]
        best = total == min(t[metric] for t in m["total"].values())
        text = format_eur_millions(total) if metric == "cost" else f"{total:,.1f}"
        mark = ' <span class="mk">▼</span><span class="sr"> cheapest</span>' if best else ""
        cells.append(f'<td class="tot">{text}{mark}</td>')
        swatch = f'<span class="sw" style="background:var(--s-{sid})"></span>'
        body.append(
            f'<tr><th scope="row">{swatch if swatches else ""}{esc(labels[sid])}</th>'
            f"{''.join(cells)}</tr>"
        )
    unit = "EUR million" if metric == "cost" else "EUR/MWh, #rank (1 = cheapest)"
    return (
        f'<div class="table-wrap"><table class="matrix" data-metric="{metric}">'
        f'<caption class="sr">Annual {"cost" if metric == "cost" else "unit cost and rank"} '
        f"by strategy, {unit}</caption>"
        f'<thead><tr><th scope="col">Strategy</th>{head}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def market_body(ex: Exports, payload: dict[str, Any]) -> str:
    """Page 2: year filter, base/peak price, negative hours, AT−DE spread (RP-402).

    Implements: RP-402.
    """
    mk = payload["market"]
    years = sorted({m[:4] for m in mk["months"]})
    options = '<option value="all">All years</option>' + "".join(
        f'<option value="{y}">{y}</option>' for y in years
    )
    price_rows = [
        [m, _fmt1(b), _fmt1(p), _fmt1(s)]
        for m, b, p, s in zip(mk["months"], mk["base"], mk["peak"], mk["spread"], strict=True)
    ]
    neg_rows = [
        [f"{y}{' (partial)' if part else ''}", f"{h:,d}"]
        for y, h, part in zip(mk["neg_years"], mk["neg_hours"], mk["neg_partial"], strict=True)
    ]
    partial = (
        f" · * partial year, through {ex.provenance.get('data_last_month', '')}"
        if any(mk["neg_partial"])
        else ""
    )
    prices = chart(
        "price",
        "Monthly AT day-ahead price, base and peak",
        "EUR/MWh · monthly mean",
        data_table(
            "monthly prices and spread",
            ["Month", "Base EUR/MWh", "Peak EUR/MWh", "AT − DE-LU EUR/MWh"],
            price_rows,
        ),
        wide=True,
    )
    neg = chart(
        "neg",
        "Hours with a negative price",
        f"hours per year{partial}",
        data_table("negative-price hours per year", ["Year", "Hours"], neg_rows),
    )
    spread = chart(
        "spread",
        "AT minus DE-LU day-ahead spread",
        "EUR/MWh · above 0 = Austria dearer",
        '<p class="note">The values are in the price table above.</p>',
    )
    controls = (
        '<div class="controls"><label for="market-year">Year</label>'
        f'<select id="market-year">{options}</select></div>'
    )
    return f'{controls}<div class="grid">{prices}</div><div class="grid two">{neg}{spread}</div>'


def _month_name(month: str) -> str:
    """``2021-01`` → ``January 2021`` (English, RP-705)."""
    return pd.Timestamp(f"{month}-01").strftime("%B %Y")


def _fmt1(value: float | None) -> str:
    return "–" if value is None else f"{value:,.1f}"


def strategies_body(ex: Exports, payload: dict[str, Any]) -> str:
    """Page 3: cost / unit-cost matrix toggle and cumulative cost lines (RP-403).

    Implements: RP-403.
    """
    labels, m = _label(ex), payload["matrix"]
    toggle = (
        '<div class="controls" role="group" aria-label="Matrix metric">'
        '<button type="button" class="seg" data-metric="cost" aria-pressed="true">'
        "Total cost</button>"
        '<button type="button" class="seg" data-metric="unit" aria-pressed="false">'
        "Unit cost and rank</button></div>"
    )
    matrix = (
        '<figure class="card chart wide"><figcaption><h3>Annual cost by strategy</h3>'
        '<p class="unit">▼ cheapest and ▲ dearest of each year</p></figcaption>'
        f"{matrix_table(m, labels, 'cost')}{matrix_table(m, labels, 'unit')}</figure>"
    )
    cum = payload["cumulative"]
    last = {sid: vals[-1] for sid, vals in cum["series"].items()}
    rows = [[labels[sid], format_eur_millions(v)] for sid, v in last.items()]
    cumulative = chart(
        "cum",
        f"Cumulative cost since {_month_name(cum['months'][0])}",
        "EUR million · running total",
        data_table(
            f"cumulative cost at {cum['months'][-1]}", ["Strategy", "Cumulative cost"], rows
        ),
        wide=True,
    )
    return f'{toggle}<div class="grid">{matrix}{cumulative}</div>'


def risk_body(ex: Exports, payload: dict[str, Any]) -> str:
    """Page 4: variant switch, Q4 cards, P5/P50/P95 ranges, mean vs P95, histograms.

    Implements: RP-404, ST-404 (read side).
    """
    s, labels = ex.ssot, _label(ex)
    radios = "".join(
        f'<button type="button" class="seg" data-variant="{v}" '
        f'aria-pressed="{"true" if v == "unconditional" else "false"}">{esc(t)}</button>'
        for v, t in VARIANT_LABELS.items()
        if v in payload["risk"]
    )
    cards = "".join(
        [
            kpi(
                "Cost-minimising choice",
                labels.get(s["q4_cost_min_strategy"], ""),
                f"Lowest mean cost, {_margin_note(labels, s, 'mean_next12m_', 'lower')}; "
                "unconditional pool · SIMULATED",
                key="q4_cost_min_strategy",
                raw=s["q4_cost_min_strategy"],
            ),
            kpi(
                "Risk-averse choice",
                labels.get(s["q4_risk_averse_strategy"], ""),
                f"Lowest P95 cost, {_margin_note(labels, s, 'p95_next12m_', 'lower')}; "
                "unconditional pool · SIMULATED",
                key="q4_risk_averse_strategy",
                raw=s["q4_risk_averse_strategy"],
            ),
            kpi(
                "Risk premium of the hedge",
                format_eur(float(s["q4_risk_premium_eur"])),
                "Extra expected cost of the risk-averse choice, unconditional pool · SIMULATED",
                key="q4_risk_premium_eur",
                raw=s["q4_risk_premium_eur"],
            ),
            kpi(
                "P95 reduction of the hedge",
                format_eur(float(s["q4_p95_reduction_eur"])),
                "Lower P95 cost of the risk-averse choice, unconditional pool · SIMULATED",
                key="q4_p95_reduction_eur",
                raw=s["q4_p95_reduction_eur"],
            ),
        ]
    )
    tables = "".join(
        data_table(
            f"next-12-month cost, {VARIANT_LABELS.get(v, v).lower()}",
            ["Strategy", "Mean", "P5", "P50", "P95", "CVaR95"],
            [
                [
                    labels[sid],
                    *[format_eur_millions(st[k]) for k in ("mean", "p5", "p50", "p95", "cvar95")],
                ]
                for sid, st in sorted(r["stats"].items(), key=lambda kv: list(labels).index(kv[0]))
            ],
            data_variant=v,
        )
        for v, r in payload["risk"].items()
    )
    ranges = chart(
        "range",
        "Next-12-month cost: P5, P50 and P95",
        "EUR million · line = P5 to P95, dot = P50 (median)",
        tables,
    )
    scatter = chart(
        "scatter",
        "Expected cost vs bad case",
        "EUR million · mean (x) vs P95 (y); lower left is cheaper and safer",
        '<p class="note">The values are in the percentile table on this page.</p>',
    )
    hist = (
        '<figure class="card chart wide"><figcaption><h3>Simulated 12-month cost per path</h3>'
        f'<p class="unit">paths per {format_eur_millions(HIST_BIN_EUR, 1)} bin · one panel per '
        'strategy · line = P95</p></figcaption><div class="multiples" id="plot-hist"></div>'
        '<p class="note">Path counts per bin are summarised by the percentiles in the table '
        "above.</p></figure>"
    )
    controls = f'<div class="controls" role="group" aria-label="Bootstrap pool">{radios}</div>'
    return (
        f'{controls}<div class="kpis">{cards}</div><div class="grid two">{ranges}{scatter}</div>'
        f'<div class="grid">{hist}</div>'
    )


def dq_body(ex: Exports, payload: dict[str, Any]) -> str:
    """Page 5: five quality cards, coverage and 15-minute charts, gap table (ADR-020 §3).

    Implements: ADR-020 §3.
    """
    dq = ex.dq_monthly
    coverage = dq["priced_hours_at"].sum() / dq["expected_hours"].sum()
    below = dq[dq["coverage_at_pct"] < 100]
    missing = int((~dq["has_oespi"].astype(str).str.lower().eq("true")).sum())
    cards = "".join(
        [
            kpi("AT price coverage", format_pct(coverage, 2), "Priced of expected hours"),
            kpi("Months below full coverage", f"{len(below):,d}", "0 = every month complete"),
            kpi("DST transition days", f"{int(dq['n_dst_days'].sum()):,d}", "23- and 25-hour days"),
            kpi(
                "Hours from 15-min quarters",
                f"{int(dq['n_hours_from_pt15m'].sum()):,d}",
                "Hourly price = mean of four quarter-hours",
            ),
            kpi("Months without ÖSPI", f"{missing:,d}", "Months with no ÖSPI value in the data"),
        ]
    )
    d = payload["dq"]
    rows = [
        [m, f"{c:,.2f}", f"{q:,d}"]
        for m, c, q in zip(d["months"], d["coverage"], d["pt15m"], strict=True)
    ]
    cov = chart(
        "cov",
        "Monthly AT price coverage",
        f"% of expected hours · axis zoomed, starts at {d['axis_min']} %",
        data_table(
            "monthly coverage and 15-minute hours",
            ["Month", "Coverage %", "Hours from 15-min"],
            rows,
        ),
        wide=True,
    )
    pt = chart(
        "pt15",
        "Hours built from 15-minute quarters",
        "hours per month",
        '<p class="note">The values are in the coverage table above.</p>',
        wide=True,
    )
    gap_rows = [
        [month, f"{cov:,.2f}", str(res)]
        for month, cov, res in zip(
            _month_key(below), below["coverage_at_pct"], below["resolution"], strict=True
        )
    ]
    gap = (
        '<figure class="card chart wide"><figcaption><h3>Months below full price coverage</h3>'
        '<p class="unit">empty = every month complete</p></figcaption>'
        + (
            '<p class="empty">No month below 100 % coverage.</p>'
            if not gap_rows
            else data_table(
                "months below full coverage",
                ["Month", "Coverage %", "Resolution"],
                gap_rows,
                open="",
            )
        )
        + "</figure>"
    )
    return f'<div class="kpis five">{cards}</div><div class="grid">{cov}{pt}{gap}</div>'


BODIES = {
    "headline": headline_body,
    "market": market_body,
    "strategies": strategies_body,
    "risk": risk_body,
    "data-quality": dq_body,
}


def css_tokens() -> str:
    """Design-system tokens (light, dark, strategy colours) as CSS custom properties.

    Implements: RP-704 (one colour definition), ADR-021, ADR-022.
    """

    def block(mode: str) -> str:
        roles = "".join(f"--{r}:{bk.COLOR[mode][r]};" for r in CSS_ROLES)
        strat = "".join(f"--s-{sid}:{hexv};" for sid, hexv in strategy_colors(mode).items())
        return roles + strat

    light, dark = block("light"), block("dark")
    return (
        f":root{{color-scheme:light;{light}}}"
        "@media (prefers-color-scheme:dark){"
        f':root:not([data-theme="light"]){{color-scheme:dark;{dark}}}}}'
        f':root[data-theme="dark"]{{color-scheme:dark;{dark}}}'
    )


def render_html(ex: Exports) -> str:
    """The complete, self-contained page (no external resource of any kind).

    Implements: ADR-022, RP-401..RP-405, ADR-018 banner.
    """
    payload = build_payload(ex)
    n_paths = int(float(ex.ssot["forward_n_paths"]))
    fixture = is_fixture(ex)
    tabs = "".join(
        f'<button type="button" role="tab" id="tab-{p.page_id}" aria-controls="panel-{p.page_id}" '
        f'aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}">'
        f"{esc(p.title)}</button>"
        for i, p in enumerate(dp.PAGES)
    )
    panels = "".join(
        page_shell(p, n_paths, BODIES[p.page_id](ex, payload), i == 0)
        for i, p in enumerate(dp.PAGES)
    )
    banner = (
        f'<div class="banner" role="note"><strong>▲ {esc(dp.FIXTURE_BANNER)}</strong> '
        "Every number on this page exercises the pipeline only. Rebuild after "
        "<code>make real-run</code>.</div>"
        if fixture
        else ""
    )
    data_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/")
    title = ("FIXTURE · " if fixture else "") + "EPRA procurement risk dashboard"
    meta = (
        f"Data through {esc(ex.provenance.get('data_last_month', ''))} · exports of "
        f"{esc(ex.provenance.get('generated_on', ''))} · the same exports/*.csv as "
        "dashboards/EPRA.pbip"
    )
    css = css_tokens() + (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    js = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="description" content="{esc(title)}: static twin of the Power BI report">'
        f"<title>{esc(title)}</title><style>{css}</style></head><body>"
        f'<a class="skip" href="#main">Skip to the dashboard</a>{banner}'
        '<header class="top"><div class="wrap"><div class="brand">'
        '<p class="eyebrow">Energy Procurement Risk Analyzer · '
        "Austrian day-ahead market (ENTSO-E)</p>"
        f'<p class="meta">{meta}</p></div>'
        '<button type="button" class="theme" id="theme" aria-label="Colour theme: automatic">'
        "Theme: auto</button></div>"
        f'<div class="wrap"><div class="tabs" role="tablist" aria-label="Dashboard pages">{tabs}'
        "</div></div></header>"
        f'<main id="main" class="wrap">{panels}</main>'
        '<div id="tip" class="tip" hidden></div>'
        '<p id="live" class="sr" aria-live="polite"></p>'
        '<noscript><p class="wrap">Charts need JavaScript; '
        "every value is in the data tables.</p></noscript>"
        f'<script type="application/json" id="epra-data">{data_json}</script>'
        f"<script>{js}</script></body></html>\n"
    )


def build(exports_dir: Path, out_path: Path) -> Path:
    """Read the exports and write the HTML twin; returns the written path.

    Implements: ADR-022.
    """
    text = render_html(load_exports(exports_dir))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return out_path


def main(argv: Sequence[str] | None = None) -> int:
    """``make dashboard-html``: exports/ → dashboards/html/index.html.

    Implements: ADR-022.
    """
    parser = argparse.ArgumentParser(description="Build the static HTML dashboard twin.")
    parser.add_argument("--exports", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    settings = load_settings()
    exports_dir = args.exports or resolve_repo_path(settings.paths.exports)
    out_path = args.out or resolve_repo_path(DEFAULT_OUT)
    if not (exports_dir / "provenance.csv").exists():
        print(f"no exports in {exports_dir}; run `make export` first", file=sys.stderr)
        return 1
    written = build(exports_dir, out_path)
    print(f"HTML dashboard -> {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
