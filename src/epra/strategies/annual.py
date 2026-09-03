"""Annual summary, ST-602(a), parquet dual-write, ST-304 charts (T6.05).

Implements: ST-001, ST-301, ST-302, ST-304, ST-602, D-05, D-06.
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

from epra.analytics._kit import frame_to_markdown, save_png, write_markdown
from epra.common.config import REPO_ROOT, Settings
from epra.report.style import STRATEGY_COLORS
from epra.strategies.align import processed_dir
from epra.strategies.retrospective import LP050_SENTENCE, ST502_SENTENCE

St602aStatus = Literal["pass", "fail", "skip"]
PARQUET_COLS = (
    "year_local",
    "month_local",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
    "unit_cost_eur_mwh",
)


@dataclass(frozen=True)
class St602aResult:
    """2022 S1 > S3 when both years exist; skip if 2022 incomplete.

    Implements: ST-602, D-06.
    """

    status: St602aStatus
    reason: str


def _as_int(value: object) -> int:
    return int(cast(Any, value))


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


def check_st602a(annual: pd.DataFrame) -> St602aResult:
    """Fail-closed when 2022 S1 and S3 exist; skip otherwise.

    Implements: ST-602, D-06.
    """
    y = annual.loc[annual["year_local"] == 2022]
    ids = set(y["strategy_id"].astype(str))
    if "S1" not in ids or "S3" not in ids:
        return St602aResult("skip", "2022 S1/S3 incomplete")
    c1 = float(y.loc[y["strategy_id"] == "S1", "cost_eur"].sum())
    c3 = float(y.loc[y["strategy_id"] == "S3", "cost_eur"].sum())
    if c1 > c3:
        return St602aResult("pass", f"2022 S1 {c1} > S3 {c3}")
    return St602aResult("fail", f"2022 S1 {c1} <= S3 {c3}; debug calibration (T-5)")


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


def _year_cost(annual: pd.DataFrame, year: int, strategy_id: str) -> float:
    mask = (annual["year_local"] == year) & (annual["strategy_id"] == strategy_id)
    return float(annual.loc[mask, "cost_eur"].sum())


def render_annual_charts(annual: pd.DataFrame, settings: Settings) -> None:
    """Grouped bar + cumulative line (ST-304).

    Implements: ST-304, ST-502, LP-050.
    """
    out = strategies_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    years = sorted(_as_int(y) for y in annual["year_local"].unique())
    present = set(annual["strategy_id"].astype(str))
    ids = [sid for sid in STRATEGY_COLORS if sid in present]
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
    ax.legend()
    fig.text(0.01, 0.06, ST502_SENTENCE, fontsize=7)
    fig.text(0.01, 0.03, LP050_SENTENCE, fontsize=7)
    save_png(fig, out / "s5_annual_costs.png", tag="CALIBRATED")

    fig2, ax2 = plt.subplots()
    for sid in ids:
        sub = annual.loc[annual["strategy_id"] == sid].sort_values("year_local")
        ax2.plot(
            sub["year_local"],
            sub["cost_eur"].cumsum(),
            color=STRATEGY_COLORS[sid],
            label=sid,
        )
    ax2.set_ylabel("EUR cumulative")
    ax2.legend()
    fig2.text(0.01, 0.06, ST502_SENTENCE, fontsize=7)
    fig2.text(0.01, 0.03, LP050_SENTENCE, fontsize=7)
    save_png(fig2, out / "s5_cumulative.png", tag="CALIBRATED")


def write_unit_cost_md(annual: pd.DataFrame, settings: Settings) -> None:
    """Unit-cost table plus honesty sentences.

    Implements: ST-304, ST-502, LP-050.
    """
    body = frame_to_markdown(annual) + "\n\n" + ST502_SENTENCE + "\n\n" + LP050_SENTENCE + "\n"
    write_markdown(strategies_dir(settings) / "s5_unit_costs.md", body)
