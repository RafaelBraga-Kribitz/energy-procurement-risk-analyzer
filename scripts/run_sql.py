"""Run one file from sql/ against the warehouse and print the result.

``{processed}`` in the file is replaced by the absolute ``data/processed`` path.

Usage: ``uv run python scripts/run_sql.py sql/q1_wrong_strategy_cost.sql``

Implements: ADR-020 §1 (headline answers readable as SQL).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from epra.common.config import Settings, load_settings, resolve_repo_path
from epra.common.db import read_sql


def render(path: Path, settings: Settings) -> str:
    """The SQL text with ``{processed}`` substituted."""
    processed = resolve_repo_path(settings.paths.data_processed).as_posix()
    return path.read_text(encoding="utf-8").replace("{processed}", processed)


def run_file(path: Path, settings: Settings) -> pd.DataFrame:
    """Execute one headline query read-only."""
    return read_sql(settings, render(path, settings))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(run_file(args.file, load_settings()).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
