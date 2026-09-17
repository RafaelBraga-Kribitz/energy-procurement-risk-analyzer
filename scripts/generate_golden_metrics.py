"""Regenerate ST-601 golden JSON. Refuses a dirty git tree (EN-072).

Writes ``tests/golden/strategy_annual_summary.json`` from the synthetic
helper (D-19) — not from a fixture warehouse and not Austrian market euros.

Implements: ST-601, EN-072, D-19.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from epra.common.config import REPO_ROOT
from epra.strategies._golden import synthetic_annual_payload

DEFAULT_OUTPUT = REPO_ROOT / "tests" / "golden" / "strategy_annual_summary.json"


def git_porcelain(cwd: Path) -> str:
    """``git status --porcelain`` stdout (empty iff clean)."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def write_golden(path: Path) -> None:
    payload = synthetic_annual_payload()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/generate_golden_metrics.py")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="destination JSON (default: tests/golden/strategy_annual_summary.json)",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=REPO_ROOT,
        help="git repo root for the dirty-tree check",
    )
    args = parser.parse_args(argv)
    if git_porcelain(args.cwd).strip():
        print(
            "refusing to regenerate goldens: git tree is dirty (EN-072)",
            file=sys.stderr,
        )
        return 1
    write_golden(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
