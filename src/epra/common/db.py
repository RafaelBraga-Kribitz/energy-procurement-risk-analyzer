"""DuckDB warehouse access (DM-001).

One helper, one file: ``data/warehouse/epra.duckdb``. Transformation logic lives
in dbt (SPEC-02); Python code uses this connection to READ marts (SPEC-04/05)
and never to create model tables by hand.

Implements: DM-001 (single warehouse file), supports ST-001 (marts → pandas).
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from epra.common.config import REPO_ROOT, Settings


def warehouse_path(settings: Settings) -> Path:
    """Absolute path of the DuckDB warehouse file."""
    p = settings.paths.warehouse
    return p if p.is_absolute() else REPO_ROOT / p


def connect(settings: Settings, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open the project warehouse, creating its parent directory if needed."""
    path = warehouse_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)
