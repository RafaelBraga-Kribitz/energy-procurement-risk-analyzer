"""clean_fixture.py deletes fixture data only when the marker is present."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from epra.common.config import REPO_ROOT, Settings

_SPEC = importlib.util.spec_from_file_location(
    "clean_fixture", REPO_ROOT / "scripts" / "clean_fixture.py"
)
assert _SPEC is not None and _SPEC.loader is not None
CLEAN = importlib.util.module_from_spec(_SPEC)
sys.modules["clean_fixture"] = CLEAN
_SPEC.loader.exec_module(CLEAN)


def _settings(tmp_settings: Settings, tmp_path: Path) -> Settings:
    paths = tmp_settings.paths.model_copy(
        update={"data_processed": tmp_path / "processed", "warehouse": tmp_path / "w" / "e.duckdb"}
    )
    return tmp_settings.model_copy(update={"paths": paths})


def test_real_data_is_never_removed(tmp_settings: Settings, tmp_path: Path) -> None:
    settings = _settings(tmp_settings, tmp_path)
    real = settings.paths.data_raw / "entsoe_prices_at" / "x.parquet"
    real.parent.mkdir(parents=True)
    real.write_bytes(b"real")
    assert CLEAN.clean(settings) == []
    assert real.exists()


def test_fixture_data_is_removed_manual_kept(tmp_settings: Settings, tmp_path: Path) -> None:
    settings = _settings(tmp_settings, tmp_path)
    raw = settings.paths.data_raw
    (raw / "entsoe_prices_at").mkdir(parents=True)
    (raw / "entsoe_prices_at" / "x.parquet").write_bytes(b"synthetic")
    (raw / "_SYNTHETIC_FIXTURE.txt").write_text("fixture", encoding="utf-8")
    (raw / ".gitkeep").write_text("", encoding="utf-8")
    settings.paths.data_processed.mkdir()
    (settings.paths.data_processed / "p.parquet").write_bytes(b"x")
    settings.paths.warehouse.parent.mkdir()
    settings.paths.warehouse.write_bytes(b"db")
    manual = settings.paths.data_manual / "oespi_monthly.csv"
    manual.parent.mkdir(parents=True)
    manual.write_text("month\n", encoding="utf-8")
    removed = CLEAN.clean(settings)
    assert len(removed) == 4
    assert sorted(p.name for p in raw.iterdir()) == [".gitkeep"]
    assert manual.exists() and not settings.paths.warehouse.exists()
