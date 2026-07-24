---
phase: EPRA-03-m2-auxiliary-data
plan: 03
subsystem: ingestion
tags: [geosphere, requests, discovery, pydantic, adr]

# Dependency graph
requires:
  - phase: EPRA-03-m2-auxiliary-data (03-02)
    provides: calendar hourly spine, holidays-based build_calendar()
provides:
  - epra.ingest.geosphere.StationInfo dataclass + discover_station(settings, transport=)
  - DiscoveryError exception (epra.ingest.exceptions)
  - tests/fixtures/geosphere/metadata.json (committed tie-break fixture)
  - config/settings.yaml geosphere.station_id/station_name filled with live-discovered station
  - docs/ADR/ADR-007_geosphere-station-selection.md
affects: [03-04 (geosphere ingest/main), validate.py ING-094 gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Transport-injection seam for a small no-auth GET (mirrors _fetch.py's TransportFn without generalizing it, per research's 'Alternatives Considered')"
    - "Live-first / fixture-fallback discovery (D-07): attempt real network in-phase, fall back to a committed fixture for CI determinism only if unreachable"

key-files:
  created:
    - src/epra/ingest/geosphere.py (StationInfo, discover_station, _load_metadata — ingest/main remain M2 stubs for 03-04)
    - tests/unit/test_geosphere.py
    - tests/fixtures/geosphere/metadata.json
    - docs/ADR/ADR-007_geosphere-station-selection.md
  modified:
    - src/epra/ingest/exceptions.py (new DiscoveryError)
    - config/settings.yaml (geosphere.station_id/station_name filled)
    - tests/unit/test_stubs_fail_loudly.py (geosphere.discover_station row removed)
    - tests/unit/test_config.py (pending-discovery test flipped to assert ADR'd station)

key-decisions:
  - "discover_station picks the Graz candidate with the earliest valid_from (longest record), tie-broken by preferring a name containing 'Graz Universität' — implemented as a stable min() over (record_start, name_not_universitaet)"
  - "Live GeoSphere /metadata endpoint returns a flat {'stations': [...]} object, not a GeoJSON FeatureCollection as SPEC-01 §9's output_format=geojson framing (which applies only to the data endpoint) suggested — _load_metadata accepts 'stations' or a defensive 'features' fallback and validates top-level shape before any nested indexing (T-03-05)"
  - "Live discovery succeeded in this session (network reachable) — station id 30, 'Graz Universität/Heinrichstraße', the COMBINED longest-record (1894-present) still-active station, chosen over the closed 1988 sub-record id 16402 that ties on valid_from but stopped reporting decades ago"
  - "config/settings.yaml.geosphere.station_id/station_name filled from the live result per D-07's 'reachable' branch — not deferred as a human checkpoint"

patterns-established:
  - "Discovery-then-ingest, ADR-gated: discover_station() is a one-off call whose *result* is persisted to config + an ADR, never re-run per ingest call (03-04 reads settings.geosphere.station_id, does not call discover_station again)"

requirements-completed: [ING-090, ING-091, ING-092]
# REQ-ING-01 stays open — it closes at 03-06 once all 6 Phase-3 plans + validation gates land, per orchestrator instruction.

coverage:
  - id: D1
    description: "discover_station(settings) returns the Graz station with the longest record, preferring 'Graz Universität' on ties, parsed from the GeoSphere station metadata JSON"
    requirement: ING-091
    verification:
      - kind: unit
        ref: "tests/unit/test_geosphere.py::test_discover_station_prefers_graz_universitaet"
        status: pass
      - kind: unit
        ref: "tests/unit/test_geosphere.py::test_discover_station_filters_out_non_graz_and_shorter_records"
        status: pass
    human_judgment: false
  - id: D2
    description: "Discovery is live-first (D-07); the metadata payload's top-level shape (stations/features list) is validated before any nested indexing, and a malformed/no-match response fails loudly with named candidates"
    requirement: ING-090
    verification:
      - kind: unit
        ref: "tests/unit/test_geosphere.py::test_discover_station_raises_when_no_graz_station"
        status: pass
      - kind: unit
        ref: "tests/unit/test_geosphere.py::test_discover_station_rejects_malformed_top_level_shape"
        status: pass
      - kind: unit
        ref: "tests/unit/test_geosphere.py::test_discover_station_rejects_payload_missing_stations_and_features"
        status: pass
      - kind: other
        ref: "uv run python -c \"discover_station(load_settings())\" — live call succeeded this session, station id 30"
        status: pass
    human_judgment: false
  - id: D3
    description: "The committed metadata.json fixture contains 'Graz Universität' plus a same-valid_from decoy Graz station, ordered before it in the list, so the tie-break is exercised deterministically in CI (not just 'first Graz station wins')"
    verification:
      - kind: unit
        ref: "tests/unit/test_geosphere.py::test_discover_station_prefers_graz_universitaet (fixture: tests/fixtures/geosphere/metadata.json)"
        status: pass
    human_judgment: false
  - id: D4
    description: "ADR-007 records the chosen station id/name/lat/lon, the tie-break rationale, and the verified klima-v2-1d dataset id; config/settings.yaml geosphere.station_id/station_name filled; geosphere.discover_station stub row removed"
    requirement: ING-092
    verification:
      - kind: unit
        ref: "tests/unit/test_stubs_fail_loudly.py (16 remaining STUBS parametrizations, geosphere.ingest/main still present)"
        status: pass
      - kind: unit
        ref: "tests/unit/test_config.py::test_settings_geosphere_station_discovered"
        status: pass
      - kind: other
        ref: "test -f docs/ADR/ADR-007_geosphere-station-selection.md"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-07-23
status: complete
---

# Phase EPRA-03 Plan 03: GeoSphere Station Discovery Summary

**GeoSphere `discover_station()` picks Graz Universität/Heinrichstraße (station 30, record since 1894) via a live-first tie-break over the real `/metadata` endpoint, with a committed fixture pinning the tie-break deterministically for CI; result recorded in ADR-007 and `config/settings.yaml`.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments

- `StationInfo` dataclass + `discover_station(settings, transport=)` implementing ING-091's exact tie-break rule (longest record, prefer "Graz Universität"), with a transport-injection seam so tests never hit the network
- `_load_metadata` validates the payload's top-level shape (dict with a `stations`/`features` list) BEFORE any nested indexing, raising `ContractError` on malformed responses (T-03-05 mitigation) instead of crashing on `KeyError`
- Discovered — via a live GeoSphere network call that succeeded in this session — that the real `/metadata` response shape is a flat `{"stations": [...]}` object, not the GeoJSON `FeatureCollection` the research/plan hedged toward; documented in the module docstring and ADR-007 so 03-04 doesn't have to re-derive it
- Live discovery result (station id `30`, "Graz Universität/Heinrichstraße", lat 47.08/lon 15.448056, record since 1894-01-01, still active) recorded in `config/settings.yaml` and `docs/ADR/ADR-007_geosphere-station-selection.md` — not deferred as a human checkpoint, since D-07's "reachable" branch applied
- `tests/fixtures/geosphere/metadata.json` committed with a deliberately order-adversarial tie ("Graz Nord Decoy" listed before "Graz Universität", both sharing the earliest `valid_from`) so the test only passes if the name-preference tie-break logic actually runs
- `geosphere.discover_station` stub row removed from `test_stubs_fail_loudly.py`; `geosphere.ingest`/`geosphere.main` remain (03-04's job)

## Task Commits

Each task was committed atomically:

1. **Task 1: discover_station with live-first / fixture-fallback and the tie-break test** - `5aed0ea` (feat)
2. **Task 2: ADR-007, settings.yaml station fill, and discover_station stub removal** - `fb00710` (docs)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `src/epra/ingest/geosphere.py` - `StationInfo`, `discover_station`, `_load_metadata`, `_station_record_start`, `_default_metadata_transport`; `ingest`/`main` remain `NotImplementedError` stubs for 03-04
- `src/epra/ingest/exceptions.py` - new `DiscoveryError(IngestError)` (names available candidates on no-match, mirrors `ContractError`/`GateFailure` style)
- `tests/unit/test_geosphere.py` - 6 deterministic tests (tie-break, filtering, no-match, malformed shape ×2) + 1 `@pytest.mark.live` real-network smoke test
- `tests/fixtures/geosphere/metadata.json` - crafted 4-station fixture in the real GeoSphere metadata shape (`stations` list), tie-break exercised deliberately
- `docs/ADR/ADR-007_geosphere-station-selection.md` - dataset-id verification, live response shape finding, tie-break rationale, chosen station
- `config/settings.yaml` - `geosphere.station_id: "30"`, `geosphere.station_name: "Graz Universität/Heinrichstraße"`, dataset id comment updated to "verified live"
- `tests/unit/test_stubs_fail_loudly.py` - `geosphere.discover_station` STUBS row removed
- `tests/unit/test_config.py` - `test_settings_geosphere_station_pending_discovery` renamed/flipped to `test_settings_geosphere_station_discovered`, asserting the ADR'd station id/name

## Decisions Made

- **Tie-break algorithm:** `min()` over `(record_start, "Graz Universität" not in name)` — earliest `valid_from` wins (longest record); on an exact tie, the name containing "Graz Universität" sorts first. Verified against the crafted fixture where the decoy is deliberately list-ordered before the real winner, so a naive "first match wins" implementation would fail the test.
- **Real metadata shape ≠ research's GeoJSON assumption:** the live `/station/historical/klima-v2-1d/metadata` endpoint returns `{"stations": [...], "parameters": [...], "title": ..., ...}`, not a `FeatureCollection`. SPEC-01 §9's `output_format=geojson` query parameter is documented on the *data* endpoint, not `/metadata`. `_load_metadata` still defensively accepts a `features` key as a fallback, since no OpenAPI schema independently pins this. Recorded in both the module docstring and ADR-007 so this doesn't need re-discovery in 03-04.
- **Chose the COMBINED record (id 30) over the closed sub-record (id 16402):** both tie on `valid_from` (1894-01-01) and both contain "Graz Universität" as a name substring, but id 30 ("Graz Universität/Heinrichstraße") is GeoSphere's `type: "COMBINED"` continuous series across the site's full history and is still actively reporting (`is_active: true`), while id 16402 ("Graz Universität") closed in 1988 and cannot supply any data for the 2019→latest ingest window. Stable-sort tie-break (list order — id 30 precedes id 16402 in the live response) selects the operationally correct station; documented explicitly in ADR-007 rather than left as an unexamined artifact of sort stability.
- **Live discovery, not a human checkpoint:** outbound network to `dataset.api.hub.geosphere.at` was reachable this session, so D-07's "reachable" branch applied — `config/settings.yaml` and ADR-007 record the real discovered station rather than `null` + a pending-checkpoint note.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Flipped `test_config.py`'s pending-discovery test to assert the ADR'd station**
- **Found during:** Task 2 verification (full suite run)
- **Issue:** `test_settings_geosphere_station_pending_discovery` asserted `s.geosphere.station_id is None`, which is now false now that discovery filled config — the test's own comment ("Once discovery runs, this test flips to asserting the ADR'd station id") anticipated exactly this change (also called out in the WBS T2.02 objective: "flip the pending-discovery config test to assert the chosen id").
- **Fix:** Renamed to `test_settings_geosphere_station_discovered`; asserts `station_id == "30"` and `station_name == "Graz Universität/Heinrichstraße"`.
- **Files modified:** `tests/unit/test_config.py`
- **Verification:** `uv run pytest -m "not live" -q` — full suite green (95.58% coverage).
- **Committed in:** `fb00710` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** Necessary correctness fix directly anticipated by the plan's own research/WBS text — not scope creep; without it the full suite would fail after Task 2.

## Issues Encountered

- Running `uv run pytest tests/unit/test_geosphere.py::test_discover_station_prefers_graz_universitaet -m "not live" -x` as a file/test subset (rather than the full suite) trips the project-wide `--cov-fail-under=80` gate even though the target test passes — the same known condition documented in `02-02-SUMMARY.md`/`03-01-SUMMARY.md`/`03-02-SUMMARY.md`. Resolved by verifying the subset with `--no-cov` and separately running the FULL suite (`uv run pytest -m "not live" -q`) for the real coverage gate: green at 95.58% (≥ 80% required).
- `uv run ruff format --check` flagged `tests/unit/test_io.py` as needing reformatting — pre-existing, already logged as deferred in `03-02-SUMMARY.md`, not touched by this plan.
- `uv run ruff format` initially flagged `src/epra/ingest/geosphere.py` for a line-length collapse in `_default_metadata_transport`'s URL f-string; applied `ruff format` before committing so the file matches the project's 100-char line-length formatting exactly.

## User Setup Required

None - no external service configuration required. The live GeoSphere discovery call succeeded automatically in this execution session (no auth needed, ING-093); no manual token/credential setup applies to this no-auth public API.

## Next Phase Readiness

- 03-04 (GeoSphere ingest + main + ING-094 gates) can now read `settings.geosphere.station_id`/`station_name` directly — no re-discovery needed, and the confirmed live metadata/data-endpoint shape split is documented for the data-endpoint parser to build against.
- `_io.write_month()`'s `ts_utc`-only assumption (research Pitfall 1) is still unresolved and remains 03-04's first concrete task — not touched by this plan, as scoped.
- No blockers identified for 03-04.

---
*Phase: EPRA-03-m2-auxiliary-data*
*Completed: 2026-07-23*

## Self-Check: PASSED

All created files (`src/epra/ingest/geosphere.py`, `src/epra/ingest/exceptions.py`,
`tests/unit/test_geosphere.py`, `tests/fixtures/geosphere/metadata.json`,
`docs/ADR/ADR-007_geosphere-station-selection.md`, `config/settings.yaml`, this
SUMMARY.md) exist on disk. Both task commits (`5aed0ea`, `fb00710`) verified present
in `git log --oneline --all`.
