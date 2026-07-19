"""Tests for epra.common.logging (EN-060) and epra.common.db (DM-001)."""

import logging
from pathlib import Path

from epra.common import db
from epra.common import logging as epra_logging
from epra.common.config import load_settings


def test_logging_setup_is_idempotent(tmp_path: Path) -> None:
    epra_logging.setup()
    epra_logging.setup()
    root = logging.getLogger()
    assert len(root.handlers) == 1  # handlers replaced, never stacked

    logfile = tmp_path / "sub" / "ingest_test.log"
    epra_logging.setup(logfile=logfile)
    assert len(root.handlers) == 2
    logging.getLogger("epra.test").info("hello EN-060")
    for handler in root.handlers:
        handler.flush()
    text = logfile.read_text(encoding="utf-8")
    assert "INFO epra.test hello EN-060" in text  # EN-060 format
    epra_logging.setup()  # reset to stdout-only for other tests


def test_db_connect_creates_warehouse(tmp_path: Path) -> None:
    settings = load_settings()
    paths = settings.paths.model_copy(update={"warehouse": tmp_path / "wh" / "epra.duckdb"})
    settings = settings.model_copy(update={"paths": paths})
    con = db.connect(settings)
    try:
        assert con.execute("select 42").fetchone() == (42,)
    finally:
        con.close()
    assert db.warehouse_path(settings).exists()
