"""GeoSphere Austria ingestion — daily mean temperature, Graz (M2).

Binding contract: SPEC-01 §9. Key points:

- MANDATORY first step is station discovery (ING-091): fetch
  ``/station/historical/klima-v2-1d/metadata``, pick the Graz station with the
  longest record (prefer "Graz Universität"), record station_id/name/lat/lon in
  ``config/settings.yaml`` under ``geosphere:`` AND in an ADR (ADR-007). The
  station id is never hardcoded in code — it lives only in config + the ADR.
- The live metadata endpoint returns a flat JSON object with a top-level
  ``stations`` list (``id``/``name``/``state``/``lat``/``lon``/``valid_from``/
  ``valid_to``/``is_active`` per station) — confirmed against the real
  endpoint at discovery time (ADR-007). SPEC-01 §9's ``output_format=geojson``
  parameter applies to the *data* endpoint (``ingest()``, 03-04), not
  ``/metadata``; `_load_metadata` still defensively accepts a GeoJSON-style
  ``features`` list too, since the metadata endpoint's exact shape is not
  independently pinned by an OpenAPI schema.
- The data endpoint (``/station/historical/klima-v2-1d?...&output_format=
  geojson``) returns a ``FeatureCollection``-shaped payload: a top-level
  ``timestamps`` array running parallel to
  ``features[0].properties.parameters.tl_mittel.data[]`` (one feature per
  requested station) — confirmed against the committed fixture
  ``tests/fixtures/geosphere/klima_2019-01.geojson`` (D-07). `parse_geojson`
  validates this shape before any deep indexing and raises `ContractError` on
  a mismatch — it never returns a silently-empty frame on a mis-parse
  (RESEARCH Pitfall 5).
- Parameter ``tl_mittel`` (daily mean air temperature, °C); resolve renames via
  metadata + ADR (ING-092). No auth needed; cache per ING-009; ≥ 0.2 s sleep.
- Raw contract (§7): ``date, station_id, tl_mittel_c, parameter_raw`` + ING-004
  columns. Written via ``_io.write_month(..., key_column="date")`` — GeoSphere
  is date-keyed, not ``ts_utc``-keyed (Pattern 1 / RESEARCH Pitfall 1).
- Gates (ING-094): coverage ≥ 99% of days; −30 ≤ tl_mittel ≤ 42; July mean in
  [15, 30]; January mean in [−10, 8].

Implements: ING-090, ING-091, ING-092, ING-093, ING-002, ING-006 (retry), ING-009 (cache).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from calendar import monthrange
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import pandas as pd
import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from epra.common import logging as common_logging
from epra.common.config import Settings, load_settings, resolve_repo_path
from epra.common.timeutil import iter_month_starts, today_local
from epra.ingest._io import _now_utc, request_hash, write_month
from epra.ingest.exceptions import (
    ContractError,
    DiscoveryError,
    IngestError,
    IngestTransportError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StationInfo:
    """A GeoSphere station's discovery-relevant metadata (ING-091).

    Implements: ING-091.
    """

    id: str
    name: str
    lat: float
    lon: float
    record_start: date


#: Transport seam for the metadata fetch — takes the validated settings,
#: returns the raw parsed JSON payload (untyped, external data). Defaults to
#: `_default_metadata_transport` (real network); tests inject a stub
#: returning the committed fixture instead (mirrors `_fetch.TransportFn` /
#: ADR-003's test-double pattern, D-07's live-first/fixture-fallback split).
MetadataTransportFn = Callable[[Settings], Any]

#: Transport seam for the daily-data fetch — takes the validated settings,
#: the pinned station id, and the target calendar month; returns the raw
#: parsed JSON (GeoJSON-shaped) payload. Defaults to `_default_data_transport`
#: (real network); tests inject a stub returning the committed
#: `tests/fixtures/geosphere/klima_2019-01.geojson` fixture instead (D-07).
DataTransportFn = Callable[[Settings, str, date], Any]


def _default_metadata_transport(settings: Settings) -> Any:
    """Live GET of the GeoSphere station metadata endpoint (no auth, ING-093).

    Implements: ING-091, ING-093.
    """
    url = (
        f"{settings.geosphere.base_url}/station/historical/{settings.geosphere.dataset_id}/metadata"
    )
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def _load_metadata(
    settings: Settings, *, transport: MetadataTransportFn | None = None
) -> list[Any]:
    """Fetch the metadata payload and validate its top-level shape.

    Validates the top-level shape BEFORE any nested indexing (Security:
    malformed/oversized response, research Pitfall 5) — raises `ContractError`
    rather than crashing on a `KeyError`/`TypeError` deep inside the parser.
    """
    transport_fn = transport if transport is not None else _default_metadata_transport
    payload = transport_fn(settings)
    if not isinstance(payload, dict):
        raise ContractError(
            "geosphere_metadata",
            expected="top-level JSON object",
            actual=type(payload).__name__,
        )
    stations = payload.get("stations", payload.get("features"))
    if not isinstance(stations, list):
        raise ContractError(
            "geosphere_metadata",
            expected="a 'stations' (or 'features') list at the top level",
            actual=f"keys={sorted(payload.keys())}",
        )
    return stations


def _station_record_start(station: dict[str, Any]) -> date:
    """Parse a station's ``valid_from`` ISO timestamp into its record-start date."""
    valid_from = station.get("valid_from")
    if not isinstance(valid_from, str):
        raise ContractError(
            "geosphere_metadata",
            expected="station.valid_from ISO timestamp string",
            actual=repr(valid_from),
        )
    return datetime.fromisoformat(valid_from).date()


def _graz_candidates(stations: list[Any]) -> list[dict[str, Any]]:
    """ING-091 filter: stations whose name contains "Graz"; raise listing all names if none.

    Implements: ING-091.
    """
    candidates = [s for s in stations if isinstance(s, dict) and "Graz" in str(s.get("name", ""))]
    if not candidates:
        available = sorted({str(s.get("name", "?")) for s in stations if isinstance(s, dict)})
        raise DiscoveryError(
            "geosphere",
            f"no station name contains 'Graz' among {len(stations)} candidates; "
            f"available: {available}",
        )
    return candidates


def _longest_record_key(station: dict[str, Any]) -> tuple[date, bool]:
    """ING-091 sort key: earliest ``valid_from`` (longest record) first; ties prefer
    a name containing "Graz Universität" (``False`` sorts before ``True``).

    Implements: ING-091.
    """
    name = str(station.get("name", ""))
    return (_station_record_start(station), "Graz Universität" not in name)


def discover_station(
    settings: Settings, *, transport: MetadataTransportFn | None = None
) -> StationInfo:
    """ING-091: pick the Graz station with the longest record.

    Implements: ING-091.

    Fetches the ``klima-v2-1d`` station metadata (live by default; inject
    `transport` in tests to use the committed fixture instead) and filters to
    stations whose name contains "Graz". The candidate with the earliest
    ``valid_from`` (i.e. the longest record) wins; ties are broken by
    preferring the station whose name contains "Graz Universität".

    Args:
        settings: injected config; never re-read YAML here (EN-040).
        transport: override for the live metadata fetch. Defaults to
            `_default_metadata_transport` (real network); tests inject a
            stub returning the committed `tests/fixtures/geosphere/
            metadata.json` fixture (D-07).

    Returns:
        The chosen station's id/name/lat/lon/record_start. The caller
        persists this into `config/settings.yaml` + ADR-007 — this function
        only discovers and reports (it never writes config itself).

    Raises:
        ContractError: the metadata payload's top-level shape is malformed,
            or a candidate station is missing/has an unparseable
            `valid_from`.
        DiscoveryError: no station name contains "Graz"; the message lists
            every available station name so the failure feeds directly into
            the ADR or a human checkpoint.
    """
    stations = _load_metadata(settings, transport=transport)
    chosen = min(_graz_candidates(stations), key=_longest_record_key)
    station = StationInfo(
        id=str(chosen["id"]),
        name=str(chosen["name"]),
        lat=float(chosen["lat"]),
        lon=float(chosen["lon"]),
        record_start=_station_record_start(chosen),
    )
    logger.info(
        "source=geosphere_metadata status=discovered station_id=%s name=%s record_start=%s",
        station.id,
        station.name,
        station.record_start.isoformat(),
    )
    return station


# ---------------------------------------------------------------------------
# parse_geojson — GeoSphere daily response -> the §7 date-keyed frame (ING-092)
# ---------------------------------------------------------------------------

#: The §7 raw contract's own columns (before ING-004 provenance is appended).
_RAW_COLUMNS = ("date", "station_id", "tl_mittel_c", "parameter_raw")


def _empty_raw_frame() -> pd.DataFrame:
    """Correctly-typed empty §7 frame -- a genuinely empty response window."""
    return pd.DataFrame(
        {
            "date": pd.Series([], dtype="object"),
            "station_id": pd.Series([], dtype="object"),
            "tl_mittel_c": pd.Series([], dtype="float64"),
            "parameter_raw": pd.Series([], dtype="object"),
        }
    )


def _top_level_lists(payload: Any) -> tuple[list[Any], list[Any]]:
    """Validate and return the top-level ``(timestamps, features)`` lists (RESEARCH Pitfall 5)."""
    if not isinstance(payload, dict):
        raise ContractError(
            "geosphere_graz_daily", expected="top-level JSON object", actual=type(payload).__name__
        )
    timestamps = payload.get("timestamps")
    features = payload.get("features")
    if not isinstance(timestamps, list) or not isinstance(features, list):
        raise ContractError(
            "geosphere_graz_daily",
            expected="'timestamps' and 'features' lists at the top level",
            actual=f"keys={sorted(payload.keys())}",
        )
    return timestamps, features


def _tl_mittel_values(features: list[Any], n_timestamps: int) -> list[Any]:
    """``features[0].properties.parameters.tl_mittel.data``, validated against ``timestamps``."""
    if not features:
        raise ContractError(
            "geosphere_graz_daily",
            expected="a non-empty 'features' list (timestamps present but no feature)",
            actual="features=[]",
        )
    feature = features[0]
    properties = feature.get("properties") if isinstance(feature, dict) else None
    parameters = properties.get("parameters") if isinstance(properties, dict) else None
    tl_mittel = parameters.get("tl_mittel") if isinstance(parameters, dict) else None
    data = tl_mittel.get("data") if isinstance(tl_mittel, dict) else None
    if not isinstance(data, list):
        raise ContractError(
            "geosphere_graz_daily",
            expected="features[0].properties.parameters.tl_mittel.data list",
            actual=f"features[0]={feature!r}"[:200],
        )
    if len(data) != n_timestamps:
        raise ContractError(
            "geosphere_graz_daily",
            expected=f"tl_mittel.data length matching timestamps length ({n_timestamps})",
            actual=f"{len(data)}",
        )
    return data


def parse_geojson(payload: Any, station_id: str) -> pd.DataFrame:
    """Parse a GeoSphere ``klima-v2-1d`` daily GeoJSON response into the §7 frame.

    Implements: ING-092.

    The response shape is a top-level ``timestamps`` array running parallel
    to ``features[0].properties.parameters.tl_mittel.data[]`` (one feature
    per requested station) — confirmed against the committed fixture
    ``tests/fixtures/geosphere/klima_2019-01.geojson``.

    Validates the top-level shape BEFORE any nested indexing (RESEARCH
    Pitfall 5): a malformed/mismatched payload raises `ContractError`, never
    a silently-empty frame — that would be indistinguishable from a
    genuinely empty window. A payload with an empty (but present) top-level
    ``timestamps``/``features`` pair IS a genuinely empty window and returns
    an empty (correctly-typed) frame.

    Args:
        payload: parsed JSON response (``response.json()`` shape).
        station_id: the requesting station id — stamped onto every row (not
            re-derived from the response body).

    Returns:
        DataFrame with columns ``date`` (python `date`), ``station_id``
        (str), ``tl_mittel_c`` (float64), ``parameter_raw`` (the raw JSON
        literal of the value as provided, str). One row per day present in
        the response — missing days are absent, never filled (A-2).

    Raises:
        ContractError: the payload's top-level shape does not match the
            expected GeoJSON structure, or ``tl_mittel.data`` length does not
            match ``timestamps`` length.
    """
    timestamps, features = _top_level_lists(payload)
    if not timestamps and not features:
        # Genuinely empty window (e.g. a future/not-yet-published range) --
        # not a mis-parse, so this does NOT raise (A-2 distinguishes the two).
        return _empty_raw_frame()
    data = _tl_mittel_values(features, len(timestamps))
    return pd.DataFrame(
        {
            "date": pd.to_datetime(timestamps, utc=True).date,
            "station_id": station_id,
            "tl_mittel_c": pd.Series(data, dtype="float64"),
            "parameter_raw": [json.dumps(v) for v in data],
        }
    )


# ---------------------------------------------------------------------------
# _fetch_geosphere — no-auth GET + ING-009 cache + ING-007 politeness (ING-093)
# ---------------------------------------------------------------------------


def _month_end(month: date) -> date:
    """Last calendar day of `month` (inclusive) — the GeoSphere `end` query param."""
    _, last_day = monthrange(month.year, month.month)
    return date(month.year, month.month, last_day)


def _request_url(settings: Settings, station_id: str, month: date) -> str:
    """Deterministic GeoSphere data-endpoint URL for one calendar month.

    Used both as the live GET URL and as the ING-009 cache/request_hash key
    — GeoSphere has no auth token to strip (unlike `_fetch._cache_request_url`
    for ENTSO-E), so this is also the literal URL sent over the wire.

    Implements: ING-090, ING-009.
    """
    params = {
        "parameters": settings.geosphere.parameter,
        "station_ids": station_id,
        "start": month.isoformat(),
        "end": _month_end(month).isoformat(),
        "output_format": "geojson",
    }
    return (
        f"{settings.geosphere.base_url}/station/historical/{settings.geosphere.dataset_id}"
        f"?{urlencode(sorted(params.items()))}"
    )


def _default_data_transport(settings: Settings, station_id: str, month: date) -> Any:
    """Live GET of one calendar month of GeoSphere `tl_mittel` daily data (no auth, ING-093).

    Implements: ING-090, ING-093.
    """
    response = requests.get(_request_url(settings, station_id, month), timeout=30)
    response.raise_for_status()
    return response.json()


def _cache_root(settings: Settings) -> Path:
    """Absolute, REPO_ROOT-anchored path of `data/cache/geosphere/` (ING-009).

    Implements: ING-009.
    """
    return resolve_repo_path(settings.paths.data_cache) / "geosphere"


def _cache_path(settings: Settings, req_hash: str) -> Path:
    return _cache_root(settings) / f"{req_hash}.json"


def _is_cache_eligible(month: date, settings: Settings) -> bool:
    """ING-009: cache is used only once the requested month is safely in the past.

    Implements: ING-009.
    """
    cutoff = _now_utc().date() - timedelta(days=settings.ingest.cache_min_age_days)
    return _month_end(month) <= cutoff


#: HTTP statuses ING-006 forbids retrying -- raised immediately with the response body.
_NO_RETRY_STATUS = frozenset({400, 401, 403})


def _http_status(exc: BaseException) -> int | None:
    """HTTP status code carried by a `requests`-shaped exception, if any."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


def _is_retryable(exc: BaseException) -> bool:
    """ING-006 retry predicate: 429, 5xx and connection errors/timeouts only.

    Implements: ING-006.
    """
    if isinstance(exc, IngestError):
        return False
    status = _http_status(exc)
    if status is not None:
        return status == 429 or status >= 500
    return isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))


def _transport_error(exc: BaseException, month: date) -> IngestTransportError:
    """Wrap a failed GeoSphere call; the response body goes into the message (ING-006).

    Implements: ING-006.
    """
    status = _http_status(exc)
    body = getattr(getattr(exc, "response", None), "text", None)
    detail = str(body)[:500] if body else f"{type(exc).__name__}: {exc}"
    return IngestTransportError(
        "geosphere", f"month={month:%Y-%m} status={status}: {detail}", status_code=status
    )


@retry(
    wait=wait_exponential(multiplier=2, min=2, max=120),
    stop=stop_after_attempt(6),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _call_with_retry(
    transport_fn: DataTransportFn, settings: Settings, station_id: str, month: date
) -> Any:
    try:
        return transport_fn(settings, station_id, month)
    except Exception as exc:
        if _http_status(exc) in _NO_RETRY_STATUS:
            raise _transport_error(exc, month) from exc
        raise


def _fetch_live(
    transport_fn: DataTransportFn, settings: Settings, station_id: str, month: date
) -> Any:
    """One live GeoSphere call under ING-006: retry 429/5xx/connection errors (6 attempts,
    exponential 2..120 s); 400/401/403 or exhausted retries raise `IngestTransportError`.

    Implements: ING-006.
    """
    try:
        return _call_with_retry(transport_fn, settings, station_id, month)
    except IngestError:
        raise
    except Exception as exc:  # retries exhausted, or a non-HTTP failure
        raise _transport_error(exc, month) from exc


def _write_cache(cache_path: Path, payload: Any) -> None:
    """Atomically persist one response (temp file, then ``os.replace``).

    Per-call-unique temp name (PID + short uuid4) mirrors `_io.write_month` /
    `_fetch.fetch_entsoe`'s WR-02 guard against two processes racing to write
    the same cache key.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.parent / f"{cache_path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    tmp_path.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp_path, cache_path)


def _fetch_geosphere(
    settings: Settings,
    station_id: str,
    month: date,
    *,
    transport: DataTransportFn | None = None,
) -> Any:
    """Fetch one calendar month of GeoSphere daily `tl_mittel` data (ING-093).

    Mirrors `_fetch.fetch_entsoe`'s cache/politeness shape at GeoSphere's
    smaller scope: no auth token (no A-7 stripping needed), an on-disk cache
    under `data/cache/geosphere/` (ING-009's 7-day rule, atomic
    temp-file-then-rename), and a `settings.ingest.geosphere_sleep_s` (>=0.2s,
    ING-007) sleep after every LIVE fetch only — a cache hit never sleeps.

    Only responses for windows that are already cache-eligible (ended > 7 days
    ago) are persisted. A response for a still-open or just-closed month may
    be incomplete (publication lag); caching it would let a later run -- once
    the month turns eligible -- replay that incomplete payload forever instead
    of re-fetching the final data.

    Live calls go through the ING-006 retry policy (`_fetch_live`): a
    transient 429/5xx/connection error no longer aborts a multi-year pull
    half-way (leaving a silently truncated series on disk).

    Implements: ING-006, ING-007, ING-009, ING-093.

    Args:
        transport: override for the live network call. Defaults to
            `_default_data_transport` (real `requests.get`); tests inject a
            stub returning the committed GeoJSON fixture (D-07).

    Returns:
        Parsed JSON payload (`response.json()` shape) ready for
        `parse_geojson`.
    """
    transport_fn = transport if transport is not None else _default_data_transport
    req_hash = request_hash(_request_url(settings, station_id, month))
    cache_path = _cache_path(settings, req_hash)
    eligible = _is_cache_eligible(month, settings)

    if cache_path.exists() and eligible:
        logger.info("source=geosphere_graz_daily month=%s status=cache_hit", f"{month:%Y-%m}")
        return json.loads(cache_path.read_text(encoding="utf-8"))

    payload = _fetch_live(transport_fn, settings, station_id, month)
    if eligible:
        _write_cache(cache_path, payload)

    logger.info("source=geosphere_graz_daily month=%s status=200", f"{month:%Y-%m}")
    time.sleep(settings.ingest.geosphere_sleep_s)  # ING-007 -- paces the *next* live call

    return payload


# ---------------------------------------------------------------------------
# ingest (ING-093)
# ---------------------------------------------------------------------------


def _require_station_id(settings: Settings) -> str:
    """Fail fast if station discovery (ING-091/ADR-007) hasn't been pinned yet.

    Implements: ING-091.
    """
    station_id = settings.geosphere.station_id
    if not station_id:
        raise DiscoveryError(
            "geosphere",
            "settings.geosphere.station_id is not set -- run discover_station() "
            "first and record the result in config/settings.yaml + ADR-007",
        )
    return station_id


def ingest(
    settings: Settings,
    start: date,
    end: date,
    transport: DataTransportFn | None = None,
) -> list[date]:
    """Ingest GeoSphere daily temperatures into monthly date-keyed parquet.

    Implements: ING-093, ING-003.

    Iterates calendar months in ``[start, end]`` (`timeutil.iter_month_starts`),
    fetches each month's GeoJSON (`_fetch_geosphere` — ING-009 cache, ING-007
    politeness sleep), parses via `parse_geojson`, and writes through
    `_io.write_month(..., key_column="date")` — GeoSphere's `date` grain, not
    `ts_utc` (Pattern 1 / RESEARCH Pitfall 1).

    Args:
        transport: forwarded to `_fetch_geosphere`; `None` uses the real
            network. Tests inject a stub returning the committed GeoJSON
            fixture (D-07).

    Returns:
        The month starts actually written, in order. A month whose response
        is empty is skipped with a WARNING (never silently), and the run ends
        with one summary line naming the requested window, the last month
        written and every empty month -- so a pull that stops short of the
        requested end is visible in the log rather than only in the data.

    Raises:
        DiscoveryError: `settings.geosphere.station_id` is unset (run
            `discover_station()` first, ADR-007) — checked before any
            network call.
        IngestTransportError: a live call failed after the ING-006 retries.
    """
    station_id = _require_station_id(settings)
    written: list[date] = []
    empty: list[str] = []
    for month in iter_month_starts(start, end):
        payload = _fetch_geosphere(settings, station_id, month, transport=transport)
        frame = parse_geojson(payload, station_id)
        if frame.empty:
            logger.warning(
                "dataset=geosphere_graz_daily month=%s no data -- skipping write", f"{month:%Y-%m}"
            )
            empty.append(f"{month:%Y-%m}")
            continue
        req_hash = request_hash(_request_url(settings, station_id, month))
        write_month(frame, "geosphere_graz_daily", month, req_hash, settings, key_column="date")
        written.append(month)
    logger.info(
        "dataset=geosphere_graz_daily requested=%s..%s months_written=%d last_written=%s "
        "empty_months=%s",
        start.isoformat(),
        end.isoformat(),
        len(written),
        f"{written[-1]:%Y-%m}" if written else "none",
        empty,
    )
    return written


def _parse_cli_date(text: str) -> date:
    """`argparse` `type=` callback (T-02-10): reject anything not YYYY-MM-DD."""
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {text!r}; expected YYYY-MM-DD") from exc


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.geosphere [--start YYYY-MM-DD] [--end YYYY-MM-DD]`` (ING-002).

    Defaults: ``--start`` to ``settings.window.start_date`` (2019-01-01),
    ``--end`` to today's Europe/Vienna date — so a bare invocation (e.g.
    ``make geosphere``) ingests the full 2019-latest window (ING-093),
    matching `entsoe.py`'s mode-flag-only ergonomics (no required date args).
    The logfile lands under the REPO_ROOT-anchored ``reports/ingestion/``.

    Returns 0 on success, 1 on a user/validation error (invalid window, or
    `settings.geosphere.station_id` unset — run `discover_station()` first)
    or an ingest failure (e.g. `IngestTransportError` after ING-006 retries).

    Implements: ING-002, ING-093, EN-060.
    """
    parser = argparse.ArgumentParser(
        prog="python -m epra.ingest.geosphere",
        description="GeoSphere daily temperature ingestion: 2019-01-01 -> latest (ING-093).",
    )
    parser.add_argument(
        "--start",
        type=_parse_cli_date,
        default=None,
        help="Override ingest start date (YYYY-MM-DD). Default: settings.window.start_date.",
    )
    parser.add_argument(
        "--end",
        type=_parse_cli_date,
        default=None,
        help="Override ingest end date (YYYY-MM-DD). Default: today (Europe/Vienna).",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    logfile = (
        resolve_repo_path(settings.paths.reports)
        / "ingestion"
        / f"geosphere_{today_local():%Y-%m-%d}.log"
    )
    common_logging.setup(logfile=logfile)

    start = args.start if args.start is not None else settings.window.start_date
    end = args.end if args.end is not None else today_local()

    try:
        if end <= start:
            raise ValueError(f"invalid window: end ({end}) must be after start ({start})")
        ingest(settings, start, end)
    except (ValueError, IngestError) as exc:
        logger.error("geosphere ingest failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
