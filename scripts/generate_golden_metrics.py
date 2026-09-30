"""Regenerate golden test values (EN-072, ST-601, LP-040) — M4/M6.

Not yet implemented. Binding contract: EN-072. Goldens
(``tests/golden/strategy_annual_summary.json``, consumer profile checksum) are
regenerated ONLY by this script, ONLY in a PR that explains why, with a diff of
old vs new values (AGENTS.md §2 item 6 — human approves).

Implements (when built): EN-072 regeneration path.
"""

from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point — fails loudly until its milestone lands (AGENTS.md M0 rule)."""
    raise NotImplementedError("not implemented yet — M4/M6 (EN-072); see module docstring")


if __name__ == "__main__":
    raise SystemExit(main())
