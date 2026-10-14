"""Data provenance: real ingested data vs the synthetic CI fixture (ADR-018).

``scripts/bootstrap_fixture_warehouse.py`` drops a marker file into
``data/raw/`` whenever it synthesizes data. Real ingestion never writes it, and
the bootstrap refuses to write over populated real data, so the marker is a
reliable signal. Every published artifact built on fixture data carries
:data:`FIXTURE_BANNER` so a synthetic number can never pass as a result (A-2).

Implements: A-2 safeguard for ADR-016/ADR-018 fixture runs.
"""

from __future__ import annotations

from pathlib import Path

from epra.common.config import Settings, resolve_repo_path

FIXTURE_MARKER = "_SYNTHETIC_FIXTURE.txt"
FIXTURE_BANNER = (
    "FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real "
    "ENTSO-E data. Every number here exercises the pipeline only and is NOT a result."
)


def fixture_marker_path(settings: Settings) -> Path:
    """Location of the synthetic-data marker inside ``data/raw``."""
    return resolve_repo_path(settings.paths.data_raw) / FIXTURE_MARKER


def is_fixture_run(settings: Settings) -> bool:
    """True when ``data/raw`` holds synthetic fixture data (ADR-018)."""
    return fixture_marker_path(settings).exists()


def banner_lines(settings: Settings) -> list[str]:
    """Markdown banner (blockquote + blank line) for fixture runs, else nothing."""
    return [f"> **{FIXTURE_BANNER}**", ""] if is_fixture_run(settings) else []
