"""Shared analytics I/O - mart loaders, RP-701/702 PNG stamp, SSOT producer.

All A1-A4 ``run()`` paths read DuckDB marts (never raw parquet) and write
artifacts only through this module.

Implements: AN preamble, AN-703, RP-701, RP-702, D-01..D-03.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from epra.common.config import REPO_ROOT, Settings
from epra.common.db import connect
from epra.report.style import DPI, FIGSIZE, SOURCE_NOTE

SQL_PRICE_HOURLY = "select * from marts.fct_price_hourly"
SQL_PRICE_DAILY = "select * from marts.fct_price_daily"

SSOT_COLUMNS = ("key", "value", "unit", "tag", "produced_by")

ARTIFACT_NAMES: frozenset[str] = frozenset(
    {
        "a1_annual_summary.md",
        "a1_heatmap_hour_month.png",
        "a1_duration_curves.png",
        "a1_negative_hours.png",
        "a2_spread_monthly.png",
        "a2_spread_summary.md",
        "a3_realized_vol.png",
        "a3_regimes.png",
        "a3_regime_stats.md",
        "a3_garch_vs_realized.png",
        "a4_load_vs_hdd.png",
        "a4_load_weather.md",
    }
)


def analytics_dir(settings: Settings) -> Path:
    """``reports/analytics`` under settings (absolute)."""
    reports = settings.paths.reports
    root = reports if reports.is_absolute() else REPO_ROOT / reports
    return root / "analytics"


def processed_dir(settings: Settings) -> Path:
    path = settings.paths.data_processed
    return path if path.is_absolute() else REPO_ROOT / path


def _fetch(settings: Settings, sql: str) -> pd.DataFrame:
    """Run ``sql`` read-only; empty result raises with the SQL text.

    Implements: D-01.
    """
    con = connect(settings, read_only=True)
    try:
        frame = con.execute(sql).fetchdf()
    finally:
        con.close()
    if frame.empty:
        raise RuntimeError(f"SQL returned empty: {sql}")
    return frame


def load_price_hourly(settings: Settings) -> pd.DataFrame:
    """Load ``marts.fct_price_hourly``.

    Implements: AN preamble, D-01.
    """
    return _fetch(settings, SQL_PRICE_HOURLY)


def load_price_daily(settings: Settings) -> pd.DataFrame:
    """Load ``marts.fct_price_daily``.

    Implements: AN preamble, D-01.
    """
    return _fetch(settings, SQL_PRICE_DAILY)


def stamp_rp702(fig: Figure, *, tag: str = "VERIFIED") -> None:
    """Apply RP-701 size and RP-702 source note + epistemic tag.

    Implements: RP-701, RP-702.
    """
    fig.set_size_inches(*FIGSIZE)
    fig.text(0.01, 0.01, SOURCE_NOTE, fontsize=8)
    fig.text(0.99, 0.01, tag, ha="right", fontsize=8)


def save_png(fig: Figure, path: Path, *, tag: str = "VERIFIED") -> None:
    """Stamp RP-702 and write PNG at RP-701 dpi.

    Implements: RP-701, RP-702.
    """
    stamp_rp702(fig, tag=tag)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def write_markdown(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def write_ssot_rows(rows: list[dict[str, object]], settings: Settings) -> Path:
    """Atomic write of ``ssot_inputs_analytics.parquet``.

    Implements: AN-703, D-03.
    """
    frame = pd.DataFrame(rows, columns=list(SSOT_COLUMNS))
    if list(frame.columns) != list(SSOT_COLUMNS):
        raise ValueError(f"SSOT columns must be {SSOT_COLUMNS}, got {list(frame.columns)}")
    if not frame.empty and (frame["tag"] != "VERIFIED").any():
        raise ValueError("analytics SSOT rows must have tag=VERIFIED")
    path = processed_dir(settings) / "ssot_inputs_analytics.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    frame.to_parquet(tmp_path, index=False, engine="pyarrow")
    os.replace(tmp_path, path)
    return path
