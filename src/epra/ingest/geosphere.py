"""GeoSphere Austria ingestion — daily mean temperature, Graz (M2).

Not yet implemented. Binding contract: SPEC-01 §9. Key points:

- MANDATORY first step is station discovery (ING-091): fetch
  ``/station/historical/klima-v2-1d/metadata``, pick the Graz station with the
  longest record (prefer "Graz Universität"), record station_id/name/lat/lon in
  ``config/settings.yaml`` under ``geosphere:`` AND in an ADR. Do not hardcode.
- Parameter ``tl_mittel`` (daily mean air temperature, °C); resolve renames via
  metadata + ADR (ING-092). No auth needed; cache per ING-009; ≥ 0.2 s sleep.
- Raw contract (§7): ``date, station_id, tl_mittel_c, parameter_raw`` + ING-004
  columns.
- Gates (ING-094): coverage ≥ 99% of days; −30 ≤ tl_mittel ≤ 42; July mean in
  [15, 30]; January mean in [−10, 8].

Implements (when built): ING-090..094.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from epra.common.config import Settings

_MSG = "M2 not implemented yet — build per SPEC-01 §9 (see module docstring)"


def discover_station(settings: Settings) -> dict[str, str]:
    """ING-091 discovery: return the chosen station's id/name/lat/lon.

    The result is written into config/settings.yaml and an ADR by the operator;
    this function only discovers and reports.
    """
    raise NotImplementedError(_MSG)


def ingest(settings: Settings, start: date, end: date) -> None:
    """Ingest daily temperatures into monthly parquet per SPEC-01 §7 contract."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.geosphere --start YYYY-MM-DD --end YYYY-MM-DD`` (ING-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
