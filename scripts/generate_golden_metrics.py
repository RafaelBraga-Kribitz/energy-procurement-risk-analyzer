"""Regenerate golden test values (EN-072, ST-601, LP-040).

Goldens are regenerated ONLY by this script, ONLY in a PR that explains why,
with a diff of old vs new values (AGENTS.md §2 item 6 — human approves).

Targets:

- ``profile``: ``tests/golden/consumer_load_2023.sha256`` — sha256 of the 2023
  slice of the StyriaMetal profile built on a 2022-2024 calendar (LP-040).
- ``strategies``: ``tests/golden/strategy_annual_summary.json`` (ST-601, M6).

Usage: ``python scripts/generate_golden_metrics.py --target profile``

Implements: EN-072 regeneration path, LP-040, ST-601.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date

from epra.common.config import REPO_ROOT, load_consumer_profile
from epra.consumer import profile
from epra.ingest.calendar import calendar_frame

GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
PROFILE_GOLDEN = GOLDEN_DIR / "consumer_load_2023.sha256"
#: LP-040 golden window: 2023 sits inside a complete-year calendar.
PROFILE_WINDOW = (date(2022, 1, 1), date(2024, 12, 31))
PROFILE_GOLDEN_YEAR = 2023


def regenerate_profile_golden() -> str:
    """Rewrite the LP-040 checksum file; returns the new checksum.

    Implements: LP-040.
    """
    built = profile.build_profile(calendar_frame(*PROFILE_WINDOW), load_consumer_profile())
    checksum = profile.year_checksum(built, PROFILE_GOLDEN_YEAR)
    old = PROFILE_GOLDEN.read_text(encoding="utf-8").strip() if PROFILE_GOLDEN.exists() else None
    PROFILE_GOLDEN.write_text(checksum + "\n", encoding="utf-8")
    print(f"profile golden: {old} -> {checksum}")
    return checksum


def regenerate_strategy_golden() -> None:
    """ST-601 golden — lands with M6."""
    raise NotImplementedError("strategy goldens land with M6 (ST-601)")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Implements: EN-072.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", choices=["profile", "strategies"], required=True)
    args = parser.parse_args(argv)
    if args.target == "profile":
        regenerate_profile_golden()
    else:
        regenerate_strategy_golden()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
