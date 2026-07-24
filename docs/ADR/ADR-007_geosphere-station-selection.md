# ADR-007: GeoSphere station selection (ING-091)

**Status:** accepted
**Date:** 2026-07-23
**Deciders:** M2 auxiliary-data ingestion (EPRA-03), plan 03-03
**Related:** SPEC-01 §9 (ING-090..094), D-07 (03-CONTEXT.md live-first/fixture-fallback),
research Pitfall 5 (GeoSphere response shape), R-7 (naming drift risk register)

## Context

ING-091 mandates a one-time discovery step before any GeoSphere ingestion: fetch
`/station/historical/klima-v2-1d/metadata`, list stations, and select the station whose
name matches "Graz" with the longest record, preferring "Graz Universität" on ties. The
chosen `station_id`/name/lat/lon must be recorded in `config/settings.yaml` under
`geosphere:` and in this ADR — never hardcoded in `geosphere.py` itself.

D-07 additionally requires attempting the live discovery call in-phase and, if the agent
environment can reach GeoSphere, using the real result now rather than deferring to a
human checkpoint. Outbound network to `dataset.api.hub.geosphere.at` was reachable in
this execution session, so the live path was taken.

**Dataset id verification (ING-090):** `klima-v2-1d` exists and its metadata payload's
`title` field reads `"Stationsdaten-v2 (1 d): Qualitätsgeprüfte Stationsdaten für
Österreich in täglicher Auflösung"` — confirming this is the correct daily
quality-checked station-climate dataset. No substitution needed.

**Metadata response shape (research Pitfall 5 resolved):** the live `/metadata` endpoint
returns a flat JSON object with a top-level `stations` list — each entry shaped like
`{"id": 30, "name": "Graz Universität/Heinrichstraße", "state": "Steiermark", "lat":
47.08, "lon": 15.448056, "valid_from": "1894-01-01T00:00:00+00:00", "valid_to":
"2100-12-31T00:00:00+00:00", "is_active": true, ...}` — **not** a GeoJSON
`FeatureCollection` with `features[].properties`. SPEC-01 §9's `output_format=geojson`
query parameter is documented on the *data* endpoint
(`/station/historical/klima-v2-1d?...&output_format=geojson`), not on `/metadata`, which
has no such parameter and returns this flat shape unconditionally. `discover_station`'s
`_load_metadata` validates the top-level shape before indexing (accepting either
`stations` or a GeoJSON-style `features` key defensively, since no OpenAPI schema
independently pins the metadata endpoint's contract) and raises `ContractError`
otherwise.

**Live candidates matching "Graz":** the metadata response lists 9 stations whose name
contains "Graz". The two with the earliest `valid_from` (1894-01-01, tied for longest
record) are:

| id | name | valid_from | valid_to | is_active |
|----|------|-----------|----------|-----------|
| 30 | Graz Universität/Heinrichstraße | 1894-01-01 | 2100-12-31 (open) | true |
| 16402 | Graz Universität | 1894-01-01 | 1988-05-31 (closed) | false |

Station 30 is GeoSphere's `type: "COMBINED"` record — the continuous series across the
site's history, including the periods separately catalogued under the plain-named
`Graz Universität` (id 16402, closed 1988) and its 1988-onward continuation (id 16412,
also named exactly `Graz Universität`). Station 30 is the ONE still-active record
(`valid_to: 2100-12-31` is GeoSphere's "still open" sentinel) spanning the full
1894-present range at this site.

## Decision

`discover_station()` implements the tie-break exactly as ING-091 specifies: sort Graz
candidates by `valid_from` ascending (earliest = longest record), and on a tie, prefer
the candidate whose name contains "Graz Universität" as a substring. Both tied
candidates (id 30 and id 16402) satisfy that substring check, so the (stable) sort
falls through to list order; `min()` over the live response deterministically selects
**station id `30`, "Graz Universität/Heinrichstraße"** — the `COMBINED` record that is
both the longest continuous series at the site AND the one still actively reporting
data today, which is also the operationally correct choice for an ongoing 2019→latest
ingest (the closed 1988 sub-record, id 16402, cannot supply any data past 1988).

Recorded in `config/settings.yaml`:

```yaml
geosphere:
  station_id: "30"
  station_name: "Graz Universität/Heinrichstraße"
```

lat/lon: `47.08, 15.448056` (state: Steiermark; record_start: 1894-01-01).

This is a live, in-phase discovery result (D-07's "reachable" branch) — not a pending
human checkpoint. `tests/unit/test_geosphere.py`'s deterministic tie-break test uses a
separately committed, crafted fixture (`tests/fixtures/geosphere/metadata.json`) rather
than this live response, so CI remains network-free (D-06/D-07); the crafted fixture
deliberately ties two Graz stations on `valid_from` (with the non-"Universität" decoy
ordered first in the list) so the test only passes if the name-preference tie-break is
actually applied, not merely "first Graz entry wins".

## Consequences

- The GeoSphere station is pinned in config + this ADR, never hardcoded in
  `geosphere.py` (SPEC-01 §9 ING-091 prohibition).
- 03-04's `ingest()` reads `settings.geosphere.station_id` ("30") when calling the data
  endpoint (`/station/historical/klima-v2-1d?...&station_ids=30&parameters=tl_mittel`).
- `geosphere.py`'s module docstring documents the confirmed metadata response shape
  (flat `stations` list, not GeoJSON) so 03-04 does not have to re-derive it against a
  fresh live pull.
- If GeoSphere ever retires/renames station id 30, or its `is_active` flips to false
  mid-project, that is a new discovery event requiring a follow-up ADR — `station_id`
  is a pinned, human-reviewed value, not re-derived per ingest run (by design, per the
  research's "Pattern 2: discovery-then-ingest, ADR-gated").

## Spec deviations

None. ING-090/091/092 are implemented as specified; the metadata response shape finding
above is new factual information discovered at build time (SPEC-01 §9 did not literally
specify `/metadata`'s payload shape), not a deviation from any pinned contract.
