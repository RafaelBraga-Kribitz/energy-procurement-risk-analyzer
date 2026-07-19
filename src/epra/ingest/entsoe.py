"""ENTSO-E ingestion — AT/DE-LU day-ahead prices, AT load, AT generation (M1).

Not yet implemented. The binding contract is SPEC-01 §§2-8; key points for the
implementing agent:

- Wrap ``entsoe-py`` (``EntsoePandasClient``) — never call it from analytics
  (ING-022). Raw REST fallback per Appendix A only with an ADR.
- Request in ≤ 90-day chunks (ING-030); pass tz='Europe/Vienna' timestamps to
  entsoe-py but convert returned indexes to UTC IMMEDIATELY (ING-031, T-4).
- One parquet file per dataset per calendar month, atomic overwrite
  (ING-003): ``data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet``.
- Output columns must byte-match SPEC-01 §7 contracts (tested by ING-070).
- Persist ``resolution`` per row; PT15M stays PT15M in raw — hourly
  aggregation (mean of quarters, NOT sum — T-2) happens in dbt staging.
- Retry/backoff per ING-006; ≥ 0.5 s between requests (ING-007); response
  cache per ING-009; request log line per ING-008 (token never logged, A-7).

Implements (when built): ING-002..010, ING-020..022, ING-030..032, ING-040..042,
ING-050..051, ING-060..063, ING-070.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from epra.common.config import Settings

_MSG = "M1 not implemented yet — build per SPEC-01 §§2-8 (see module docstring)"


def backfill(settings: Settings, start: date, end: date) -> None:
    """Full ingestion of all four ENTSO-E datasets for [start, end] (ING-040)."""
    raise NotImplementedError(_MSG)


def ingest_incremental(settings: Settings) -> None:
    """45-day lookback re-ingestion — ENTSO-E restates recent data (ING-041)."""
    raise NotImplementedError(_MSG)


def latest_complete_month(settings: Settings) -> date:
    """First day of the last calendar month with ALL days of price data present.

    Computed from ingested data, never assumed (ING-042). Downstream modules
    (dbt freshness, SPEC-05 forward window) call this instead of guessing.
    """
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.entsoe --start YYYY-MM-DD --end YYYY-MM-DD`` (ING-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
