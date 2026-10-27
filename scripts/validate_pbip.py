"""Validate every PBIP/PBIR JSON file against the JSON schema it declares (ADR-022).

Each JSON file under ``dashboards/`` that carries a ``$schema`` URL of the
``https://developer.microsoft.com/json-schemas/`` tree is checked against a LOCAL
copy of that schema tree, so the check needs no network. Cross-file ``$ref``s
(visualContainer → visualConfiguration → semanticQuery …) resolve through a
``referencing`` registry that maps each https URL onto the matching local file.

Usage::

    uv run python scripts/validate_pbip.py --schema-dir <dir that holds fabric/…>

Without ``--schema-dir`` (and without ``PBIP_SCHEMA_DIR``) the script prints a
message and exits 0: CI has no copy of the schema tree, and the PBIP's own
consistency is covered offline by ``tests/unit/test_pbip_integrity.py``.
Exit code 1 means at least one file failed validation or declared no schema.

Implements: ADR-022 (PBIP schema gate), supports RP-401..RP-406.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / "dashboards"
SCHEMA_URL_PREFIX = "https://developer.microsoft.com/json-schemas/"
#: JSON files in the PBIP that are data, not schema-bound definitions.
UNBOUND = {"theme.json"}


def pbip_json_files(root: Path) -> list[Path]:
    """Every schema-bound JSON file of the PBIP projects under ``root`` (sorted).

    Implements: ADR-022.
    """
    files = [*root.glob("*.pbip"), *root.rglob("*.pbir"), *root.rglob("*.pbism")]
    files += [
        p
        for p in root.rglob("*.json")
        if p.name not in UNBOUND and "RegisteredResources" not in p.parts and ".pbi" not in p.parts
    ]
    return sorted(set(files))


def _url_to_path(url: str, schema_dir: Path) -> Path:
    """https://…/json-schemas/<rel> (or the ``schema.embedded.json`` $id spelling) → file."""
    rel = url.split("#", 1)[0].removeprefix(SCHEMA_URL_PREFIX)
    path = schema_dir / rel
    if not path.exists() and path.name == "schema.embedded.json":
        path = path.with_name("schema-embedded.json")
    return path


def build_registry(schema_dir: Path) -> Any:
    """A ``referencing`` registry that loads any schema URL from ``schema_dir`` lazily.

    Implements: ADR-022 (offline cross-file $ref resolution).
    """
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    def retrieve(uri: str) -> Resource[Any]:
        path = _url_to_path(uri, schema_dir)
        contents = json.loads(path.read_text(encoding="utf-8-sig"))
        return Resource.from_contents(contents, default_specification=DRAFT7)

    return Registry(retrieve=retrieve)  # type: ignore[call-arg]


def validate_file(path: Path, schema_dir: Path, registry: Any) -> list[str]:
    """Schema errors of one file as ``path: message`` strings (empty = valid).

    Implements: ADR-022.
    """
    # jsonschema ships without type stubs; resolved at runtime (installed via dbt-core).
    draft7_validator: Any = importlib.import_module("jsonschema").Draft7Validator
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return [f"{path}: UTF-8 BOM (Power BI Desktop rejects it)"]
    document = json.loads(raw.decode("utf-8"))
    url = document.get("$schema") if isinstance(document, dict) else None
    if not isinstance(url, str) or not url.startswith(SCHEMA_URL_PREFIX):
        return [f"{path}: no $schema URL under {SCHEMA_URL_PREFIX}"]
    schema_path = _url_to_path(url, schema_dir)
    if not schema_path.exists():
        return [f"{path}: schema not in the local tree: {schema_path}"]
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    schema.setdefault("$id", url)
    validator = draft7_validator(schema, registry=registry)
    return [
        f"{path}: {'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; see module docstring.

    Implements: ADR-022.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--schema-dir", type=Path, default=os.environ.get("PBIP_SCHEMA_DIR"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    if args.schema_dir is None:
        print("validate_pbip: no --schema-dir / PBIP_SCHEMA_DIR given; skipping (exit 0).")
        return 0
    schema_dir = Path(args.schema_dir)
    if not (schema_dir / "fabric").is_dir():
        print(f"validate_pbip: {schema_dir} has no fabric/ schema tree", file=sys.stderr)
        return 1
    registry = build_registry(schema_dir)
    files = pbip_json_files(args.root)
    errors = [e for f in files for e in validate_file(f, schema_dir, registry)]
    for error in errors:
        print(error, file=sys.stderr)
    print(f"validate_pbip: {len(files)} files, {len(errors)} errors")
    return 1 if errors or not files else 0


if __name__ == "__main__":
    sys.exit(main())
