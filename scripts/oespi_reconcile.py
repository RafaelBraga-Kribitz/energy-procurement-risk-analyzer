"""ÖSPI double-entry reconciliation (ING-101).

Workflow: a human (or two independent agent sessions) transcribes the ÖSPI
monthly series TWICE from the Austrian Energy Agency publication into
``data/manual/oespi_monthly_entry1.csv`` and ``..._entry2.csv`` (schema per
ING-100). This script diffs them; if identical on all value columns, it writes
the reconciled ``data/manual/oespi_monthly.csv`` and tells you to delete the
entry files. Any mismatch is listed month-by-month and must be resolved by
RE-READING THE SOURCE — never by guessing (A-2).

Usage: ``uv run python scripts/oespi_reconcile.py [--dir DIR]`` (``DIR`` defaults to
the repo's ``data/manual/``, independent of the current working directory)
Exit 0 on successful reconciliation, 1 on mismatch or missing input.

Implements: ING-101.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

#: Default ``--dir``: the repo's ``data/manual/``, anchored at the repo root (not the cwd).
DEFAULT_DIR = Path(__file__).resolve().parents[1] / "data" / "manual"

EXPECTED_COLUMNS = ["month", "oespi_base", "oespi_peak", "source_url", "retrieved_at"]
VALUE_COLUMNS = ["oespi_base", "oespi_peak"]


def _read(path: Path) -> dict[str, dict[str, str]]:
    """Read one transcription as ``{month: row}``; exit on ING-100 schema drift or no rows.

    Implements: ING-100.
    """
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise SystemExit(
                f"ERROR: {path} columns {reader.fieldnames} != expected {EXPECTED_COLUMNS} "
                "(ING-100 schema)"
            )
        rows = {row["month"]: row for row in reader}
    if not rows:
        raise SystemExit(f"ERROR: {path} contains no data rows")
    return rows


def reconcile(entry1: Path, entry2: Path, out: Path) -> int:
    """Diff the two transcriptions; write ``out`` only if they fully agree.

    Implements: ING-101 steps 3-4 (diff entry1 vs entry2; the agreed file becomes
    ``oespi_monthly.csv``), ING-100 (both inputs must match the exact schema).

    Every month present in only one file, and every month whose
    ``oespi_base``/``oespi_peak`` differ (after whitespace strip), is printed
    as a mismatch; nothing is written unless there are zero mismatches.
    ``source_url``/``retrieved_at`` are provenance, not transcribed values, and
    are taken from ``entry1`` verbatim (the output is a byte copy of it).

    Returns:
        0 when ``out`` was written, 1 on any mismatch (resolve by re-reading the
        AEA source, A-2 -- never by guessing).

    Raises:
        SystemExit: an input's columns differ from ING-100 or it has no rows.
    """
    rows1, rows2 = _read(entry1), _read(entry2)
    mismatches: list[str] = []

    for month in sorted(set(rows1) | set(rows2)):
        r1, r2 = rows1.get(month), rows2.get(month)
        if r1 is None or r2 is None:
            mismatches.append(f"{month}: present in only one entry file")
            continue
        for col in VALUE_COLUMNS:
            if r1[col].strip() != r2[col].strip():
                mismatches.append(f"{month}: {col} entry1={r1[col]!r} entry2={r2[col]!r}")

    if mismatches:
        print(f"RECONCILIATION FAILED — {len(mismatches)} mismatch(es):")
        for m in mismatches:
            print(f"  {m}")
        print("Resolve by re-reading the AEA source (A-2), then re-run.")
        return 1

    out.write_text(entry1.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"OK: {len(rows1)} months reconciled -> {out}")
    print(f"Now delete {entry1.name} and {entry2.name} (ING-101 step 4).")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python scripts/oespi_reconcile.py [--dir data/manual]``.

    Implements: ING-101 (reconcile ``<dir>/oespi_monthly_entry1.csv`` against
    ``..._entry2.csv`` into ``<dir>/oespi_monthly.csv``).

    Returns 0 on a successful reconciliation, 1 if an entry file is missing or
    the entries disagree.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=DEFAULT_DIR, type=Path)
    args = parser.parse_args(argv)
    entry1 = args.dir / "oespi_monthly_entry1.csv"
    entry2 = args.dir / "oespi_monthly_entry2.csv"
    for p in (entry1, entry2):
        if not p.exists():
            print(f"ERROR: {p} not found — transcribe both entries first (ING-101).")
            return 1
    return reconcile(entry1, entry2, args.dir / "oespi_monthly.csv")


if __name__ == "__main__":
    sys.exit(main())
