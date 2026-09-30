"""DuckDB warehouse access (DM-001).

One helper, one file: ``data/warehouse/epra.duckdb``. Transformation logic lives
in dbt (SPEC-02); Python code uses this connection to READ marts (SPEC-04/05)
and never to create model tables by hand.

Implements: DM-001 (single warehouse file), supports ST-001 (marts → pandas).
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

from epra.common.config import Settings, resolve_repo_path


def warehouse_path(settings: Settings) -> Path:
    """Absolute path of the DuckDB warehouse file.

    ``EPRA_DUCKDB_PATH`` (absolute path) overrides the configured path, as for
    dbt (`dbt/profiles.yml`), so Python readers and dbt always open one file.

    Implements: DM-001 (the single warehouse file location).
    """
    override = os.environ.get("EPRA_DUCKDB_PATH")
    return resolve_repo_path(Path(override) if override else settings.paths.warehouse)


def connect(settings: Settings, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open the project warehouse, creating its parent directory if needed.

    The session TimeZone is pinned to UTC, as in `dbt/profiles.yml`, so a
    TIMESTAMPTZ `ts_utc` renders and casts identically in Python and dbt.

    Implements: DM-001, DM-010 (ADR-014), ST-001 (Python reads marts here).
    """
    path = warehouse_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), read_only=read_only)
    con.execute("SET TimeZone = 'UTC'")  # same session zone as dbt (ADR-014, T-1)
    return con
