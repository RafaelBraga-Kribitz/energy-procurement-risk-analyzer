"""Shared plumbing for the A1-A4 analytics modules (SPEC-04).

Analytics read DuckDB marts only (never raw files), write markdown + PNG to
``reports/analytics/`` and publish numbers via SSOT input rows (AN-703).

Implements: supports AN-701, AN-703, AN-704.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from epra.common.config import Settings, resolve_repo_path
from epra.common.db import connect
from epra.common.provenance import banner_lines


def analytics_dir(settings: Settings) -> Path:
    """``reports/analytics/`` (SPEC-04 §6)."""
    path = resolve_repo_path(settings.paths.reports) / "analytics"
    path.mkdir(parents=True, exist_ok=True)
    return path


def query(settings: Settings, sql: str) -> pd.DataFrame:
    """Run one read-only SQL statement against the warehouse marts."""
    con = connect(settings, read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def md_table(frame: pd.DataFrame, floatfmt: str = ".1f") -> str:
    """GitHub-markdown table without the tabulate dependency."""

    def cell(value: object) -> str:
        if isinstance(value, float):
            return format(value, floatfmt)
        return str(value)

    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    rule = "|" + "|".join("---:" if frame[c].dtype.kind in "fiu" else "---" for c in frame.columns)
    rows = ["| " + " | ".join(cell(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule + "|", *rows])


def write_markdown(settings: Settings, name: str, title: str, sections: list[str]) -> Path:
    """Write ``reports/analytics/<name>`` with the fixture banner when applicable.

    Implements: AN-704 (interpretation paragraph is the last section).
    """
    lines = [f"# {title}", "", *banner_lines(settings), *sections]
    path = analytics_dir(settings) / name
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def by_year(frame: pd.DataFrame, key: str = "year") -> dict[int, dict[str, float]]:
    """``{year: {column: value}}`` plain-Python view of a per-year table."""
    records = frame.to_dict("records")
    return {int(r[key]): {str(k): float(v) for k, v in r.items()} for r in records}


def complete_years(frame: pd.DataFrame, year_col: str = "year_local") -> list[int]:
    """Years with at least 8,700 priced hours — partial edge years are excluded
    from year-keyed SSOT rows so no partial-year number reads as annual."""
    counts = frame.groupby(year_col).size()
    return [int(y) for y, n in zip(counts.index, counts, strict=True) if n >= 8700]
