"""``python -m epra.analytics`` — run A1 → A2 → A4 → A3 (``make analyze``).

Build/run order per AGENTS.md M5 (regimes last). Exit 1 if the AN-304 regime
sanity gate fails, so ``make all`` stops loudly.

Implements: AN-701, AN-702.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from epra.analytics import descriptive, regimes, spread, weather
from epra.common import logging as common_logging
from epra.common.config import load_settings

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run every analytics module; returns 1 on an AN-304 failure.

    Implements: AN-701, AN-702.
    """
    del argv
    common_logging.setup()
    settings = load_settings()
    descriptive.run(settings)
    spread.run(settings)
    weather.run(settings)
    try:
        gate = regimes.run(settings)
    except regimes.RegimeGateFailure as exc:
        logger.error("%s", exc)
        return 1
    logger.info(
        "analytics done; AN-304 top-2 %.1f%%, calm-2019 %.1f%%",
        100 * gate.crisis_top2_share,
        100 * gate.calm_2019_share,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
