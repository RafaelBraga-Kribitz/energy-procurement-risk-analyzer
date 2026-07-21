"""Single raw parquet writer — the persistence boundary for all ENTSO-E
datasets (ING-003/004/005).

`_io` is intentionally the ONLY module that writes to `data/raw/`: every
ingestor calls `write_month()` so atomic, idempotent writes and the ING-004
provenance columns are enforced in exactly one place, never reimplemented
per source (`docs/EXECUTION_BLUEPRINT/03_MODULES.md` §`_io`).

Implements: ING-003 (temp-file-then-rename atomic overwrite idempotency),
ING-004 (raw + provenance columns only — no unit conversion/dedup), ING-005
(rejects non-UTC/naive `ts_utc`), ING-070 (fixed, contract-stable column
layout consumed by `tests/test_raw_contracts.py`).
"""

from __future__ import annotations

import logging
import re
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from epra.common.config import REPO_ROOT, Settings

logger = logging.getLogger(__name__)

#: ING-004 provenance columns, appended in this fixed order after the raw
#: dataset's own columns (unchanged) so re-runs with identical input + clock
#: are byte-identical (ING-003) regardless of dict/kwarg construction order.
_PROVENANCE_COLUMNS = ("ingested_at_utc", "source", "request_hash")

#: `dataset` must be a safe, allowlist-shaped filesystem identifier — this
#: mitigates T-02-03 (path traversal via a crafted dataset string) without
#: hardcoding a fixed dataset-name allowlist that would need a code change
#: per new dataset (03_MODULES.md `_io` "Extension" note).
_DATASET_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def request_hash(url: str) -> str:
    """sha256 hex digest of ``url`` with the ``securitytoken`` query param removed.

    Implements ING-004's ``request_hash`` column: two URLs identical except
    for the ENTSO-E ``securityToken`` query parameter (any letter case) hash
    identically, so the token itself never has to appear in a cache
    filename, diff, or log line downstream of this function (A-7, ING-008).

    Raises:
        ValueError: ``url`` is empty.
    """
    if not url:
        raise ValueError("request_hash() requires a non-empty url")
    parsed = urlparse(url)
    kept = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() != "securitytoken"
    ]
    stripped = urlunparse(parsed._replace(query=urlencode(kept)))
    return sha256(stripped.encode("utf-8")).hexdigest()


def _data_raw_root(settings: Settings) -> Path:
    """Absolute path of the `data/raw/` root (mirrors `db.warehouse_path`)."""
    p = settings.paths.data_raw
    return p if p.is_absolute() else REPO_ROOT / p


def raw_month_path(dataset: str, month: date, settings: Settings) -> Path:
    """Absolute path of the monthly raw parquet file for ``dataset``.

    Layout is SPEC-01 §7 / ING-003:
    ``data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet``.

    Raises:
        ValueError: ``dataset`` is not a safe filesystem identifier
            (T-02-03 — rejects path separators, ``..``, etc.).
    """
    if not _DATASET_NAME_RE.fullmatch(dataset):
        raise ValueError(
            f"dataset={dataset!r} is not a safe filesystem identifier "
            "(lowercase letters, digits, underscore only, starting with a letter)"
        )
    root = _data_raw_root(settings)
    return root / dataset / f"{month:%Y}" / f"{dataset}_{month:%Y-%m}.parquet"
