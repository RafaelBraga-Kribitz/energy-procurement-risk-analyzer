"""ADR-020 publish targets, tested with fakes — no network, no Azure SDK (EN-070)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import epra.cloud.__main__ as cli
from epra.cloud.targets import (
    AzureTarget,
    LocalTarget,
    azure_clients_from_env,
    create_table_sql,
    insert_sql,
    manifest,
)
from epra.common.config import Settings


class FakeBlob:
    def __init__(self) -> None:
        self.uploads: dict[str, bytes] = {}

    def get_blob_client(self, container: str, blob: str) -> FakeBlob._Client:
        return FakeBlob._Client(self, f"{container}/{blob}")

    class _Client:
        def __init__(self, parent: FakeBlob, name: str) -> None:
            self.parent, self.name = parent, name

        def upload_blob(self, handle: Any, overwrite: bool) -> None:
            assert overwrite
            self.parent.uploads[self.name] = handle.read()


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.batches: list[tuple[str, list[tuple[Any, ...]]]] = []
        self.fast_executemany = False

    def execute(self, sql: str) -> None:
        self.statements.append(sql)

    def executemany(self, sql: str, rows: list[tuple[Any, ...]]) -> None:
        assert self.fast_executemany
        self.batches.append((sql, rows))


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.cur, self.fail = FakeCursor(), fail
        self.committed = self.rolled_back = self.closed = False

    def cursor(self) -> FakeCursor:
        if self.fail:
            raise RuntimeError("sql down")
        return self.cur

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def files(tmp_path: Path) -> tuple[list[Path], list[Path], Path]:
    exports = tmp_path / "exports"
    exports.mkdir()
    pd.DataFrame(
        {
            "year": [2021, 2022],
            "cost_eur": [1.5, None],
            "strategy_id": ["S1", "S3"],
            "flag": [True, False],
        }
    ).to_csv(exports / "strategy_annual_summary.csv", index=False)
    raw = tmp_path / "raw" / "entsoe_prices_at" / "2022"
    raw.mkdir(parents=True)
    (raw / "m.parquet").write_bytes(b"PAR1")
    return sorted(exports.glob("*.csv")), [raw / "m.parquet"], tmp_path / "raw"


def test_local_target_writes_manifest(files: tuple[list[Path], list[Path], Path]) -> None:
    exports, _, _ = files
    report = LocalTarget(exports[0].parent).publish(exports, [], "2026-10-14")
    data = json.loads((exports[0].parent / "MANIFEST.json").read_text(encoding="utf-8"))
    assert report.target == "local"
    assert data["files"][0]["rows"] == 2 and len(data["files"][0]["sha256"]) == 64
    assert manifest(exports, "x")["run_id"] == "x"


def test_azure_target_uploads_and_loads(files: tuple[list[Path], list[Path], Path]) -> None:
    exports, raw, raw_root = files
    blob, conn = FakeBlob(), FakeConnection()
    report = AzureTarget(blob, lambda: conn, "epra", "epra", raw_root).publish(
        exports, raw, "2026-10-14"
    )
    assert set(blob.uploads) == {
        "epra/raw/entsoe_prices_at/2022/m.parquet",
        "epra/exports/2026-10-14/strategy_annual_summary.csv",
        "epra/exports/latest/strategy_annual_summary.csv",
    }
    assert report.tables == {"strategy_annual_summary": 2}
    assert any("CREATE TABLE [epra].[strategy_annual_summary]" in s for s in conn.cur.statements)
    sql, rows = conn.cur.batches[0]
    assert sql.startswith("INSERT INTO [epra].[strategy_annual_summary]")
    assert rows[1][1] is None  # NaN -> SQL NULL, never an invented value
    assert conn.committed and conn.closed and not conn.rolled_back


def test_azure_target_rolls_back_on_failure(files: tuple[list[Path], list[Path], Path]) -> None:
    exports, _, raw_root = files
    conn = FakeConnection(fail=True)
    with pytest.raises(RuntimeError, match="sql down"):
        AzureTarget(FakeBlob(), lambda: conn, "epra", "epra", raw_root).publish(exports, [], "r")
    assert conn.rolled_back and conn.closed


def test_ddl_types_and_insert() -> None:
    frame = pd.DataFrame({"a": [1.0], "b": [1], "c": ["x"], "d": [True]})
    ddl = create_table_sql("epra", "t", frame)
    assert "[a] FLOAT NULL" in ddl and "[b] BIGINT NULL" in ddl
    assert "[c] NVARCHAR(400) NULL" in ddl and "[d] BIT NULL" in ddl
    assert insert_sql("epra", "t", ["a", "b"]) == "INSERT INTO [epra].[t] ([a], [b]) VALUES (?, ?)"


def test_azure_clients_require_env(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("azure.storage.blob")
    for var in ("AZURE_STORAGE_CONNECTION_STRING", "AZURE_STORAGE_ACCOUNT_URL"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError, match="AZURE_STORAGE"):
        azure_clients_from_env()


def test_cli_local_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_settings: Settings
) -> None:
    settings = tmp_settings.model_copy(
        update={"paths": tmp_settings.paths.model_copy(update={"exports": tmp_path / "exp"})}
    )
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    assert settings.cloud.target == "local"
    assert cli.main([]) == 1  # nothing exported yet
    (tmp_path / "exp").mkdir()
    (tmp_path / "exp" / "ssot.csv").write_text("key,value\nk,1\n", encoding="utf-8")
    assert cli.main([]) == 0
    assert (tmp_path / "exp" / "MANIFEST.json").exists()


def test_cli_azure_uses_injected_clients(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_settings: Settings
) -> None:
    settings = tmp_settings.model_copy(
        update={"paths": tmp_settings.paths.model_copy(update={"exports": tmp_path / "exp"})}
    )
    (tmp_path / "exp").mkdir()
    (tmp_path / "exp" / "ssot.csv").write_text("key,value\nk,1\n", encoding="utf-8")
    blob, conn = FakeBlob(), FakeConnection()
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "azure_clients_from_env", lambda: (blob, lambda: conn))
    assert cli.main(["--target", "azure", "--run-id", "r1"]) == 0
    assert "epra/exports/r1/ssot.csv" in blob.uploads and conn.committed
