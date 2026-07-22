"""GeoSphere Austria ingestion — daily mean temperature, Graz (M2).

Station discovery (ING-090..092) is implemented in this plan; the monthly
`tl_mittel` ingest (ING-093/094) lands in 03-04. Binding contract: SPEC-01 §9.
Key points:

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
- Parameter ``tl_mittel`` (daily mean air temperature, °C); resolve renames via
  metadata + ADR (ING-092). No auth needed; cache per ING-009; ≥ 0.2 s sleep.
- Raw contract (§7): ``date, station_id, tl_mittel_c, parameter_raw`` + ING-004
  columns.
- Gates (ING-094): coverage ≥ 99% of days; −30 ≤ tl_mittel ≤ 42; July mean in
  [15, 30]; January mean in [−10, 8].

Implements: ING-090, ING-091, ING-092.
Implements (when built, 03-04): ING-093, ING-094.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import requests

from epra.common.config import Settings
from epra.ingest.exceptions import ContractError, DiscoveryError

logger = logging.getLogger(__name__)

_MSG = "M2 not implemented yet — build per SPEC-01 §9 (see module docstring)"


@dataclass(frozen=True)
class StationInfo:
    """A GeoSphere station's discovery-relevant metadata (ING-091)."""

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


def _default_metadata_transport(settings: Settings) -> Any:
    """Live GET of the GeoSphere station metadata endpoint (no auth, ING-093)."""
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


def discover_station(
    settings: Settings, *, transport: MetadataTransportFn | None = None
) -> StationInfo:
    """ING-091: pick the Graz station with the longest record.

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
    candidates = [s for s in stations if isinstance(s, dict) and "Graz" in str(s.get("name", ""))]
    if not candidates:
        available = sorted({str(s.get("name", "?")) for s in stations if isinstance(s, dict)})
        raise DiscoveryError(
            "geosphere",
            f"no station name contains 'Graz' among {len(stations)} candidates; "
            f"available: {available}",
        )

    def _sort_key(station: dict[str, Any]) -> tuple[date, bool]:
        name = str(station.get("name", ""))
        # Earliest valid_from = longest record; on a tie, prefer a name
        # containing "Graz Universität" (False sorts before True).
        return (_station_record_start(station), "Graz Universität" not in name)

    chosen = min(candidates, key=_sort_key)
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


def ingest(settings: Settings, start: date, end: date) -> None:
    """Ingest daily temperatures into monthly parquet per SPEC-01 §7 contract."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.geosphere --start YYYY-MM-DD --end YYYY-MM-DD`` (ING-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
