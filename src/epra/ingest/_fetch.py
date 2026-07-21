"""Cached, retried ENTSO-E HTTP transport — the single external API boundary
for M1 (SG-01 / ADR-003).

This module owns `EntsoeQuery`, the immutable, validated request-window
object every ENTSO-E fetch is built from (ING-030 — an invalid window raises
before any HTTP call is attempted). `fetch_entsoe` itself (cache/retry/
politeness/logging — ING-006, ING-007, ING-008, ING-009, ING-021, ING-031)
lands in a following commit on this same file.

Implements: ING-030.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

#: ENTSO-E document families this module fetches (SPEC-01 §3).
DocumentType = Literal["day_ahead_prices", "load", "generation"]


@dataclass(frozen=True)
class EntsoeQuery:
    """One bounded ENTSO-E request — immutable so it hashes/caches stably.

    Implements ING-030: constructing an invalid window raises before any
    HTTP call is attempted (validation happens in `__post_init__`, which
    runs before `fetch_entsoe` ever sees the object).

    Attributes:
        document_type: which SPEC-01 §3 dataset family to fetch.
        domain: EIC area code (e.g. ``settings.zones["at"].eic``).
        period_start: UTC-aware start of the request window (exclusive per
            ENTSO-E convention).
        period_end: UTC-aware end of the request window. Must be strictly
            after `period_start` and no more than 90 days later.
        psr_type: generation PSR type filter; only meaningful when
            `document_type == "generation"`.
    """

    document_type: DocumentType
    domain: str
    period_start: datetime
    period_end: datetime
    psr_type: str | None = None

    def __post_init__(self) -> None:
        for name, ts in (("period_start", self.period_start), ("period_end", self.period_end)):
            if ts.tzinfo is None:
                raise ValueError(f"EntsoeQuery.{name} must be tz-aware UTC; got naive datetime")
        if self.period_end <= self.period_start:
            raise ValueError(
                f"EntsoeQuery: period_end ({self.period_end.isoformat()}) must be after "
                f"period_start ({self.period_start.isoformat()})"
            )
        window = self.period_end - self.period_start
        if window > timedelta(days=90):
            raise ValueError(
                f"EntsoeQuery: window of {window} exceeds ING-030's 90-day maximum "
                f"(period_start={self.period_start.isoformat()}, "
                f"period_end={self.period_end.isoformat()})"
            )
