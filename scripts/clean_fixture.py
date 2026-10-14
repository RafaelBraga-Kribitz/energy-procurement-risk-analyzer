"""Remove synthetic fixture data before a real-data run (ADR-018 safeguard).

Deletes ``data/raw``, ``data/processed`` and the warehouse ONLY when the fixture
marker ``data/raw/_SYNTHETIC_FIXTURE.txt`` is present, so real ingested data can
never be deleted by this script. ``data/manual`` (the reconciled ÖSPI CSV) and
``data/cache`` are never touched.

Usage: ``uv run python scripts/clean_fixture.py``  (``make clean-fixture``)
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Sequence

from epra.common.config import Settings, load_settings, resolve_repo_path
from epra.common.db import warehouse_path
from epra.common.provenance import fixture_marker_path, is_fixture_run


def clean(settings: Settings) -> list[str]:
    """Delete fixture-derived data; returns what was removed (empty if no marker)."""
    if not is_fixture_run(settings):
        return []
    removed = []
    for root in (settings.paths.data_raw, settings.paths.data_processed):
        path = resolve_repo_path(root)
        for child in path.iterdir():
            if child.name == ".gitkeep":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
            removed.append(str(child))
    db = warehouse_path(settings)
    for candidate in (db, db.with_name(db.name + ".wal")):
        if candidate.exists():
            candidate.unlink()
            removed.append(str(candidate))
    assert not fixture_marker_path(settings).exists()
    return removed


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    del argv
    removed = clean(load_settings())
    print(
        f"removed {len(removed)} fixture paths" if removed else "no fixture marker: nothing removed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
