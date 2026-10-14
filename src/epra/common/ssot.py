"""SSOT input rows — the only way a computed number reaches ``NUMERIC_SSOT.md``.

Every producer (profile, analytics, strategies) writes its published numbers as
rows ``key, value, unit, tag, produced_by`` to ``data/processed/ssot/<producer>.csv``.
``scripts/generate_ssot.py`` collects all of them into the one markdown table
(GV-301). Nobody types a result number by hand (A-6).

Implements: GV-101, GV-102 (tag per row), supports GV-301, LP-020, AN-703.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from epra.common.config import Settings, resolve_repo_path

Tag = Literal["VERIFIED", "CALIBRATED", "SIMULATED"]
TAGS: tuple[Tag, ...] = ("VERIFIED", "CALIBRATED", "SIMULATED")
SSOT_COLUMNS = ["key", "value", "unit", "tag", "produced_by"]


@dataclass(frozen=True)
class SsotRow:
    """One published number with its unit and epistemic tag (Charter §5)."""

    key: str
    value: float | str
    unit: str
    tag: Tag
    produced_by: str


def ssot_input_dir(settings: Settings) -> Path:
    """Directory holding the per-producer SSOT input CSVs.

    Implements: GV-301 (single collection point for the generator).
    """
    return resolve_repo_path(settings.paths.data_processed) / "ssot"


def write_ssot_rows(rows: Iterable[SsotRow], producer: str, settings: Settings) -> Path:
    """Replace ``<producer>.csv`` with ``rows`` (idempotent, EN-050).

    Implements: GV-102, LP-020, AN-703.
    """
    frame = pd.DataFrame([asdict(r) for r in rows], columns=SSOT_COLUMNS)
    bad = set(frame["tag"]) - set(TAGS)
    if bad:
        raise ValueError(f"unknown epistemic tag(s) {sorted(bad)}; allowed {TAGS}")
    if frame["key"].duplicated().any():
        raise ValueError(f"duplicate SSOT keys from {producer}")
    path = ssot_input_dir(settings) / f"{producer}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def read_ssot_rows(settings: Settings) -> pd.DataFrame:
    """All producers' rows, sorted by key; raises on a key published twice.

    Implements: GV-301.
    """
    files = sorted(ssot_input_dir(settings).glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=SSOT_COLUMNS)
    frame = pd.concat([pd.read_csv(f, dtype={"value": str}) for f in files], ignore_index=True)
    dupes = frame.loc[frame["key"].duplicated(), "key"].tolist()
    if dupes:
        raise ValueError(f"SSOT keys published by more than one producer: {dupes}")
    return frame.sort_values("key").reset_index(drop=True)


def ssot_value(settings: Settings, key: str) -> float:
    """Read one numeric SSOT input (e.g. ``consumer_peak_share`` for ST-102).

    Implements: LP-020 (value reused, never retyped).
    """
    frame = read_ssot_rows(settings)
    match = frame.loc[frame["key"] == key, "value"]
    if match.empty:
        raise KeyError(f"SSOT input {key!r} not found — run its producer first")
    return float(match.iloc[0])
