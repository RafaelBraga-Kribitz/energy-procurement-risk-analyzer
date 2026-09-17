"""CLI: ``python -m epra.analytics`` - A1 -> A2 -> A4 -> A3 (SPEC-04 / WBS M5).

Does not invoke dbt. Missing warehouse exits 1.

Implements: EN-050, D-04, AN-701 orchestrator shell (module bodies in 06-02+).
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from epra.analytics import descriptive, regimes, spread, weather
from epra.common.config import load_settings
from epra.common.db import warehouse_path

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run A1 → A2 → A4 → A3. Missing warehouse → exit 1.

    Implements: D-04, EN-050.
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.analytics",
        description="Market analytics A1-A4 from DuckDB marts (SPEC-04).",
    )
    parser.parse_args(argv)

    settings = load_settings()
    path = warehouse_path(settings)
    if not path.is_file():
        msg = (
            f"warehouse not found at {path}. "
            "Run `make warehouse` first (analytics read marts only, D-01/D-04)."
        )
        print(f"ERROR: {msg}", file=sys.stderr)
        logger.error(msg)
        return 1

    descriptive.run(settings)
    spread.run(settings)
    weather.run(settings)
    regimes.run(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
