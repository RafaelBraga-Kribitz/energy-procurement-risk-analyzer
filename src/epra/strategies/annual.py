"""Annual summary, ST-602, parquet dual-write, ST-304 charts (T6.05).

Implements: ST-001, ST-204, ST-301, ST-302, ST-304, ST-602, D-05, D-06.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from epra.analytics._kit import frame_to_markdown, save_png, write_markdown
from epra.common.config import REPO_ROOT, Settings
from epra.report.style import STRATEGY_COLORS
from epra.strategies.align import processed_dir
from epra.strategies.retrospective import LP050_SENTENCE, ST502_SENTENCE

St602Status = Literal["pass", "fail", "skip"]
PARQUET_COLS = (
    "year_local",
    "month_local",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
    "unit_cost_eur_mwh",
)
KNOWN_REPORTS = ("s5_annual_costs.png", "s5_cumulative.png", "s5_unit_costs.md")
ST602B_TOL = 0.005


@dataclass(frozen=True)
class St602Result:
    """ST-602 skip / fail / pass, same shape as AN-304.

    Implements: ST-602, D-06.
    """

    status: St602Status
    reason: str


St602aResult = St602Result


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _as_float(value: object) -> float:
    return float(cast(Any, value))


def annual_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    """Year x strategy totals with rank and delta vs min cost.

    Implements: ST-301.
    """
    grouped = monthly.groupby(["year_local", "strategy_id"], as_index=False, sort=True).agg(
        volume_mwh=("volume_mwh", "sum"),
        cost_eur=("cost_eur", "sum"),
    )
    grouped["unit_cost_eur_mwh"] = grouped["cost_eur"] / grouped["volume_mwh"]
    mins = grouped.groupby("year_local")["cost_eur"].transform("min")
    grouped["delta_vs_min_eur"] = grouped["cost_eur"] - mins
    grouped["rank"] = grouped.groupby("year_local")["cost_eur"].rank(method="min").astype(int)
    return grouped


def wrong_strategy_costs(annual: pd.DataFrame) -> pd.DataFrame:
    """max-min cost per year (ST-302).

    Implements: ST-302.
    """
    span = annual.groupby("year_local", as_index=False).agg(
        cost_min=("cost_eur", "min"), cost_max=("cost_eur", "max")
    )
    span["wrong_strategy_cost_eur"] = span["cost_max"] - span["cost_min"]
    return span


def check_st602a(annual: pd.DataFrame) -> St602Result:
    """Fail-closed when 2022 S1 and S3 exist; skip otherwise.

    Implements: ST-602, D-06.
    """
    y = annual.loc[annual["year_local"] == 2022]
    ids = set(y["strategy_id"].astype(str))
    if "S1" not in ids or "S3" not in ids:
        return St602Result("skip", "2022 S1/S3 incomplete")
    c1 = float(y.loc[y["strategy_id"] == "S1", "cost_eur"].sum())
    c3 = float(y.loc[y["strategy_id"] == "S3", "cost_eur"].sum())
    if c1 > c3:
        return St602Result("pass", f"2022 S1 {c1} > S3 {c3}")
    return St602Result("fail", f"2022 S1 {c1} <= S3 {c3}; debug calibration (T-5)")


def check_st602b(annual: pd.DataFrame) -> St602Result:
    """Hybrid S4_50 sits between S1 and S3 each year (±0.5%).

    Implements: ST-602.
    """
    checked = 0
    for year, chunk in annual.groupby("year_local", sort=True):
        ids = set(chunk["strategy_id"].astype(str))
        if not {"S1", "S3", "S4_50"} <= ids:
            continue
        checked += 1
        c1 = float(chunk.loc[chunk["strategy_id"] == "S1", "cost_eur"].sum())
        c3 = float(chunk.loc[chunk["strategy_id"] == "S3", "cost_eur"].sum())
        c4 = float(chunk.loc[chunk["strategy_id"] == "S4_50", "cost_eur"].sum())
        lo, hi = (min(c1, c3), max(c1, c3))
        if c4 + abs(hi) * ST602B_TOL < lo or c4 - abs(hi) * ST602B_TOL > hi:
            return St602Result(
                "fail",
                f"{_as_int(year)} S4_50 {c4} outside [{lo}, {hi}] ±{ST602B_TOL:.1%}",
            )
    if checked == 0:
        return St602Result("skip", "no year with S1/S3/S4_50")
    return St602Result("pass", f"S4_50 between S1 and S3 in {checked} year(s)")


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    frame.to_parquet(tmp, index=False, engine="pyarrow")
    os.replace(tmp, path)


def write_ssot_parquet(frame: pd.DataFrame, path: Path) -> None:
    """Atomic parquet write for strategy SSOT producer rows."""
    _atomic_parquet(frame, path)


def write_strategy_costs(monthly: pd.DataFrame, settings: Settings) -> Path:
    """Dual-write ST-001 file and ADR-010 dbt glob (D-05).

    Implements: ST-001, D-05.
    """
    out = monthly.loc[:, list(PARQUET_COLS)].copy()
    out["year_local"] = out["year_local"].astype("int64")
    out["month_local"] = out["month_local"].astype("int64")
    root = processed_dir(settings)
    glob_dir = root / "procurement_cost_monthly"
    if glob_dir.exists():
        shutil.rmtree(glob_dir)
    canonical = root / "strategy_costs_monthly.parquet"
    _atomic_parquet(out, canonical)
    _atomic_parquet(out, glob_dir / "strategy_costs_monthly.parquet")
    return canonical


def strategies_dir(settings: Settings) -> Path:
    reports = settings.paths.reports
    root = reports if reports.is_absolute() else REPO_ROOT / reports
    return root / "strategies"


def wipe_known_reports(settings: Settings) -> None:
    """Remove known ST-304 filenames; leave other reports (e.g. sensitivities)."""
    out = strategies_dir(settings)
    if not out.is_dir():
        return
    for name in KNOWN_REPORTS:
        path = out / name
        if path.is_file():
            path.unlink()


def _year_cost(annual: pd.DataFrame, year: int, strategy_id: str) -> float:
    mask = (annual["year_local"] == year) & (annual["strategy_id"] == strategy_id)
    return float(annual.loc[mask, "cost_eur"].sum())


def _strategy_ids(annual: pd.DataFrame) -> list[str]:
    present = set(annual["strategy_id"].astype(str))
    return [sid for sid in STRATEGY_COLORS if sid in present]


def _caption(fig: Figure) -> None:
    fig.text(0.01, 0.06, ST502_SENTENCE, fontsize=7)
    fig.text(0.01, 0.03, LP050_SENTENCE, fontsize=7)


def figure_annual_costs(annual: pd.DataFrame) -> Figure:
    """Grouped bar of annual cost by strategy (ST-304).

    Implements: ST-304, ST-502, LP-050, RP-704.
    """
    years = sorted(_as_int(y) for y in annual["year_local"].unique())
    ids = _strategy_ids(annual)
    fig, ax = plt.subplots()
    width = 0.12
    x0 = range(len(years))
    for i, sid in enumerate(ids):
        vals = [_year_cost(annual, y, sid) for y in years]
        ax.bar(
            [x + i * width for x in x0],
            vals,
            width=width,
            color=STRATEGY_COLORS[sid],
            label=sid,
        )
    ax.set_xticks([x + width * (len(ids) - 1) / 2 for x in x0], [str(y) for y in years])
    ax.set_ylabel("EUR")
    ax.set_title("Annual procurement cost by strategy")
    ax.legend()
    _caption(fig)
    return fig


def figure_cumulative(annual: pd.DataFrame) -> Figure:
    """Cumulative annual cost lines (ST-304).

    Implements: ST-304, ST-502, LP-050, RP-704.
    """
    fig, ax = plt.subplots()
    for sid in _strategy_ids(annual):
        sub = annual.loc[annual["strategy_id"] == sid].sort_values("year_local")
        ax.plot(
            sub["year_local"],
            sub["cost_eur"].cumsum(),
            color=STRATEGY_COLORS[sid],
            label=sid,
        )
    ax.set_ylabel("EUR cumulative")
    ax.set_title("Cumulative procurement cost by strategy")
    ax.legend()
    _caption(fig)
    return fig


def render_annual_charts(annual: pd.DataFrame, settings: Settings) -> None:
    """Grouped bar + cumulative line (ST-304).

    Implements: ST-304, ST-502, LP-050.
    """
    out = strategies_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    save_png(figure_annual_costs(annual), out / "s5_annual_costs.png", tag="CALIBRATED")
    save_png(figure_cumulative(annual), out / "s5_cumulative.png", tag="CALIBRATED")


def unit_cost_prose(annual: pd.DataFrame) -> str:
    """Interpretation after the unit-cost table (AN-704 style, RP-703).

    Numbers are taken from ``annual``; missing years are omitted, not zero-filled.

    Implements: ST-304, ST-502, LP-050, AN-704, RP-703.
    """
    if annual.empty:
        return (
            "No strategy years are present in this run, so there is no annual "
            "cost matrix and no wrong-strategy euro headline to quote. "
            "Absent years stay omitted rather than written as zero cost. "
            f"{ST502_SENTENCE} {LP050_SENTENCE} "
            "Unit costs are annual cost divided by the shared ST-101 volume; "
            "ranks and delta_vs_min_eur come from the same table when rows exist. "
            "These figures are CALIBRATED contract proxies plus VERIFIED spot "
            "hours, not a supplier quote, and they are not Austrian market "
            "evidence until an operator warehouse run writes them."
        )
    parts: list[str] = []
    for rec in wrong_strategy_costs(annual).itertuples(index=False):
        year = _as_int(rec.year_local)
        span = _as_float(rec.wrong_strategy_cost_eur)
        parts.append(
            f"In {year} the wrong-strategy span is {span:.2f} EUR "
            f"(max annual cost {_as_float(rec.cost_max):.2f} minus min "
            f"{_as_float(rec.cost_min):.2f})."
        )
    for year_key, chunk in annual.groupby("year_local", sort=True):
        best = chunk.loc[chunk["cost_eur"].idxmin()]
        parts.append(
            f"Cheapest strategy in {_as_int(year_key)} is {best['strategy_id']} at "
            f"{_as_float(best['unit_cost_eur_mwh']):.4f} EUR/MWh on "
            f"{_as_float(best['volume_mwh']):.4f} MWh "
            f"(cost {_as_float(best['cost_eur']):.2f} EUR)."
        )
    parts.append(
        f"{ST502_SENTENCE} {LP050_SENTENCE} "
        "Unit costs are annual cost divided by the shared ST-101 volume so "
        "every strategy prices the same MWh. Ranks and delta_vs_min_eur are "
        "computed from that table; no missing year is filled with a zero cost. "
        "Spot hours are VERIFIED market prices; S2/S3/S4 euros are CALIBRATED "
        "ÖSPI-through-P_ref translations, not observed supplier invoices."
    )
    return " ".join(parts)


def write_unit_cost_md(annual: pd.DataFrame, settings: Settings) -> None:
    """Unit-cost table plus honesty sentences.

    Implements: ST-304, ST-502, LP-050.
    """
    body = f"# S5 unit costs (ST-304)\n\n{frame_to_markdown(annual)}\n\n{unit_cost_prose(annual)}\n"
    write_markdown(strategies_dir(settings) / "s5_unit_costs.md", body)
