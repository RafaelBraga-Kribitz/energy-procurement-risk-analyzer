"""Retrospective engine — Q1: what did each strategy cost, 2021-2025 (SPEC-05 §5).

Outputs:

- ``data/processed/strategy_costs_monthly.parquet`` (ST-001; re-exposed by dbt
  as ``fct_procurement_cost_monthly``) and ``strategy_annual_summary.parquet``;
- ``reports/strategies/strategy_annual_summary.md`` (+ CSV), the unit-cost
  table, ``sensitivity_matrix.md`` (ST-303), charts ``s5_annual_costs.png``
  and ``s5_cumulative.png`` (ST-304);
- SSOT rows: cost matrix, ``wrong_strategy_cost_<year>`` / ``_total``,
  ``best_strategy_5yr``, the four anchors and the sensitivity totals — all
  CALIBRATED, because the load profile is (Charter E-2).

Implements: ST-002, ST-101..107, ST-201..204, ST-301..304, ST-501..503.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from epra.common import logging as common_logging
from epra.common.config import (
    Settings,
    StrategyCfg,
    load_settings,
    load_strategy_config,
    resolve_repo_path,
)
from epra.common.provenance import banner_lines, is_fixture_run
from epra.common.ssot import SsotRow, ssot_value, write_ssot_rows
from epra.report.charts import annual_cost_chart
from epra.report.figure import new_figure, save_figure
from epra.report.format import format_eur_millions, md_table
from epra.report.style import (
    CALIBRATED_TAG,
    LP050_CAPTION,
    ST502_CAPTION,
    STRATEGY_COLORS,
    STRATEGY_LABELS,
)
from epra.strategies.calibration import Anchors, compute_anchors
from epra.strategies.engine import (
    StrategyParams,
    annual_summary,
    monthly_costs,
    strategy_ids,
    wrong_strategy_cost,
)
from epra.strategies.inputs import FLAT_PROFILE, MAIN_PROFILE, monthly_spot, oespi_monthly

logger = logging.getLogger(__name__)
PRODUCER = "strategies/retrospective.py"
COSTS_FILE = "strategy_costs_monthly.parquet"
ANNUAL_FILE = "strategy_annual_summary.parquet"


@dataclass(frozen=True)
class Scenario:
    """One ST-303 rerun: a name, the profile priced and the parameter set."""

    name: str
    profile: str
    params: StrategyParams


def strategies_dir(settings: Settings) -> Path:
    """``reports/strategies/``."""
    path = resolve_repo_path(settings.paths.reports) / "strategies"
    path.mkdir(parents=True, exist_ok=True)
    return path


def base_params(anchors: Anchors, w_peak: float, cfg: StrategyCfg) -> StrategyParams:
    """Default parameter set from ``config/strategies.yaml`` (ST-003)."""
    return StrategyParams(
        anchors=anchors,
        w_peak=w_peak,
        fixed_premium_eur_mwh=cfg.fixed_premium_eur_mwh,
        lock_window_months=tuple(cfg.lock_window_months),
        hybrid_ratios=tuple(cfg.hybrid_ratios),
        peak_available=cfg.peak_available,
    )


def scenarios(settings: Settings, cfg: StrategyCfg) -> list[Scenario]:
    """Base case + the ST-303 grid; each differs from base in exactly one input.

    Implements: ST-303.
    """
    base = base_params(
        compute_anchors(settings, cfg), ssot_value(settings, "consumer_peak_share"), cfg
    )
    flat = base_params(
        compute_anchors(settings, cfg, FLAT_PROFILE),
        ssot_value(settings, f"consumer_peak_share_{FLAT_PROFILE}"),
        cfg,
    )
    premium = [
        Scenario(f"premium_{p:g}", MAIN_PROFILE, replace(base, fixed_premium_eur_mwh=p))
        for p in cfg.sensitivity.fixed_premium_eur_mwh
    ]
    lock = replace(base, lock_window_months=tuple(cfg.sensitivity.lock_window_months))
    return [
        Scenario("base", MAIN_PROFILE, base),
        *premium,
        Scenario("flat_baseload", FLAT_PROFILE, flat),
        Scenario("lock_full_prior_year", MAIN_PROFILE, lock),
    ]


def price_scenario(settings: Settings, scenario: Scenario, years: list[int]) -> pd.DataFrame:
    """Monthly cost frame for one scenario (logs ST-101 dropped hours)."""
    spot = monthly_spot(settings, scenario.profile)
    dropped = int(spot.loc[spot["year_local"].isin(years), "dropped_hours"].sum())
    if dropped:
        logger.warning("%s: %d hours without AT price dropped (ST-101)", scenario.name, dropped)
    return monthly_costs(spot, oespi_monthly(settings), scenario.params, years)


def sensitivity_table(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """5-year cost per strategy (EUR M), best strategy and wrong-strategy total.

    Implements: ST-303.
    """
    rows = []
    for name, annual in results.items():
        totals = annual.groupby("strategy_id", sort=False)["cost_eur"].sum()
        row: dict[str, object] = {"scenario": name}
        row.update({sid: totals[sid] / 1e6 for sid in totals.index})
        row["best"] = str(totals.idxmin())
        row["wrong_strategy_cost_total_m"] = float(wrong_strategy_cost(annual).sum()) / 1e6
        rows.append(row)
    return pd.DataFrame(rows)


def _annual_chart(annual: pd.DataFrame, settings: Settings) -> None:
    annual_cost_chart(
        annual, strategies_dir(settings) / "s5_annual_costs.png", fixture=is_fixture_run(settings)
    )


def _cumulative_chart(annual: pd.DataFrame, settings: Settings) -> None:
    totals = annual.groupby("strategy_id")["cost_eur"].sum()
    fig, ax = new_figure()
    for sid in dict.fromkeys(annual["strategy_id"]):
        part = annual[annual["strategy_id"] == sid].sort_values("year")
        ax.plot(
            part["year"],
            part["cost_eur"].cumsum() / 1e6,
            marker="o",
            lw=2,
            color=STRATEGY_COLORS[sid],
            label=STRATEGY_LABELS[sid],
        )
    ax.set_xticks(sorted(annual["year"].unique()))
    ax.set_xlabel("Delivery year")
    ax.set_ylabel("Cumulative energy cost since 2021 (EUR million)")
    ax.legend(frameon=False)
    save_figure(
        fig,
        strategies_dir(settings) / "s5_cumulative.png",
        title=f"Five-year total: {STRATEGY_LABELS[str(totals.idxmin())]} "
        f"cheapest, {STRATEGY_LABELS[str(totals.idxmax())]} dearest "
        f"(gap {format_eur_millions(float(totals.max() - totals.min()))})",
        subtitle=f"Cumulative energy cost per strategy. {ST502_CAPTION}",
        tag=CALIBRATED_TAG,
        fixture=is_fixture_run(settings),
    )


def _matrix(annual: pd.DataFrame, value: str, scale: float) -> pd.DataFrame:
    wide = annual.pivot(index="strategy_id", columns="year", values=value) / scale
    wide = wide.reindex(list(dict.fromkeys(annual["strategy_id"])))
    wide.insert(0, "strategy", [STRATEGY_LABELS[s] for s in wide.index])
    wide.columns = [str(c) for c in wide.columns]
    return wide.reset_index(drop=True)


def _write_reports(
    settings: Settings, annual: pd.DataFrame, sens: pd.DataFrame, anchors: Anchors
) -> None:
    out = strategies_dir(settings)
    annual.round(4).to_csv(out / "strategy_annual_summary.csv", index=False)
    sens.round(4).to_csv(out / "sensitivity_matrix.csv", index=False)
    wrong = wrong_strategy_cost(annual)
    wrong_table = pd.DataFrame(
        {
            "year": wrong.index.astype(str),
            "wrong_strategy_cost": [format_eur_millions(v) for v in wrong],
        }
    )
    caption = [f"*{ST502_CAPTION}*", "", f"*{LP050_CAPTION}*", ""]
    (out / "strategy_annual_summary.md").write_text(
        "\n".join(
            [
                "# Strategy comparison 2021-2025 (Q1)",
                "",
                *banner_lines(settings),
                *caption,
                "## Annual energy cost (EUR million, CALIBRATED)",
                "",
                md_table(_matrix(annual, "cost_eur", 1e6), ".2f"),
                "",
                "## Unit cost (EUR/MWh, CALIBRATED)",
                "",
                md_table(_matrix(annual, "unit_cost_eur_mwh", 1.0), ".1f"),
                "",
                "## Cost of the wrong strategy (max − min per year, CALIBRATED)",
                "",
                md_table(wrong_table),
                "",
                "## Calibration anchors (CALIBRATED, ST-201..204)",
                "",
                f"p_ref_base = {anchors.p_ref_base:.2f} EUR/MWh; p_ref_peak = "
                f"{anchors.p_ref_peak:.2f} EUR/MWh; ÖSPI base ref = {anchors.oespi_base_ref:.2f}; "
                f"ÖSPI peak ref = {anchors.oespi_peak_ref:.2f} (index points).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (out / "sensitivity_matrix.md").write_text(
        "\n".join(
            [
                "# Sensitivity matrix (ST-303)",
                "",
                *banner_lines(settings),
                *caption,
                "Five-year (2021-2025) energy cost per strategy in EUR million; each scenario "
                "changes exactly one input versus `base`: fixed-price premium, load shape "
                "(flat baseload), or S3 lock window (full prior year).",
                "",
                md_table(sens, ".2f"),
                "",
            ]
        ),
        encoding="utf-8",
    )


def _ssot_rows(annual: pd.DataFrame, sens: pd.DataFrame, anchors: Anchors) -> list[SsotRow]:
    def row(key: str, value: float | str, unit: str) -> SsotRow:
        return SsotRow(key, value, unit, "CALIBRATED", PRODUCER)

    wrong = wrong_strategy_cost(annual)
    totals = annual.groupby("strategy_id")["cost_eur"].sum()
    rows = [
        row("wrong_strategy_cost_total", round(float(wrong.sum()), 2), "EUR"),
        row("best_strategy_5yr", str(totals.idxmin()), "strategy_id"),
    ]
    rows += [
        row(f"wrong_strategy_cost_{y}", round(float(v), 2), "EUR")
        for y, v in zip(wrong.index, wrong, strict=True)
    ]
    for rec in annual.to_dict("records"):
        sid, year = rec["strategy_id"], rec["year"]
        rows.append(row(f"cost_{sid}_{year}", round(float(rec["cost_eur"]), 2), "EUR"))
        rows.append(
            row(f"unit_cost_{sid}_{year}", round(float(rec["unit_cost_eur_mwh"]), 4), "EUR/MWh")
        )
    rows += [row(f"cost5yr_{sid}", round(float(v), 2), "EUR") for sid, v in totals.items()]
    rows += [
        row(name, round(value, 4), unit)
        for name, value, unit in (
            ("p_ref_base", anchors.p_ref_base, "EUR/MWh"),
            ("p_ref_peak", anchors.p_ref_peak, "EUR/MWh"),
            ("oespi_base_ref", anchors.oespi_base_ref, "index"),
            ("oespi_peak_ref", anchors.oespi_peak_ref, "index"),
        )
    ]
    for rec in sens.to_dict("records"):
        name = rec["scenario"]
        rows.append(
            row(
                f"sens_{name}_wrong_total",
                round(rec["wrong_strategy_cost_total_m"] * 1e6, 2),
                "EUR",
            )
        )
        rows.append(row(f"sens_{name}_best", str(rec["best"]), "strategy_id"))
    return rows


def run(settings: Settings) -> pd.DataFrame:
    """Compute Q1, sensitivities, charts and SSOT rows; returns the annual summary.

    Implements: ST-002, ST-301..304, ST-204.
    """
    cfg = load_strategy_config()
    years = list(cfg.retrospective_years)
    results: dict[str, pd.DataFrame] = {}
    base_monthly = pd.DataFrame()
    grid = scenarios(settings, cfg)
    for scenario in grid:
        monthly = price_scenario(settings, scenario, years)
        results[scenario.name] = annual_summary(monthly)
        if scenario.name == "base":
            base_monthly = monthly
    annual = results["base"]
    processed = resolve_repo_path(settings.paths.data_processed)
    processed.mkdir(parents=True, exist_ok=True)
    base_monthly.to_parquet(processed / COSTS_FILE, index=False)
    annual.to_parquet(processed / ANNUAL_FILE, index=False)
    sens = sensitivity_table(results)
    anchors = grid[0].params.anchors
    _write_reports(settings, annual, sens, anchors)
    _annual_chart(annual, settings)
    _cumulative_chart(annual, settings)
    write_ssot_rows(_ssot_rows(annual, sens, anchors), "strategies_retrospective", settings)
    logger.info(
        "retrospective: %d strategies x %d years; wrong-strategy total %s",
        len(strategy_ids(grid[0].params)),
        len(years),
        format_eur_millions(float(wrong_strategy_cost(annual).sum())),
    )
    return annual


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.retrospective`` (ST-002).

    Implements: ST-002.
    """
    argparse.ArgumentParser(
        prog="python -m epra.strategies.retrospective", description=__doc__.splitlines()[0]
    ).parse_args(argv)
    common_logging.setup()
    run(load_settings())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
