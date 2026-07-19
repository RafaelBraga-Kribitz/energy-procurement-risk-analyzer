"""Logging setup — stdlib logging, one canonical format.

Implements: EN-060 (format, INFO to stdout, optional ingestion logfile),
supports ING-008 (per-request log lines are emitted by the ingest modules).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def setup(level: int = logging.INFO, logfile: Path | None = None) -> None:
    """Configure root logging: INFO to stdout; optionally also to ``logfile``.

    Idempotent — repeated calls replace handlers instead of stacking them, so
    pipeline steps can each call setup() safely (EN-050 idempotency spirit).
    Ingestion passes ``reports/ingestion/ingest_<date>.log`` as ``logfile``.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(LOG_FORMAT)
    stream = logging.StreamHandler(stream=sys.stdout)
    stream.setFormatter(formatter)
    root.addHandler(stream)

    if logfile is not None:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(logfile, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    root.setLevel(level)
