"""Cached, retried ENTSO-E HTTP transport — the single external API boundary
for M1 (SG-01 / ADR-003).

`_fetch` is the ONLY module that talks to the ENTSO-E REST API. It wraps
`entsoe.EntsoeRawClient` as a URL-builder/transport returning raw XML
strings (never `EntsoePandasClient` — ADR-003 forbids it everywhere in this
codebase), caches those raw responses under `data/cache/entsoe/` (ING-009),
retries transient failures with `tenacity` (ING-006), and paces consecutive
live requests (ING-007). The token lives only here, in request assembly,
and is stripped before any log line or cache-key hash (A-7, ING-008).

Implements: ING-006 (retry/no-retry HTTP split), ING-007 (politeness sleep),
ING-008 (request logging, no secrets), ING-009 (raw-response cache + 7-day
rule), ING-021 (fail-fast token), ING-030 (chunk bound), ING-031 (Vienna-tz
request boundary, UTC persistence). Supports REQ-ING-01. ING-020 is the
human account-registration prerequisite, not code.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from uuid import uuid4

import pandas as pd
import requests
from entsoe.entsoe import EntsoeRawClient
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from epra.common.config import REPO_ROOT, Settings, entsoe_token
from epra.common.timeutil import to_local
from epra.ingest._io import _now_utc, request_hash
from epra.ingest.exceptions import IngestAuthError, IngestTransportError

logger = logging.getLogger(__name__)

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


#: HTTP statuses ING-006 forbids retrying — always a fatal, immediate raise.
_NO_RETRY_STATUS = frozenset({400, 401, 403})
#: Subset of `_NO_RETRY_STATUS` that means "bad/expired credentials" (IngestAuthError)
#: rather than "malformed request" (IngestTransportError).
_AUTH_STATUS = frozenset({401, 403})

_DOCUMENT_TYPE_METHOD: dict[DocumentType, str] = {
    "day_ahead_prices": "query_day_ahead_prices",
    "load": "query_load",
    "generation": "query_generation",
}


#: Transport seam — takes a validated query + the caller's API key, returns
#: raw XML text or raises. Defaults to `_default_transport` (real network);
#: tests inject a stub per ADR-003's "stub `EntsoeRawClient.query_*`" note.
TransportFn = Callable[[EntsoeQuery, str], str]


def _default_transport(query: EntsoeQuery, api_key: str) -> str:
    """Live transport: `EntsoeRawClient.query_*` returning raw XML (ADR-003).

    Never imports/calls `EntsoePandasClient` — only the raw-XML-string
    methods that preserve the `resolution`/`curveType`/currency fields
    ING-050/060/063 need and that `EntsoePandasClient` discards.

    Converts UTC `EntsoeQuery` bounds to Europe/Vienna `pd.Timestamp` only
    here, at the client boundary (ING-031) — the single sanctioned TZ
    conversion point per `epra.common.timeutil` doctrine (T-1).
    """
    client = EntsoeRawClient(api_key=api_key)
    start = pd.Timestamp(to_local(query.period_start))
    end = pd.Timestamp(to_local(query.period_end))
    method: Callable[..., str] = getattr(client, _DOCUMENT_TYPE_METHOD[query.document_type])
    if query.document_type == "generation":
        return method(query.domain, start, end, psr_type=query.psr_type)
    return method(query.domain, start, end)


def _http_status(exc: BaseException) -> int | None:
    """Extract an HTTP status code from a transport exception, if any."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _error_detail(exc: BaseException) -> str:
    """Response body snippet for an error message — never the token (A-7).

    The token only ever appears in the outgoing request's query string, not
    in ENTSO-E's response body, so truncating the response text here cannot
    leak it. When there is no response body (e.g. a gateway/WAF 401/403 with
    an empty body), we must NOT fall back to `str(exc)`: for a
    `requests.HTTPError` raised via `response.raise_for_status()`, that
    string embeds the full request URL -- including the real
    `securityToken` -- which would leak the token into an
    `IngestAuthError`/`IngestTransportError` message (A-7/ING-008).
    """
    response = getattr(exc, "response", None)
    text = getattr(response, "text", None)
    if text:
        return str(text)[:500]
    return f"{type(exc).__name__}: no response body available"


def _invoke_transport_once(transport: TransportFn, query: EntsoeQuery, api_key: str) -> str:
    """One attempt at `transport`; converts non-retryable statuses immediately.

    ING-006: 401/403 -> `IngestAuthError`; 400 -> `IngestTransportError`; none
    of these are retried. Any other failure (429, 5xx, connection error) is
    re-raised unchanged so the `tenacity`-wrapped caller can classify it.
    """
    try:
        return transport(query, api_key)
    except Exception as exc:
        status = _http_status(exc)
        if status in _AUTH_STATUS:
            # `from None` deliberately severs the exception chain (A-7): the
            # original `requests.HTTPError`'s own `str()` can embed the real
            # token-bearing request URL, and preserving it as `__cause__`
            # would let a future traceback dump (logger.exception, a bare
            # script, pytest failure output) reprint it.
            raise IngestAuthError("entsoe", f"HTTP {status}: {_error_detail(exc)}") from None
        if status == 400:
            raise IngestTransportError("entsoe", _error_detail(exc), status_code=400) from None
        raise


def _is_retryable(exc: BaseException) -> bool:
    """ING-006 retry predicate: 429/5xx/connection errors only.

    `IngestAuthError`/`IngestTransportError` raised by
    `_invoke_transport_once` for 400/401/403 are already terminal and must
    never be retried, even though they are ordinary exceptions to `tenacity`.
    """
    if isinstance(exc, (IngestAuthError, IngestTransportError)):
        return False
    status = _http_status(exc)
    if status is not None:
        return status == 429 or status >= 500
    return isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))


@retry(
    wait=wait_exponential(multiplier=2, min=2, max=120),
    stop=stop_after_attempt(6),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _fetch_live_with_retry(transport: TransportFn, query: EntsoeQuery, api_key: str) -> str:
    return _invoke_transport_once(transport, query, api_key)


def _cache_root(settings: Settings) -> Path:
    """Absolute path of `data/cache/entsoe/` (mirrors `_io._data_raw_root`)."""
    p = settings.paths.data_cache
    root = p if p.is_absolute() else REPO_ROOT / p
    return root / "entsoe"


def _cache_path(settings: Settings, req_hash: str) -> Path:
    """Absolute path of the cache file for a token-stripped request hash."""
    return _cache_root(settings) / f"{req_hash}.bin"


def _cache_request_url(query: EntsoeQuery, api_key: str) -> str:
    """Deterministic, cache-key-only URL — never sent over the network.

    `EntsoeRawClient` builds and sends its own request; this mirrors
    ENTSO-E's query-parameter shape closely enough that `request_hash()`
    (which strips `securityToken`) produces a stable key that changes if and
    only if the query itself changes (ING-009).
    """
    params: dict[str, str] = {
        "documentType": query.document_type,
        "domain": query.domain,
        "periodStart": query.period_start.isoformat(),
        "periodEnd": query.period_end.isoformat(),
        "securityToken": api_key,
    }
    if query.psr_type:
        params["psrType"] = query.psr_type
    return f"https://web-api.tp.entsoe.eu/api?{urlencode(sorted(params.items()))}"


def _is_cache_eligible(query: EntsoeQuery, settings: Settings) -> bool:
    """ING-009: cache is used only once the window is safely in the past."""
    cutoff = _now_utc() - timedelta(days=settings.ingest.cache_min_age_days)
    return query.period_end <= cutoff


def fetch_entsoe(
    query: EntsoeQuery,
    settings: Settings,
    *,
    use_cache: bool = True,
    transport: TransportFn | None = None,
) -> str:
    """Fetch raw ENTSO-E XML for `query`, using the on-disk cache (ING-009).

    Reads `ENTSOE_API_TOKEN` via `entsoe_token()` first, so a missing token
    fails fast (ING-021) before any cache lookup or network call. On a live
    fetch, writes the response bytes to `data/cache/entsoe/<hash>.bin`
    (atomic temp-file-then-rename, mirroring `_io.write_month`) and sleeps
    `settings.ingest.entsoe_sleep_s` before returning (ING-007) so any
    immediately-following live call is paced.

    Args:
        query: validated request window (see `EntsoeQuery`).
        settings: injected config; never re-read YAML here (EN-040).
        use_cache: when `False`, always hits the network regardless of any
            existing cache file (`--no-cache` semantics, ING-009).
        transport: override for the live network call. Defaults to
            `_default_transport` (real `EntsoeRawClient`); tests inject a
            stub returning canned XML or raising a `requests`-shaped error
            with `.response.status_code` set (ADR-003).

    Returns:
        Raw XML text (`Publication_MarketDocument` / `GL_MarketDocument` /
        `Acknowledgement_MarketDocument` — the caller/parser classifies).

    Raises:
        RuntimeError: `ENTSOE_API_TOKEN` unset (ING-021, via `entsoe_token()`).
        IngestAuthError: HTTP 401/403 — bad/expired token; never retried.
        IngestTransportError: HTTP 400, or 429/5xx/connection retries
            exhausted after `tenacity`'s 6 attempts.
    """
    api_key = entsoe_token()
    transport_fn = transport if transport is not None else _default_transport

    req_hash = request_hash(_cache_request_url(query, api_key))
    cache_path = _cache_path(settings, req_hash)

    if use_cache and cache_path.exists() and _is_cache_eligible(query, settings):
        xml = cache_path.read_text(encoding="utf-8")
        logger.info(
            "source=entsoe window=%s..%s status=cache_hit rows=n/a elapsed_ms=0",
            query.period_start.isoformat(),
            query.period_end.isoformat(),
        )
        return xml

    start_ns = time.monotonic()
    try:
        xml = _fetch_live_with_retry(transport_fn, query, api_key)
    except (IngestAuthError, IngestTransportError):
        raise
    except Exception as exc:  # tenacity exhausted retries on 429/5xx/connection error
        # `from None` severs the exception chain (A-7) -- see the comment in
        # `_invoke_transport_once` for why preserving `__cause__` here could
        # leak the real token via a future traceback dump.
        raise IngestTransportError(
            "entsoe", _error_detail(exc), status_code=_http_status(exc)
        ) from None
    elapsed_ms = int((time.monotonic() - start_ns) * 1000)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Per-call-unique temp name (PID + short uuid4) so two processes racing
    # to fetch the same cache key never share a `.tmp` path (WR-02) -- see
    # the identical rationale in `_io.write_month`.
    tmp_path = cache_path.parent / f"{cache_path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    tmp_path.write_text(xml, encoding="utf-8")
    os.replace(tmp_path, cache_path)

    logger.info(
        "source=entsoe window=%s..%s status=200 rows=n/a elapsed_ms=%d",
        query.period_start.isoformat(),
        query.period_end.isoformat(),
        elapsed_ms,
    )

    time.sleep(settings.ingest.entsoe_sleep_s)  # ING-007 — paces the *next* live call

    return xml
