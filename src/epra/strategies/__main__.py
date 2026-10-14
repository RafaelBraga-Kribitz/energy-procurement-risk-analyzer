"""``python -m epra.strategies`` — ``make simulate``: retrospective → forward → ST-602.

Exit 1 when any ST-602 sanity relation fails, so ``make all`` stops loudly.

Implements: ST-002, ST-602.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from epra.common import logging as common_logging
from epra.common.config import load_settings
from epra.strategies import forward_risk, retrospective
from epra.strategies.gates import sanity_failures

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run both engines and the ST-602 gate.

    Implements: ST-002, ST-602.
    """
    del argv
    common_logging.setup()
    settings = load_settings()
    annual = retrospective.run(settings)
    forward = forward_risk.run(settings)
    failures = sanity_failures(annual, forward)
    for failure in failures:
        logger.error("ST-602 %s", failure)
    if failures:
        return 1
    logger.info("ST-602 sanity relations (a)(b)(c): PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
