"""Assemble ``reports/NUMERIC_SSOT.md`` from producer parquets (GV-301).

Never recomputes strategy costs. Duplicate keys raise. ``updated_at`` is
max input mtime ISO-8601 UTC (ADR-016). ``data_last_month`` is the latest
complete mart month (VERIFIED), not ENTSO-E raw.

Implements: GV-301, GV-302, ST-204, ADR-016, D-16, D-17, E-2.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd

from epra.analytics._kit import frame_to_markdown, write_markdown
from epra.common.config import REPO_ROOT, Settings
from epra.common.db import connect
from epra.strategies.align import STRATEGY_IDS, processed_dir

SSOT_COLUMNS = ("key", "value", "unit", "tag", "produced_by")
PRODUCER_GLOB = "ssot_inputs_*.parquet"
SQL_LAST_MONTH = (
    "select year_local, month_local from marts.fct_price_hourly "
    "order by year_local desc, month_local desc limit 1"
)
CORE_GV302 = (
    "p_ref_base",
    "p_ref_peak",
    "oespi_base_ref",
    "oespi_peak_ref",
    "consumer_peak_share",
    "garch_persistence",
    "data_last_month",
)
YEAR_STEMS = (
    "wrong_strategy_cost",
    "annual_mean_price",
    "neg_hours",
    "spread_mean",
)


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def reports_dir(settings: Settings) -> Path:
    reports = settings.paths.reports
    return reports if reports.is_absolute() else REPO_ROOT / reports


def iso_mtime_utc(mtime: float) -> str:
    """Second-precision ISO-8601 UTC with Z (ADR-016).

    Implements: ADR-016, D-17.
    """
    stamp = datetime.fromtimestamp(int(mtime), tz=UTC)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_producer_frames(settings: Settings) -> tuple[list[pd.DataFrame], list[Path]]:
    """Read ``ssot_inputs_*.parquet``; missing glob raises listing the path."""
    root = processed_dir(settings)
    paths = sorted(root.glob(PRODUCER_GLOB))
    if not paths:
        raise FileNotFoundError(
            f"no {PRODUCER_GLOB} under {root}; run profile/analyze/simulate first"
        )
    return [pd.read_parquet(path) for path in paths], paths


def _year_suffix(key: str) -> int | None:
    if len(key) < 5 or key[-5] != "_" or not key[-4:].isdigit():
        return None
    return int(key[-4:])


def years_in_keys(keys: Iterable[str]) -> set[int]:
    """Local years present on GV-302 year-suffixed keys (never invent missing years)."""
    years: set[int] = set()
    for raw in keys:
        key = str(raw)
        year = _year_suffix(key)
        if year is None:
            continue
        if key.startswith("cost_") or any(key.startswith(f"{stem}_") for stem in YEAR_STEMS):
            years.add(year)
    return years


def missing_gv302_keys(keys: Iterable[str]) -> list[str]:
    """Year-adaptive GV-302 gaps. Absent years are omitted, not zero-filled.

    Implements: GV-302, ST-204, D-16.
    """
    present = {str(k) for k in keys}
    missing = [key for key in CORE_GV302 if key not in present]
    years = years_in_keys(present)
    if years and "wrong_strategy_cost_total" not in present:
        missing.append("wrong_strategy_cost_total")
    if years and "best_strategy_5yr" not in present:
        missing.append("best_strategy_5yr")
    for year in sorted(years):
        for stem in YEAR_STEMS:
            key = f"{stem}_{year}"
            if key not in present:
                missing.append(key)
        missing.extend(
            f"cost_{sid}_{year}" for sid in STRATEGY_IDS if f"cost_{sid}_{year}" not in present
        )
    for sid in STRATEGY_IDS:
        for stem in ("p95_next12m", "cvar95_next12m"):
            key = f"{stem}_{sid}"
            if key not in present:
                missing.append(key)
    return missing


def require_gv302(frame: pd.DataFrame) -> None:
    missing = missing_gv302_keys(frame["key"].astype(str))
    if missing:
        raise ValueError(f"GV-302 missing keys: {missing}")


def concat_producers(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """Stack producer rows; duplicate keys raise (GV-302 exactly once).

    Implements: GV-302, E-2.
    """
    parts = [frame.loc[:, list(SSOT_COLUMNS)].copy() for frame in frames]
    if not parts:
        raise ValueError("no SSOT producer frames")
    stacked = pd.concat(parts, ignore_index=True)
    dupes = stacked.loc[stacked["key"].duplicated(keep=False), "key"]
    if not dupes.empty:
        keys = sorted({str(k) for k in dupes})
        raise ValueError(f"duplicate SSOT keys: {keys}")
    return stacked.sort_values("key", kind="mergesort").reset_index(drop=True)


def mart_last_month(settings: Settings) -> str:
    """Latest ``year_local``-``month_local`` in ``fct_price_hourly`` as YYYY-MM.

    Implements: D-16.
    """
    con = connect(settings, read_only=True)
    try:
        frame = con.execute(SQL_LAST_MONTH).fetchdf()
    finally:
        con.close()
    if frame.empty:
        raise RuntimeError(f"SQL returned empty: {SQL_LAST_MONTH}")
    year = _as_int(frame.iloc[0]["year_local"])
    month = _as_int(frame.iloc[0]["month_local"])
    return f"{year:04d}-{month:02d}"


def _data_last_month_row(value: str) -> dict[str, object]:
    return {
        "key": "data_last_month",
        "value": value,
        "unit": "YYYY-MM",
        "tag": "VERIFIED",
        "produced_by": "epra.report.ssot",
    }


def _best_strategy_row(frame: pd.DataFrame) -> dict[str, object] | None:
    prefix = "cost_"
    costs: dict[str, float] = {}
    for rec in frame.itertuples(index=False):
        key = str(rec.key)
        if not key.startswith(prefix):
            continue
        body = key[len(prefix) :]
        if "_" not in body:
            continue
        sid, _year = body.rsplit("_", 1)
        costs[sid] = costs.get(sid, 0.0) + float(cast(Any, rec.value))
    if not costs:
        return None
    best = min(costs, key=lambda sid: (costs[sid], sid))
    return {
        "key": "best_strategy_5yr",
        "value": best,
        "unit": "strategy_id",
        "tag": "CALIBRATED",
        "produced_by": "epra.report.ssot",
    }


def render_ssot(frame: pd.DataFrame, updated_at: str) -> str:
    """Markdown table with ADR-016 ``updated_at`` on every row (E-2: tags copied)."""
    out = frame.copy()
    out["updated_at"] = updated_at
    table = frame_to_markdown(out)
    return "# NUMERIC_SSOT\n\n" + table + "\n"


def assemble(
    settings: Settings,
    *,
    frames: Sequence[pd.DataFrame] | None = None,
    data_last_month: str | None = None,
    mtimes: Sequence[float] | None = None,
    check_complete: bool | None = None,
) -> str:
    """Write ``reports/NUMERIC_SSOT.md``; return the markdown body.

    Does not recompute strategy costs. ``check_complete`` defaults True when
    reading producer parquets (ST-604) and False when frames are injected.

    Implements: GV-301, GV-302, ADR-016, D-16, D-17.
    """
    paths: list[Path] = []
    from_disk = frames is None
    if frames is None:
        frames, paths = load_producer_frames(settings)
    if check_complete is None:
        check_complete = from_disk
    stacked = concat_producers(frames)
    last = data_last_month if data_last_month is not None else mart_last_month(settings)
    present = set(stacked["key"].astype(str))
    extra: list[dict[str, object]] = []
    if "data_last_month" not in present:
        extra.append(_data_last_month_row(last))
    best = _best_strategy_row(stacked)
    if best is not None and "best_strategy_5yr" not in present:
        extra.append(best)
    if extra:
        stacked = concat_producers([stacked, pd.DataFrame(extra)])
    if check_complete:
        require_gv302(stacked)
    if mtimes is None:
        mtimes = [path.stat().st_mtime for path in paths] or [0.0]
    updated = iso_mtime_utc(max(mtimes) if mtimes else 0.0)
    body = render_ssot(stacked, updated)
    dest = reports_dir(settings) / "NUMERIC_SSOT.md"
    write_markdown(dest, body)
    return body


def main(argv: Sequence[str] | None = None) -> int:
    """CLI used by ``scripts/generate_ssot.py`` (thin shell)."""
    import argparse

    from epra.common.config import load_settings
    from epra.common.logging import setup

    parser = argparse.ArgumentParser(prog="python -m epra.report.ssot")
    parser.parse_args(argv)
    setup()
    assemble(load_settings())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
