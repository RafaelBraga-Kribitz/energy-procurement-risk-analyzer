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
import os
import re
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import uuid4

import pandas as pd

from epra.common.config import REPO_ROOT, Settings
from epra.ingest.exceptions import ContractError

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


def _dataset_root(dataset: str, settings: Settings) -> Path:
    """Absolute `data/raw/<dataset>/` root.

    Single canonical implementation (WR-03) -- `entsoe.py` and `validate.py`
    both import this instead of reimplementing the same
    `data_raw / dataset` path resolution independently, so a future change
    to path resolution only has to happen here.
    """
    return _data_raw_root(settings) / dataset


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


def _now_utc() -> datetime:
    """Wall-clock accessor — a seam so tests can freeze `ingested_at_utc` (ING-003).

    Single canonical implementation (WR-03): `_fetch.py` imports this same
    function for its ING-009 cache-age cutoff instead of reimplementing an
    identical one-line seam.
    """
    return datetime.now(UTC)


def _month_bounds(month: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """UTC-naive-safe ``[month_start, month_end)`` bounds shared by both
    validation paths (ts_utc and date-keyed) so the calendar-month contract
    is computed in exactly one place (WR-03)."""
    month_start = pd.Timestamp(year=month.year, month=month.month, day=1, tz="UTC")
    month_end = month_start + pd.offsets.MonthBegin(1)  # exclusive upper bound
    return month_start, month_end


def _validate_ts_utc_key(frame: pd.DataFrame, dataset: str, month: date) -> None:
    """Enforce ING-005 (UTC, tz-aware) and the write-boundary month contract.

    Raises:
        ContractError: ``ts_utc`` column missing entirely — a schema
            violation, not a value problem.
        ValueError: ``ts_utc`` is naive/non-UTC, or any row falls outside
            ``month`` (calendar-month bounds, per the monthly file layout).
    """
    if "ts_utc" not in frame.columns:
        raise ContractError(
            dataset,
            expected="column 'ts_utc' (tz-aware UTC timestamp)",
            actual=f"columns={list(frame.columns)}",
        )
    ts = frame["ts_utc"]
    if not pd.api.types.is_datetime64_any_dtype(ts):
        raise ValueError(
            f"write_month({dataset}): ts_utc must be tz-aware UTC; "
            f"got non-datetime dtype {ts.dtype}"
        )
    tz = ts.dt.tz
    if tz is None:
        raise ValueError(
            f"write_month({dataset}): ts_utc must be tz-aware UTC; got naive datetime64 (no tzinfo)"
        )
    if str(tz) != "UTC":
        raise ValueError(f"write_month({dataset}): ts_utc must be UTC, got tz={tz}")

    month_start, month_end = _month_bounds(month)
    out_of_month = ts[(ts < month_start) | (ts >= month_end)]
    if not out_of_month.empty:
        offenders = [str(t) for t in out_of_month.tolist()]
        raise ValueError(
            f"write_month({dataset}): {len(offenders)} row(s) fall outside target month "
            f"{month:%Y-%m}: {offenders[:10]}"
        )


def _validate_date_key(frame: pd.DataFrame, dataset: str, month: date, key_column: str) -> None:
    """Enforce the write-boundary month contract for a plain (tz-naive)
    date-grain key column — e.g. GeoSphere's ``date`` (SPEC-01 §7).

    Unlike ``_validate_ts_utc_key`` this applies NO timezone assertion: a
    calendar ``date`` is tz-naive by design, not a defect.

    Raises:
        ContractError: ``key_column`` missing entirely — a schema violation,
            not a value problem.
        ValueError: any row's key value falls outside ``month`` (calendar-
            month bounds, per the monthly file layout).
    """
    if key_column not in frame.columns:
        raise ContractError(
            dataset,
            expected=f"column {key_column!r}",
            actual=f"columns={list(frame.columns)}",
        )
    key = pd.to_datetime(frame[key_column])
    # Compare tz-naive: strip the UTC tz from the shared bounds since a
    # `date`-grain key carries no tzinfo of its own (no UTC assertion here).
    month_start, month_end = _month_bounds(month)
    month_start = month_start.tz_localize(None)
    month_end = month_end.tz_localize(None)
    out_of_month = key[(key < month_start) | (key >= month_end)]
    if not out_of_month.empty:
        offenders = [str(v) for v in out_of_month.tolist()]
        raise ValueError(
            f"write_month({dataset}): {len(offenders)} row(s) fall outside target month "
            f"{month:%Y-%m}: {offenders[:10]}"
        )


def write_month(
    frame: pd.DataFrame,
    dataset: str,
    month: date,
    request_hash: str,
    settings: Settings,
    *,
    key_column: str = "ts_utc",
) -> Path:
    """Persist one calendar-month slice of raw ``dataset`` rows, atomically.

    Implements ING-003 (temp-file-then-``os.replace`` atomic overwrite — a
    re-run with identical input and clock is byte-identical), ING-004
    (appends ``ingested_at_utc``/``source``/``request_hash``; never unit-
    converts or deduplicates the raw values), ING-005 (rejects any frame
    whose ``ts_utc`` is not tz-aware UTC), and ING-070 (fixed column order —
    the frame's own columns unchanged, then the three ING-004 columns — the
    layout `tests/test_raw_contracts.py` asserts against).

    ``key_column`` selects which write-key grain to validate against
    ``month``'s calendar bounds. It defaults to ``"ts_utc"``, which preserves
    ING-005's tz-aware-UTC contract byte-for-byte for every existing
    ENTSO-E caller. Passing ``key_column="date"`` (or any other non-
    ``"ts_utc"`` column name) switches to a plain, tz-naive date-grain
    validation path with no UTC assertion — for date-keyed datasets such as
    GeoSphere daily temperature (SPEC-01 §7) that have no ``ts_utc`` column
    at all. Both paths share the same atomic write, ING-004 provenance
    columns, and ING-070 column-order guarantee below.

    ``source`` is derived from ``dataset``'s prefix before the first
    underscore (``entsoe_prices_at`` -> ``entsoe``, ``geosphere_graz_daily``
    -> ``geosphere``) so callers never pass a fourth provenance argument
    that could drift out of sync with the dataset name.

    Does NOT deduplicate rows or convert units — raw means raw (ING-004).

    Raises:
        ContractError: ``key_column`` missing.
        ValueError: (``ts_utc`` path only) naive/non-UTC key, a row falls
            outside ``month``, or ``dataset`` is not a safe filesystem
            identifier (T-02-03).
    """
    if key_column == "ts_utc":
        _validate_ts_utc_key(frame, dataset, month)
    else:
        _validate_date_key(frame, dataset, month, key_column)

    out = frame.copy()
    out["ingested_at_utc"] = _now_utc().isoformat()
    out["source"] = dataset.split("_", 1)[0]
    out["request_hash"] = request_hash
    out = out[[*frame.columns, *_PROVENANCE_COLUMNS]]

    path = raw_month_path(dataset, month, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Per-call-unique temp name (PID + short uuid4) so two processes writing
    # the same month file concurrently never share a `.tmp` path and clobber
    # each other's partially-written temp file before either `os.replace`
    # (WR-02) -- the fixed `<name>.tmp` scheme this replaces defeated the
    # atomicity guarantee in exactly the concurrent-writer scenario it was
    # meant to protect against.
    tmp_path = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    out.to_parquet(tmp_path, index=False, engine="pyarrow")
    os.replace(tmp_path, path)

    logger.info(
        "wrote dataset=%s month=%s rows=%d path=%s", dataset, f"{month:%Y-%m}", len(out), path
    )
    return path
