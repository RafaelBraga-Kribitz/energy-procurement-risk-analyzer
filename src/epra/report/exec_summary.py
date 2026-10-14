"""EXEC_SUMMARY.md and the README result blocks, rendered from the SSOT (SPEC-06 §5/§6).

Numbers are read ONLY from the published ``reports/NUMERIC_SSOT.md`` and
formatted with the shared formatter, so every figure in the two documents is
an SSOT value at the rounding ``check_ssot_consistency.py`` accepts (A-6,
GV-303). The prose around them is fixed text written for a CFO / procurement
lead; the recommendation sentence is assembled from the Q4 rows so it never
contradicts the numbers.

README blocks live between ``<!-- epra:<name>:start -->`` / ``:end -->``
markers. On a fixture run (ADR-018) the README blocks carry NO numbers — only
a notice — because fixture numbers must never read as results; the
EXEC_SUMMARY keeps them under the FIXTURE banner as a format preview.

Implements: SPEC-06 §5 (structure), §6 items 2 and 5, RP-601, A-6, E-1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from epra.common.config import REPO_ROOT, Settings, load_strategy_config, resolve_repo_path
from epra.common.provenance import FIXTURE_BANNER, is_fixture_run
from epra.report.format import format_eur_millions, format_eur_mwh
from epra.report.style import LP050_CAPTION, ST502_CAPTION, STRATEGY_LABELS

SSOT_FILE = Path("reports") / "NUMERIC_SSOT.md"
README = REPO_ROOT / "README.md"
MARKER = "<!-- epra:{name}:{edge} -->"


@dataclass(frozen=True)
class Entry:
    """One SSOT row."""

    value: str
    unit: str
    tag: str


class Ssot:
    """Typed read access to the published SSOT table."""

    def __init__(self, rows: dict[str, Entry]) -> None:
        self.rows = rows

    @classmethod
    def from_markdown(cls, path: Path) -> Ssot:
        rows: dict[str, Entry] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 6 and cells[0] not in ("key", "---"):
                rows[cells[0]] = Entry(cells[1], cells[2], cells[3])
        return cls(rows)

    def num(self, key: str) -> float:
        return float(self.rows[key].value)

    def text(self, key: str) -> str:
        return self.rows[key].value

    def tag(self, key: str) -> str:
        return self.rows[key].tag

    def eur_m(self, key: str) -> str:
        """``€x.xx M`` plus the epistemic tag in parentheses (E-1)."""
        return f"{format_eur_millions(self.num(key))} ({self.tag(key)})"


def _label(sid: str) -> str:
    return STRATEGY_LABELS.get(sid, sid)


def strategy_table(ssot: Ssot, years: list[int], strategies: list[str]) -> str:
    """Annual cost matrix (EUR million) + 5-year total, from SSOT keys."""
    header = "| Strategy | " + " | ".join(str(y) for y in years) + " | 2021-2025 |"
    rule = "|---|" + "---:|" * (len(years) + 1)
    rows = [
        "| "
        + _label(s)
        + " | "
        + " | ".join(f"{ssot.num(f'cost_{s}_{y}') / 1e6:.2f}" for y in years)
        + f" | {ssot.num(f'cost5yr_{s}') / 1e6:.2f} |"
        for s in strategies
    ]
    return "\n".join([header, rule, *rows])


def forward_table(ssot: Ssot, strategies: list[str]) -> str:
    """Q3 table: mean / P5 / P50 / P95 / CVaR95 in EUR million."""
    metrics = ("mean", "p5", "p50", "p95", "cvar95")
    header = "| Strategy | Mean | P5 | P50 | P95 | CVaR95 |"
    rule = "|---|---:|---:|---:|---:|---:|"
    rows = [
        "| "
        + _label(s)
        + " | "
        + " | ".join(f"{ssot.num(f'{m}_next12m_{s}') / 1e6:.2f}" for m in metrics)
        + " |"
        for s in strategies
    ]
    return "\n".join([header, rule, *rows])


def answer(ssot: Ssot) -> str:
    """SPEC-06 §5 item 1 / README §6 item 2: the three-sentence answer."""
    best = ssot.text("best_strategy_5yr")
    cost_min = ssot.text("q4_cost_min_strategy")
    averse = ssot.text("q4_risk_averse_strategy")
    return (
        f"Buying electricity with the wrong strategy cost the 50 GWh reference consumer "
        f"{ssot.eur_m('wrong_strategy_cost_total')} over 2021-2025, the sum of each year's "
        f"gap between the dearest and the cheapest of four strategies. Over the five years "
        f"**{_label(best)}** was the cheapest strategy at {ssot.eur_m(f'cost5yr_{best}')} in "
        f"total. For the next 12 months {_label(cost_min)} has the lowest expected cost, "
        f"{ssot.eur_m(f'mean_next12m_{cost_min}')}, and {_label(averse)} the lowest P95 "
        f"exposure: {ssot.eur_m(f'p95_next12m_{averse}')} against "
        f"{ssot.eur_m(f'p95_next12m_{cost_min}')}."
    )


def yearly_winners(ssot: Ssot, years: list[int], strategies: list[str]) -> str:
    """Data-driven sentence on which strategy was cheapest each year."""
    winners = {y: min(strategies, key=lambda s: ssot.num(f"cost_{s}_{y}")) for y in years}
    listing = "; ".join(f"{y}: {_label(w)}" for y, w in winners.items())
    distinct = set(winners.values())
    if len(distinct) == 1:
        verdict = f"{_label(distinct.pop())} was the cheapest strategy in every year."
    else:
        verdict = (
            f"{len(distinct)} different strategies were cheapest in at least one year, "
            f"so no single choice wins every year; the budget question is how much "
            f"year-to-year variation the company can absorb."
        )
    return f"Cheapest strategy per year — {listing}. {verdict}"


def recommendation(ssot: Ssot) -> str:
    """SPEC-06 §5 item 5: both CFO types, each with its euro trade-off."""
    cost_min = ssot.text("q4_cost_min_strategy")
    averse = ssot.text("q4_risk_averse_strategy")
    if cost_min == averse:
        return (
            f"**Both CFO types choose {_label(cost_min)}**: it has the lowest expected cost, "
            f"{ssot.eur_m(f'mean_next12m_{cost_min}')}, and the lowest P95, "
            f"{ssot.eur_m(f'p95_next12m_{cost_min}')}. There is no trade-off to price in "
            f"this window."
        )
    # cost_min has the lowest mean by definition, so the premium is never negative.
    return (
        f"A **cost-minimizing CFO** chooses {_label(cost_min)}: the lowest expected 12-month "
        f"cost, {ssot.eur_m(f'mean_next12m_{cost_min}')}, with a P95 of "
        f"{ssot.eur_m(f'p95_next12m_{cost_min}')}. A **risk-averse CFO** chooses "
        f"{_label(averse)}: it lowers the P95 by {ssot.eur_m('q4_p95_reduction_eur')} and "
        f"costs {ssot.eur_m('q4_risk_premium_eur')} more in expectation. That premium is the "
        f"price of the risk reduction."
    )


def persistence_sentence(ssot: Ssot) -> str:
    """Volatility-clustering sentence conditioned on the GARCH persistence (AN-303)."""
    persistence = ssot.num("garch_persistence")
    if persistence >= 0.8:
        return (
            f"Volatility clusters: the GARCH persistence of daily price changes is "
            f"{persistence:.2f} (VERIFIED), so turbulent periods last for months."
        )
    return f"The GARCH persistence of daily price changes is {persistence:.2f} (VERIFIED)."


def exec_summary(ssot: Ssot, fixture: bool) -> str:
    """The full ``reports/EXEC_SUMMARY.md`` text (SPEC-06 §5, ≤ 2 pages)."""
    cfg = load_strategy_config()
    years = list(cfg.retrospective_years)
    strategies = ["S1", "S2", "S3", *(f"S4_{round(h * 100)}" for h in cfg.hybrid_ratios)]
    crisis = ssot.num("annual_mean_price_2022") if "annual_mean_price_2022" in ssot.rows else 0.0
    calm = ssot.num("annual_mean_price_2019")
    last_year = max(y for y in years if f"neg_hours_{y}" in ssot.rows)
    banner = [f"> **{FIXTURE_BANNER}**", ""] if fixture else []
    return "\n".join(
        [
            "# Executive summary — electricity procurement risk, StyriaMetal GmbH (reference)",
            "",
            *banner,
            "*For: CFO / Head of Procurement. Energy cost only (no grid fees, taxes or levies). "
            f"Data through {ssot.text('data_last_month')}.*",
            "",
            "## 1. The answer",
            "",
            answer(ssot),
            "",
            "## 2. How to read this",
            "",
            "Market prices are **VERIFIED**: computed from ENTSO-E day-ahead data without "
            "modelling. Strategy costs are **CALIBRATED**: the 50 GWh load profile is constructed, "
            "not metered, and contract prices are translated from the ÖSPI index. Forward risk is "
            f"**SIMULATED**: {ssot.text('forward_n_paths')} seeded resamples of historical "
            "months; it is not a price forecast.",
            "",
            "## 3. The market you are buying in",
            "",
            f"The Austrian day-ahead price averaged {format_eur_mwh(crisis)} in 2022 against "
            f"{format_eur_mwh(calm)} in 2019 (VERIFIED). {persistence_sentence(ssot)} "
            f"{last_year} had {int(ssot.num(f'neg_hours_{last_year}'))} hours with negative "
            "prices (VERIFIED). Chart: `reports/executive_charts/04_market_context.png`.",
            "",
            "## 4. Strategy comparison 2021-2025 (EUR million, CALIBRATED)",
            "",
            strategy_table(ssot, years, strategies),
            "",
            f"*{ST502_CAPTION} {LP050_CAPTION}*",
            "",
            yearly_winners(ssot, years, strategies),
            "",
            f"## 5. Forward risk and recommendation ({ssot.text('forward_window')}, "
            "EUR million, SIMULATED)",
            "",
            forward_table(ssot, strategies),
            "",
            recommendation(ssot),
            "",
            "## 6. What would change this analysis",
            "",
            "- Metered (RLM) load data instead of the constructed profile would change the cost "
            "levels, not the logic of the comparison (LIMITATIONS §1).",
            "- Real supplier offers can differ from the ÖSPI proxy by margin, credit and "
            "flexibility terms; the direction of that bias is unknown (§2, §3).",
            "- A crisis without historical precedent lies outside the bootstrap; the P95 would "
            "understate it (§4).",
            "",
        ]
    )


def readme_blocks(ssot: Ssot, fixture: bool) -> dict[str, str]:
    """``answer`` and ``chart`` (top of README) and ``results`` (Results section)."""
    if fixture:
        notice = (
            "> **Results pending the first real-data run.** The pipeline is complete and "
            "tested end to end on a synthetic CI fixture (ADR-018); fixture numbers are "
            "never shown here as results. Running `make backfill && make all` with an "
            "ENTSO-E token fills this section from `reports/NUMERIC_SSOT.md`."
        )
        chart = (
            "*The headline chart (what the wrong strategy cost per year) is embedded here "
            "after the first real-data run. A watermarked [pipeline preview on synthetic "
            "fixture data](reports/executive_charts/01_wrong_strategy_cost.png) shows its "
            "layout; its figures are not results.*"
        )
        return {"answer": notice, "chart": chart, "results": notice}
    cfg = load_strategy_config()
    years = list(cfg.retrospective_years)
    strategies = ["S1", "S2", "S3", *(f"S4_{round(h * 100)}" for h in cfg.hybrid_ratios)]
    results = "\n".join(
        [
            "**Annual energy cost per strategy, EUR million (CALIBRATED)**",
            "",
            strategy_table(ssot, years, strategies),
            "",
            f"**Next 12 months ({ssot.text('forward_window')}), EUR million (SIMULATED)**",
            "",
            forward_table(ssot, strategies),
            "",
            recommendation(ssot),
            "",
            f"*{ST502_CAPTION} {LP050_CAPTION}*",
        ]
    )
    chart = (
        "![What the wrong electricity procurement strategy cost a 50 GWh Styrian "
        "manufacturer](reports/executive_charts/01_wrong_strategy_cost.png)"
    )
    return {"answer": answer(ssot), "chart": chart, "results": results}


def replace_block(text: str, name: str, body: str) -> str:
    """Swap the content between the ``name`` markers; raises if markers are missing."""
    start, end = MARKER.format(name=name, edge="start"), MARKER.format(name=name, edge="end")
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"README markers for block {name!r} not found")
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text)


def run(settings: Settings, readme: Path = README) -> Path:
    """Write EXEC_SUMMARY.md and refresh the README blocks from the SSOT.

    Implements: SPEC-06 §5, RP-601, A-6.
    """
    reports = resolve_repo_path(settings.paths.reports)
    ssot = Ssot.from_markdown(reports / SSOT_FILE.name)
    fixture = is_fixture_run(settings)
    path = reports / "EXEC_SUMMARY.md"
    path.write_text(exec_summary(ssot, fixture), encoding="utf-8")
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        for name, body in readme_blocks(ssot, fixture).items():
            text = replace_block(text, name, body)
        readme.write_text(text, encoding="utf-8")
    return path
