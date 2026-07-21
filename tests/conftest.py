"""Shared pytest fixtures for ingest tests — tmp_path-backed Settings and the
committed ENTSO-E fixture directory.

Mirrors the `tmp_path` + `model_copy` pattern already used in
`tests/unit/test_logging_and_db.py`: ingest and validation tests never write
into the repo's real `data/raw/`, `data/cache/`, or `reports/` trees — every
fixture here redirects those paths under pytest's `tmp_path` so tests are
isolated and ING-003 idempotency (same input -> same output, no dupes) is
actually checkable against a throwaway directory instead of shared state.

No production ingest logic lives here — infrastructure only (Wave 0, 02-01).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epra.common.config import REPO_ROOT, Settings, load_settings

#: Directory of committed ENTSO-E XML/parquet fixtures (ING-070, T1.03a).
_ENTSOE_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "entsoe"

_ENTSOE_FIXTURES_README = """# ENTSO-E test fixtures

Committed XML/parquet samples for `tests/test_raw_contracts.py` and the
ENTSO-E parser unit tests (ING-070, T1.03a). Expected coverage, each file
<= 200 rows and generated once from real ENTSO-E pulls so CI never needs
network access:

- PT60M day-ahead prices (AT and DE-LU)
- PT15M day-ahead prices (post SDAC 15-min switch)
- curveType A03 (forward-fill within period, ING-063)
- a DST transition day (last Sunday of March / October, ING-080)
- AT actual load (PT15M)
- AT generation per type, long format (ING-032)
- an `Acknowledgement_MarketDocument` (no-data) response

Populate this directory when implementing the fetch/parse plans; do not
commit synthetic data that isn't a fixture-worthy sample of a real response.
"""


def _ensure_entsoe_fixtures_dir() -> Path:
    """Create `tests/fixtures/entsoe/` with a placeholder README if it's empty.

    Runs at module import (collection) time so the directory exists on disk
    even before any fixture files are committed by later ingest plans.
    """
    _ENTSOE_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    readme = _ENTSOE_FIXTURES_DIR / "README.md"
    other_files = [p for p in _ENTSOE_FIXTURES_DIR.iterdir() if p.name != "README.md"]
    if not readme.exists() and not other_files:
        readme.write_text(_ENTSOE_FIXTURES_README, encoding="utf-8")
    return _ENTSOE_FIXTURES_DIR


_ensure_entsoe_fixtures_dir()


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    """`Settings` with `data_raw`, `data_cache`, and `reports` redirected to `tmp_path`.

    Ingest and validation tests inject this instead of the real `Settings` so
    parquet writes, cache files, and validation reports never touch the repo's
    real `data/` or `reports/` trees (mirrors `test_db_connect_creates_warehouse`
    in `tests/unit/test_logging_and_db.py`).
    """
    settings = load_settings()
    paths = settings.paths.model_copy(
        update={
            "data_raw": tmp_path / "data" / "raw",
            "data_cache": tmp_path / "data" / "cache",
            "reports": tmp_path / "reports",
        }
    )
    return settings.model_copy(update={"paths": paths})


@pytest.fixture
def entsoe_fixtures_dir() -> Path:
    """Path to the committed ENTSO-E fixture directory (ING-070, T1.03a)."""
    return _ENTSOE_FIXTURES_DIR
