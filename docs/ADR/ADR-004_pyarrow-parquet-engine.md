# ADR-004: pyarrow as the pandas parquet engine for ingestion I/O
Date: 2026-07-21  |  Status: accepted

## Context
`src/epra/ingest/_io.py` (planned, T1.01) and `tests/test_raw_contracts.py`
(ING-070) both read and write `data/raw/**/*.parquet` via
`pandas.DataFrame.to_parquet` / `pandas.read_parquet`. Neither `pyarrow` nor
`fastparquet` is currently listed in SPEC-07 §3's pinned dependency list or
in `pyproject.toml`'s `[project.dependencies]` — an omission confirmed by
`02-RESEARCH.md` Environment Availability (`pyarrow: ✗`) and the Package
Legitimacy Audit (`pyarrow ... [ASSUMED] OK — Add in Wave 0`). Without a
parquet engine, `pandas.read_parquet`/`to_parquet` raise
`ImportError: Unable to find a usable engine` on first use — Pitfall 4 in
research. DuckDB (already a dependency) can read/write parquet without
pyarrow, but the blueprint's `_io` contract and `test_raw_contracts.py` are
written against the pandas API, and standardizing on DuckDB-only I/O would
require rewriting both to avoid ever touching `pandas.read_parquet`.

## Decision
Add `pyarrow>=18,<26` to `[project.dependencies]` in `pyproject.toml`.
`pandas.to_parquet`/`read_parquet` (via the `pyarrow` engine) is the
canonical parquet I/O path for `_io.write_month`, `_io` readers, and
ING-070 contract tests. DuckDB parquet functions remain available as the
warehouse-load path (M3, SPEC-02) but are not used for raw-layer I/O.

The version range mirrors the project's existing pin style (lower bound at
current major-ish floor, open upper bound short of a speculative future
major) and was verified installable and importable in the dev venv at
research time (`pyarrow` latest verified `25.0.0` on PyPI, `apache/arrow`
source repo, Package Legitimacy Audit verdict "OK [ASSUMED]").

## Consequences
- `pandas.DataFrame.to_parquet(path, index=False)` and
  `pandas.read_parquet(path)` work without an explicit `engine=` kwarg
  (pyarrow is pandas' default preferred engine when installed).
- `uv pip install -e ".[dev]"` must be re-run after this change so the venv
  picks up pyarrow before any `_io` or contract-test code runs.
- Any future pyarrow major-version bump past `<26` requires a superseding
  ADR (GV-203) per SPEC-07 §3 pin discipline.
- No DuckDB-vs-pandas fork in ingestion code — one parquet engine, one
  code path, matching `08_PATTERNS.md` functional-core guidance.

## Spec deviations
SPEC-07 §3 (pinned dependency list omitted a parquet engine — reality
correction, not a design choice). Output contract preserved: `_io` and
`test_raw_contracts.py` still operate on `pandas.DataFrame` with the exact
§7 column/dtype contracts; only the underlying parquet codec dependency is
added. Cross-reference: `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` — pyarrow
gap resolution recorded as adopted here (no separate SG-N row existed for
this omission; tracked directly in `02-RESEARCH.md` Open Question 2).
