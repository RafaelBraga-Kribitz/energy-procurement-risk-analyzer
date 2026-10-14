"""``python -m epra.report`` — ``make report``: data quality, executive charts,
EXEC_SUMMARY and the README result blocks (SPEC-06 §§1-6, ADR-020 §3).

Implements: RP-201..204, SPEC-06 §5/§6, ADR-020 §3.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from epra.common import logging as common_logging
from epra.common.config import load_settings
from epra.report import charts, data_quality, exec_summary

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Render every reporting artifact from marts, processed outputs and the SSOT.

    Implements: RP-201..204, SPEC-06 §5.
    """
    del argv
    common_logging.setup()
    settings = load_settings()
    logger.info("data quality -> %s", data_quality.run(settings))
    for path in charts.render_executive_charts(settings):
        logger.info("executive chart -> %s", path)
    logger.info("exec summary -> %s", exec_summary.run(settings))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
