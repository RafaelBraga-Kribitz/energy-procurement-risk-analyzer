"""Publish targets: local (default) and Azure Blob Storage + Azure SQL (ADR-020).

The analytical engine stays DuckDB + dbt on the local machine / CI runner. A
publish target only decides where the RESULTS go after ``make all``:

- :class:`LocalTarget` — writes ``exports/MANIFEST.json`` (file, rows, sha256).
  No account, no network: the default, and what CI exercises.
- :class:`AzureTarget` — uploads the raw parquet tree and the export CSVs to a
  Blob container (``raw/…``, ``exports/<run_id>/…``, ``exports/latest/…``) and
  loads every export CSV into an Azure SQL table ``<schema>.<name>``
  (create-if-missing, then full reload in one transaction).

Clients are injected (``blob_service``, ``sql_connect``) so tests use fakes and
the Azure SDK / ODBC driver are imported only when the Azure path really runs.
Secrets come from environment variables only (EN-041, A-7).

Implements: ADR-020 §2.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

#: pandas dtype kind → T-SQL column type for the Azure SQL tables.
SQL_TYPES = {"f": "FLOAT", "i": "BIGINT", "u": "BIGINT", "b": "BIT", "O": "NVARCHAR(400)"}
ENV_BLOB_CONN = "AZURE_STORAGE_CONNECTION_STRING"
ENV_BLOB_URL = "AZURE_STORAGE_ACCOUNT_URL"
ENV_SQL_CONN = "AZURE_SQL_CONNECTION_STRING"


@dataclass
class PublishReport:
    """What a target did — printed by the CLI, asserted by tests."""

    target: str
    uploaded: list[str] = field(default_factory=list)
    tables: dict[str, int] = field(default_factory=dict)


class PublishTarget(Protocol):
    """Interface every target implements."""

    name: str

    def publish(self, exports: list[Path], raw_files: list[Path], run_id: str) -> PublishReport:
        """Ship ``exports`` (+ ``raw_files``) for ``run_id``."""
        ...


def sha256(path: Path) -> str:
    """Hex digest of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(exports: Iterable[Path], run_id: str) -> dict[str, Any]:
    """Row counts + checksums of the export CSVs (lineage for any target)."""
    files = [
        {
            "file": p.name,
            "rows": int(sum(1 for _ in p.open(encoding="utf-8")) - 1),
            "sha256": sha256(p),
        }
        for p in sorted(exports)
    ]
    return {"run_id": run_id, "files": files}


class LocalTarget:
    """Default target: a manifest next to the exports, nothing leaves the machine."""

    name = "local"

    def __init__(self, exports_dir: Path) -> None:
        self.exports_dir = exports_dir

    def publish(self, exports: list[Path], raw_files: list[Path], run_id: str) -> PublishReport:
        path = self.exports_dir / "MANIFEST.json"
        path.write_text(json.dumps(manifest(exports, run_id), indent=1) + "\n", encoding="utf-8")
        return PublishReport(self.name, uploaded=[str(path)])


def create_table_sql(schema: str, table: str, frame: pd.DataFrame) -> str:
    """Idempotent T-SQL DDL for one export, column types from the CSV dtypes."""
    cols = ",\n    ".join(
        f"[{c}] {SQL_TYPES.get(frame[c].dtype.kind, 'NVARCHAR(400)')} NULL" for c in frame.columns
    )
    return (
        f"IF OBJECT_ID(N'[{schema}].[{table}]', N'U') IS NULL\n"
        f"CREATE TABLE [{schema}].[{table}] (\n    {cols}\n);"
    )


def insert_sql(schema: str, table: str, columns: list[str]) -> str:
    """Parameterized INSERT for ``executemany``."""
    names = ", ".join(f"[{c}]" for c in columns)
    marks = ", ".join("?" for _ in columns)
    return f"INSERT INTO [{schema}].[{table}] ({names}) VALUES ({marks})"


class AzureTarget:
    """Blob Storage upload + Azure SQL load. Clients injected; secrets from env."""

    name = "azure"

    def __init__(
        self,
        blob_service: Any,
        sql_connect: Callable[[], Any],
        container: str,
        schema: str,
        raw_root: Path,
    ) -> None:
        self.blob_service = blob_service
        self.sql_connect = sql_connect
        self.container = container
        self.schema = schema
        self.raw_root = raw_root

    def _upload(self, path: Path, blob_name: str) -> str:
        client = self.blob_service.get_blob_client(container=self.container, blob=blob_name)
        with path.open("rb") as handle:
            client.upload_blob(handle, overwrite=True)
        return blob_name

    def _load_table(self, cursor: Any, path: Path) -> int:
        frame = pd.read_csv(path)
        table = path.stem
        cursor.execute(
            f"IF SCHEMA_ID(N'{self.schema}') IS NULL EXEC('CREATE SCHEMA [{self.schema}]')"
        )
        cursor.execute(create_table_sql(self.schema, table, frame))
        cursor.execute(f"TRUNCATE TABLE [{self.schema}].[{table}]")
        rows = frame.astype(object).where(frame.notna(), None).itertuples(index=False, name=None)
        cursor.fast_executemany = True
        cursor.executemany(insert_sql(self.schema, table, list(frame.columns)), list(rows))
        return len(frame)

    def publish(self, exports: list[Path], raw_files: list[Path], run_id: str) -> PublishReport:
        report = PublishReport(self.name)
        for path in raw_files:
            report.uploaded.append(
                self._upload(path, f"raw/{path.relative_to(self.raw_root).as_posix()}")
            )
        for path in exports:
            for prefix in (f"exports/{run_id}", "exports/latest"):
                report.uploaded.append(self._upload(path, f"{prefix}/{path.name}"))
        connection = self.sql_connect()
        try:
            cursor = connection.cursor()
            for path in exports:
                report.tables[path.stem] = self._load_table(cursor, path)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return report


def azure_clients_from_env() -> tuple[Any, Callable[[], Any]]:
    """Real Azure clients, built ONLY from environment variables (A-7).

    Requires ``pip install 'epra[azure]'`` (or ``uv sync --extra azure``) and the
    Microsoft ODBC Driver 18 for SQL Server.
    """
    from azure.storage.blob import BlobServiceClient

    if os.environ.get(ENV_BLOB_CONN):
        blob = BlobServiceClient.from_connection_string(os.environ[ENV_BLOB_CONN])
    elif os.environ.get(ENV_BLOB_URL):
        from azure.identity import DefaultAzureCredential

        blob = BlobServiceClient(os.environ[ENV_BLOB_URL], credential=DefaultAzureCredential())
    else:
        raise RuntimeError(f"set {ENV_BLOB_CONN} or {ENV_BLOB_URL} for the Azure target")
    sql_conn = os.environ.get(ENV_SQL_CONN)
    if not sql_conn:
        raise RuntimeError(f"set {ENV_SQL_CONN} for the Azure target")

    def connect() -> Any:
        import pyodbc

        return pyodbc.connect(sql_conn, autocommit=False)

    return blob, connect
