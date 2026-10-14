"""``python -m epra.cloud [--target local|azure]`` — ``make publish`` (ADR-020).

Publishes the current ``exports/*.csv`` (and, for Azure, the raw parquet tree)
to the configured target. The default comes from ``config/settings.yaml``
(``cloud.target: local``); ``--target`` overrides it for one run.

Implements: ADR-020 §2.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date

from epra.cloud.targets import AzureTarget, LocalTarget, PublishTarget, azure_clients_from_env
from epra.common.config import Settings, load_settings, resolve_repo_path


def build_target(settings: Settings, name: str) -> PublishTarget:
    """Instantiate the named target (Azure clients only when actually requested)."""
    if name == "local":
        return LocalTarget(resolve_repo_path(settings.paths.exports))
    blob, connect = azure_clients_from_env()
    return AzureTarget(
        blob,
        connect,
        settings.cloud.azure.container,
        settings.cloud.azure.sql_schema,
        resolve_repo_path(settings.paths.data_raw),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Publish exports (+ raw for Azure); exit 1 if there is nothing to publish.

    Implements: ADR-020 §2.
    """
    settings = load_settings()
    parser = argparse.ArgumentParser(prog="python -m epra.cloud", description=__doc__)
    parser.add_argument("--target", choices=["local", "azure"], default=settings.cloud.target)
    parser.add_argument("--run-id", default=date.today().strftime("%Y-%m-%d"))
    args = parser.parse_args(argv)
    exports = sorted(resolve_repo_path(settings.paths.exports).glob("*.csv"))
    if not exports:
        print("ERROR: no exports/*.csv — run `make export` first", file=sys.stderr)
        return 1
    raw_root = resolve_repo_path(settings.paths.data_raw)
    raw = sorted(raw_root.rglob("*.parquet")) if args.target == "azure" else []
    report = build_target(settings, args.target).publish(exports, raw, args.run_id)
    print(
        f"OK: target={report.target} uploaded={len(report.uploaded)} "
        f"tables={sum(report.tables.values())} rows in {len(report.tables)} tables"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
