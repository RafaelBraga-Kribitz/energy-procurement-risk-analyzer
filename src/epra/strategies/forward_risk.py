"""Forward risk engine — Q3: next-12-month cost distribution (SPEC-05 §6).

Seasonal block bootstrap over whole historical months, implemented with the
RECOMMENDED vectorized design (ST-406):

1. Pool (ST-401.1): every historical month with prices AND ÖSPI.
2. Cells: for each target month t (calendar month c) and each pool year y' of
   month c, align the drawn month's hourly prices onto the target month's hours
   by (day-of-month, hour_local) (ST-401.3) and precompute the consumer's spot
   cost, its volume, and the drawn month's ÖSPI pair — 12 × ~8 cells.
3. Draws (ST-401.2): ``numpy.random.default_rng(seed)``; one integer per
   (path, target month) in row-major = deterministic loop order. A path's
   strategy costs are sums over its drawn cells (costs are additive over months
   and all strategies share a path's drawn months — mathematically identical
   to pricing every path hour by hour).
4. S3's lock price (ST-402): observed lock-window ÖSPI where the month is in
   the warehouse, the path's drawn ÖSPI where it is a target month, and — for
   a lock month that is neither (between the last observed ÖSPI month and the
   first target month) — the last observed value carried forward (ADR-019).
5. Variants (ST-401.4): unconditional, and "no-crisis" with the pool limited to
   years whose December HMM regime (AN-302) is calm/elevated.

Outputs: ``forward_risk_summary`` (mean, std, P5, P50, P95, CVaR95 per
strategy and variant; SIMULATED), ``s5_forward_fan.png``, ``s5_risk_return.png``,
the Q4 recommendation rows, ``reports/strategies/forward_risk_summary.md``.

Implements: ST-002, ST-401..406, ST-602(c) inputs, Q3/Q4 SSOT rows.
"""

from __future__ import annotations

import argparse
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd

from epra.common import logging as common_logging
from epra.common.config import (
    Settings,
    StrategyCfg,
    load_settings,
    load_strategy_config,
    resolve_repo_path,
)
from epra.common.frames import scalar
from epra.common.provenance import banner_lines, is_fixture_run
from epra.common.ssot import SsotRow, ssot_value, write_ssot_rows
from epra.report.charts import forward_fan_chart
from epra.report.figure import new_figure, save_figure
from epra.report.format import format_eur_millions, md_table
from epra.report.style import (
    LP050_CAPTION,
    SIMULATED_TAG,
    ST502_CAPTION,
    STRATEGY_COLORS,
    STRATEGY_LABELS,
)
from epra.strategies.calibration import compute_anchors
from epra.strategies.engine import StrategyParams, hybrid_id, indexed_price, strategy_ids
from epra.strategies.inputs import (
    MAIN_PROFILE,
    hourly_prices,
    last_priced_month,
    oespi_monthly,
    target_load,
)
from epra.strategies.retrospective import base_params, strategies_dir

logger = logging.getLogger(__name__)
PRODUCER = "strategies/forward_risk.py"
SUMMARY_FILE = "forward_risk_summary.parquet"
PATHS_FILE = "forward_paths.parquet"
VARIANTS = ("unconditional", "no_crisis")
CRISIS_LABEL = "crisis"
Month = tuple[int, int]
#: Label offsets (points) so the three hybrids, which sit close together, stay legible.
_LABEL_OFFSETS = {"S4_30": (7, 6), "S4_50": (7, -14), "S4_70": (7, 18)}


@dataclass(frozen=True)
class Cells:
    """Precomputed per-(target month, pool year) quantities (ST-406)."""

    targets: list[Month]
    pool_years: list[list[int]]  # per target: candidate y'
    volume: np.ndarray  # per target, MWh
    spot_cost: list[np.ndarray]  # per target: one value per pool year, EUR
    oespi_base: list[np.ndarray]
    oespi_peak: list[np.ndarray]


def target_months(last: Month, horizon: int) -> list[Month]:
    """The ``horizon`` calendar months after ``last`` (Charter §4.3)."""
    out, (year, month) = [], last
    for _ in range(horizon):
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        out.append((year, month))
    return out


def align_prices(drawn: pd.DataFrame, target: pd.DataFrame) -> np.ndarray:
    """ST-401.3: drawn-month prices mapped onto target hours.

    Keyed by (day-of-month, hour_local); duplicate fall-back hours are averaged.
    Target days beyond the drawn month reuse the drawn month's LAST day of the
    same day type (working day vs weekend/holiday). An hour missing in the
    drawn month (spring-forward) is forward-filled in target order.

    Implements: ST-401 step 3.
    """
    table = drawn.groupby(["day_local", "hour_local"])["price_at_eur_mwh"].mean()
    day_type = drawn.groupby("day_local")["is_weekend_or_holiday"].first()
    n_days = int(day_type.index.max())
    last_of_type = {
        flag: int(day_type[day_type == flag].index.max()) if (day_type == flag).any() else n_days
        for flag in (True, False)
    }
    src_day = np.where(
        target["day_local"] <= n_days,
        target["day_local"],
        target["is_weekend_or_holiday"].map(last_of_type),
    )
    keys = pd.MultiIndex.from_arrays([src_day, target["hour_local"].to_numpy()])
    aligned = pd.Series(table.reindex(keys).to_numpy())
    return np.asarray(aligned.ffill().bfill().to_numpy(), dtype=float)


def december_regimes(regimes: pd.DataFrame) -> dict[int, str]:
    """Modal HMM regime of each year's December (AN-302 labels)."""
    dates = pd.to_datetime(regimes["date_local"])
    december = regimes[dates.dt.month == 12].assign(year=dates[dates.dt.month == 12].dt.year)
    return {
        int(cast(int, year)): str(group["regime"].mode().sort_values().iloc[0])
        for year, group in december.groupby("year")
    }


def build_pool(oespi: pd.DataFrame, excluded_years: set[int]) -> dict[int, list[int]]:
    """Calendar month → sorted pool years with prices + ÖSPI (ST-401.1/.4)."""
    pool: dict[int, list[int]] = {}
    for rec in oespi.to_dict("records"):
        if int(rec["year_local"]) not in excluded_years:
            pool.setdefault(int(rec["month_local"]), []).append(int(rec["year_local"]))
    return {month: sorted(years) for month, years in pool.items()}


def build_cells(
    prices: pd.DataFrame,
    loads: pd.DataFrame,
    oespi: pd.DataFrame,
    targets: list[Month],
    pool: dict[int, list[int]],
) -> Cells:
    """Precompute every (target month, pool year) cell (ST-406).

    Implements: ST-401 steps 1-3, ST-402 (volumes from the forward profile).
    """
    by_month = dict(iter(prices.groupby(["year_local", "month_local"])))
    index = oespi.set_index(["year_local", "month_local"])
    volume, spot, base, peak, years_per_target = [], [], [], [], []
    for year, month in targets:
        target = loads[(loads["year_local"] == year) & (loads["month_local"] == month)]
        if target.empty:
            raise ValueError(f"no forward load for {year}-{month:02d} — rerun `make profile`")
        years = pool.get(month, [])
        if not years:
            raise ValueError(f"empty bootstrap pool for calendar month {month}")
        load = target["load_mwh"].to_numpy()
        spot.append(
            np.array([float(load @ align_prices(by_month[(y, month)], target)) for y in years])
        )
        base.append(np.array([scalar(index, (y, month), "oespi_base") for y in years]))
        peak.append(np.array([scalar(index, (y, month), "oespi_peak") for y in years]))
        volume.append(float(load.sum()))
        years_per_target.append(years)
    return Cells(targets, years_per_target, np.array(volume), spot, base, peak)


def draw_indices(cells: Cells, n_paths: int, seed: int) -> np.ndarray:
    """(n_paths, n_targets) pool indices; one RNG, row-major loop order (ST-401.2)."""
    rng = np.random.default_rng(seed=seed)
    sizes = np.array([len(years) for years in cells.pool_years])
    return rng.integers(0, sizes, size=(n_paths, len(sizes)))


def s3_prices(
    cells: Cells, draws: np.ndarray, oespi: pd.DataFrame, params: StrategyParams
) -> dict[int, np.ndarray]:
    """Per delivery year: S3 lock price per path, premium included (ST-402, ADR-019)."""
    observed = oespi.set_index(["year_local", "month_local"])[["oespi_base", "oespi_peak"]]
    last_obs = observed.iloc[-1]
    target_pos = {m: i for i, m in enumerate(cells.targets)}
    n_paths = draws.shape[0]
    prices = {}
    for year in sorted({y for y, _ in cells.targets}):
        base_sum, peak_sum = np.zeros(n_paths), np.zeros(n_paths)
        for month in params.lock_window_months:
            key = (year - 1, month)
            if key in observed.index:
                base_sum += scalar(observed, key, "oespi_base")
                peak_sum += scalar(observed, key, "oespi_peak")
            elif key in target_pos:
                t = target_pos[key]
                base_sum += cells.oespi_base[t][draws[:, t]]
                peak_sum += cells.oespi_peak[t][draws[:, t]]
            else:  # ADR-019: gap between last observed index month and the window
                base_sum += last_obs["oespi_base"]
                peak_sum += last_obs["oespi_peak"]
        n = len(params.lock_window_months)
        prices[year] = indexed_price(base_sum / n, peak_sum / n, params) + (
            params.fixed_premium_eur_mwh
        )
    return prices


def path_costs(
    cells: Cells, draws: np.ndarray, oespi: pd.DataFrame, params: StrategyParams
) -> pd.DataFrame:
    """12-month total cost per path and strategy (EUR), vectorized (ST-402/406).

    Implements: ST-402, ST-406.
    """
    columns = range(len(cells.targets))
    s1 = sum(cells.spot_cost[t][draws[:, t]] for t in columns)
    s2 = sum(
        cells.volume[t]
        * indexed_price(cells.oespi_base[t][draws[:, t]], cells.oespi_peak[t][draws[:, t]], params)
        for t in columns
    )
    lock = s3_prices(cells, draws, oespi, params)
    s3 = sum(cells.volume[t] * lock[cells.targets[t][0]] for t in columns)
    costs = {"S1": s1, "S2": s2, "S3": s3}
    for ratio in params.hybrid_ratios:
        costs[hybrid_id(ratio)] = ratio * np.asarray(s3) + (1.0 - ratio) * np.asarray(s1)
    return pd.DataFrame({sid: np.asarray(v, dtype=float) for sid, v in costs.items()})


def risk_metrics(costs: pd.Series) -> dict[str, float]:
    """mean, std, P5, P50, P95, CVaR95 (mean of the worst 5% = highest costs).

    Implements: ST-403.
    """
    values = np.sort(costs.to_numpy(dtype=float))[::-1]
    tail = values[: math.ceil(0.05 * len(values))]
    return {
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)),
        "p5": float(np.percentile(values, 5)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "cvar95": float(tail.mean()),
    }


def summarize(paths: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Long table ``variant, strategy_id, mean, std, p5, p50, p95, cvar95``."""
    rows = [
        {"variant": variant, "strategy_id": sid, **risk_metrics(frame[sid])}
        for variant, frame in paths.items()
        for sid in frame.columns
    ]
    return pd.DataFrame(rows)


def recommendation(summary: pd.DataFrame) -> dict[str, float | str]:
    """Q4: cost-minimizer (lowest mean) vs risk-averse (lowest P95) and the
    EUR price of the tail reduction, on the unconditional variant.

    Implements: Charter Q4 (SPEC-06 §5 item 5 inputs).
    """
    base = summary[summary["variant"] == "unconditional"].set_index("strategy_id")
    cost_min = str(base["mean"].idxmin())
    risk_averse = str(base["p95"].idxmin())
    return {
        "cost_min_strategy": cost_min,
        "risk_averse_strategy": risk_averse,
        "risk_premium_eur": scalar(base, risk_averse, "mean") - scalar(base, cost_min, "mean"),
        "p95_reduction_eur": scalar(base, cost_min, "p95") - scalar(base, risk_averse, "p95"),
    }


def _fan_chart(paths: pd.DataFrame, summary: pd.DataFrame, window: str, settings: Settings) -> None:
    forward_fan_chart(
        paths,
        summary,
        window,
        strategies_dir(settings) / "s5_forward_fan.png",
        fixture=is_fixture_run(settings),
    )


def _risk_return_chart(summary: pd.DataFrame, settings: Settings) -> None:
    fig, ax = new_figure()
    for variant, marker, fill in (("unconditional", "o", True), ("no_crisis", "s", False)):
        part = summary[summary["variant"] == variant]
        for rec in part.to_dict("records"):
            color = STRATEGY_COLORS[rec["strategy_id"]]
            ax.scatter(
                rec["mean"] / 1e6,
                rec["p95"] / 1e6,
                s=90,
                marker=marker,
                facecolors=color if fill else "none",
                edgecolors=color,
                linewidths=2,
            )
            if fill:
                ax.annotate(
                    STRATEGY_LABELS[rec["strategy_id"]],
                    (rec["mean"] / 1e6, rec["p95"] / 1e6),
                    xytext=(7, 4),
                    textcoords="offset points",
                    fontsize=9,
                )
    ax.scatter([], [], marker="o", color="grey", label="Unconditional pool")
    ax.scatter([], [], marker="s", facecolors="none", edgecolors="grey", label="No-crisis pool")
    ax.legend(frameon=False, loc="upper left")
    ax.set_xlabel("Expected 12-month cost (EUR million)")
    ax.set_ylabel("P95 12-month cost (EUR million)")
    save_figure(
        fig,
        strategies_dir(settings) / "s5_risk_return.png",
        title="Lower tail risk costs a premium: pick a point on the risk-return frontier",
        subtitle=f"Mean vs P95 of the 12-month cost per strategy. {ST502_CAPTION}",
        tag=SIMULATED_TAG,
        fixture=is_fixture_run(settings),
    )


def _report(
    settings: Settings, summary: pd.DataFrame, q4: dict[str, float | str], window: str, n_paths: int
) -> None:
    shown = summary.copy()
    shown.insert(1, "strategy", shown["strategy_id"].map(STRATEGY_LABELS))
    for col in ("mean", "std", "p5", "p50", "p95", "cvar95"):
        shown[col] = shown[col] / 1e6
    cost_min, risk_averse = str(q4["cost_min_strategy"]), str(q4["risk_averse_strategy"])
    text = [
        "# Forward risk, next 12 months (Q3/Q4)",
        "",
        *banner_lines(settings),
        f"*{ST502_CAPTION}*",
        "",
        f"*{LP050_CAPTION}*",
        "",
        f"Window {window}; {n_paths:,} seeded bootstrap paths per variant; costs in EUR "
        "million (SIMULATED). `no_crisis` limits the pool to years whose December HMM "
        "regime is not `crisis` (ST-401 step 4).",
        "",
        md_table(shown.drop(columns=["strategy_id"]), ".2f"),
        "",
        "## Q4 — what a CFO would choose",
        "",
        f"A cost-minimizing buyer picks **{STRATEGY_LABELS[cost_min]}** (lowest expected "
        f"cost). A risk-averse buyer picks **{STRATEGY_LABELS[risk_averse]}** (lowest P95). "
        f"The tail protection costs {format_eur_millions(float(q4['risk_premium_eur']))} "
        f"in expected cost and lowers the P95 by "
        f"{format_eur_millions(float(q4['p95_reduction_eur']))} (SIMULATED).",
        "",
    ]
    (strategies_dir(settings) / "forward_risk_summary.md").write_text(
        "\n".join(text), encoding="utf-8"
    )


def _ssot_rows(
    summary: pd.DataFrame, q4: dict[str, float | str], window: str, n_paths: int
) -> list[SsotRow]:
    def row(key: str, value: float | str, unit: str) -> SsotRow:
        return SsotRow(key, value, unit, "SIMULATED", PRODUCER)

    rows = [row("forward_window", window, "months"), row("forward_n_paths", n_paths, "paths")]
    for rec in summary.to_dict("records"):
        suffix = "" if rec["variant"] == "unconditional" else "_nocrisis"
        for metric in ("mean", "p5", "p50", "p95", "cvar95"):
            rows.append(
                row(
                    f"{metric}_next12m{suffix}_{rec['strategy_id']}",
                    round(float(rec[metric]), 2),
                    "EUR",
                )
            )
    rows += [
        row("q4_cost_min_strategy", str(q4["cost_min_strategy"]), "strategy_id"),
        row("q4_risk_averse_strategy", str(q4["risk_averse_strategy"]), "strategy_id"),
        row("q4_risk_premium_eur", round(float(q4["risk_premium_eur"]), 2), "EUR"),
        row("q4_p95_reduction_eur", round(float(q4["p95_reduction_eur"]), 2), "EUR"),
    ]
    return rows


def simulate(settings: Settings, cfg: StrategyCfg) -> tuple[dict[str, pd.DataFrame], str]:
    """Both variants' path-cost frames and the window label (ST-401..405)."""
    params = base_params(
        compute_anchors(settings, cfg), ssot_value(settings, "consumer_peak_share"), cfg
    )
    oespi = oespi_monthly(settings)
    targets = target_months(last_priced_month(settings), cfg.forward.horizon_months)
    first, final = targets[0], targets[-1]
    loads = target_load(
        settings, MAIN_PROFILE, f"{first[0]}-{first[1]:02d}-01", f"{final[0]}-{final[1]:02d}-01"
    )
    prices = hourly_prices(settings)
    regimes = pd.read_parquet(
        resolve_repo_path(settings.paths.data_processed) / "regimes_daily.parquet"
    )
    crisis_years = {y for y, r in december_regimes(regimes).items() if r == CRISIS_LABEL}
    paths = {}
    for variant, excluded in (("unconditional", set()), ("no_crisis", crisis_years)):
        cells = build_cells(prices, loads, oespi, targets, build_pool(oespi, excluded))
        draws = draw_indices(cells, cfg.forward.n_paths, cfg.forward.seed)
        paths[variant] = path_costs(cells, draws, oespi, params)[strategy_ids(params)]
    window = f"{first[0]}-{first[1]:02d}..{final[0]}-{final[1]:02d}"
    logger.info(
        "forward: window %s, crisis years excluded in no_crisis: %s", window, sorted(crisis_years)
    )
    return paths, window


def run(settings: Settings) -> pd.DataFrame:
    """Simulate, summarize, chart and publish Q3/Q4; returns the summary table.

    Implements: ST-401..405, ST-002.
    """
    cfg = load_strategy_config()
    paths, window = simulate(settings, cfg)
    summary = summarize(paths)
    q4 = recommendation(summary)
    processed = resolve_repo_path(settings.paths.data_processed)
    summary.to_parquet(processed / SUMMARY_FILE, index=False)
    long_paths = pd.concat(
        [
            frame.rename_axis("path")
            .reset_index()
            .melt(id_vars="path", var_name="strategy_id", value_name="cost_eur")
            .assign(variant=v)
            for v, frame in paths.items()
        ],
        ignore_index=True,
    )
    long_paths.to_parquet(processed / PATHS_FILE, index=False)
    summary.round(2).to_csv(strategies_dir(settings) / "forward_risk_summary.csv", index=False)
    _fan_chart(paths["unconditional"], summary, window, settings)
    _risk_return_chart(summary, settings)
    _report(settings, summary, q4, window, cfg.forward.n_paths)
    write_ssot_rows(
        _ssot_rows(summary, q4, window, cfg.forward.n_paths), "strategies_forward", settings
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.forward_risk`` (ST-002).

    Implements: ST-002.
    """
    argparse.ArgumentParser(
        prog="python -m epra.strategies.forward_risk", description=__doc__.splitlines()[0]
    ).parse_args(argv)
    common_logging.setup()
    run(load_settings())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
