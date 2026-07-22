# Phase 3: M2 Auxiliary Data - Research

**Researched:** 2026-07-22
**Domain:** External data ingestion (HTTP API + hand-curated CSV + pure calendar computation) completing the SPEC-01 ingestion layer
**Confidence:** MEDIUM-HIGH (code-level findings HIGH; external-source specifics MEDIUM — GeoSphere/ÖSPI details are CITED from official pages, not exhaustively enumerated against a live response)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ÖSPI series & methodology (SPEC-01 §10 · ING-102/104)**
- **D-01:** Use the **current-method** AEA ÖSPI series if it covers 2019→present as one consistent series; fall back to the long-running/legacy series **only** if current-method coverage is insufficient. **Never splice two methods.** Final pick is confirmed against the actual publication at transcription time and recorded in the methodology ADR.
- **D-02:** Target **Base + Peak**. If monthly Peak values are not published for part of 2019→latest, drop to **Base-only** (`peak_available: false`, SPEC-05 base-only behavior per ING-104) and record it in the ADR **and** `LIMITATIONS.md`.

**ÖSPI acquisition & double-entry (SPEC-01 §10 · ING-101, T2.04/T2.05)**
- **D-03:** The **human (operator) transcribes both entry1 and entry2 in separate sessions** — the spec's literal double-entry procedure. Not agent-transcribed.
- **D-04:** The AEA *strompreisindex* source is **not located yet** (at CONTEXT-gathering time) — locating the current publication is part of this checkpoint. The agent **finds/verifies the source URL and drafts the methodology ADR (series + source URLs) first (T2.04)**; the human confirms the source, then transcribes (T2.05).
- **D-05:** `load_oespi()` + the ING-103 gate set (continuity, positivity, 2022 peak ≥ 3× 2019 mean, MoM ≤ ±60%) are **built and unit-tested against a committed synthetic CSV** covering every gate's fail case. The **real reconciled `oespi_monthly.csv` is a committed human checkpoint**, not a blocker for shipping the loader/gates.

**Real-data boundary & phase close (reprises M1 ADR-006 / EN-070)**
- **D-06:** M2 closes on **code + fixture/synthetic gates green in CI** (network-free). Live GeoSphere pull + the reconciled real ÖSPI CSV land as **committed human/local checkpoints** with a validation report under `reports/ingestion/`. Do not gate CI on live network or real ÖSPI transcription.
- **D-07:** **GeoSphere (no auth, ING-093):** attempt `discover_station()` (ING-091) **live in-phase** and, if reachable, a real pull to get ING-094 green on real data now. If the agent env blocks outbound network, **fall back to a committed GeoJSON fixture** for parse/gate tests and mark the live pull as a human checkpoint. Either way, ship the parser + ING-094 gates against a fixture so CI is deterministic.

**Calendar forward horizon (SPEC-01 §11 · SG-15)**
- **D-08:** Forward-window end = **`latest_complete_month() + 18 months`**, recomputed each run (18 = the 12-month forward-risk sim per REQ-Q3 + a 6-month cushion for later convention shifts).
- **D-09:** **Compute the default `--end` dynamically from M1** (M1 is complete, so wire `epra.ingest.entsoe.latest_complete_month()` as the default). A fixed `--end` is used **only in tests** for determinism (e.g., `--end 2027-12-31`). The SG-15 "pre-M1 `--end` bootstrap" is moot since M1 exists.
- **D-10:** `is_peak_hour` comes from `epra.common.timeutil` — **never re-implemented** in `calendar.py`. Holidays via the `holidays` package, `subdiv='6'` for Styria (SG-10); the ING-111 test asserts the **working** subdiv code, and an ADR is written **only if** the working code deviates from `'6'`.

### Claude's Discretion
- **ADR numbering:** the WBS labels the new ADRs "ADR-003" (GeoSphere station) and "ADR-004" (ÖSPI methodology), but those numbers are already used (ADR-003 = entsoe-raw-client, ADR-004 = pyarrow). The GeoSphere-station ADR and ÖSPI-methodology ADR must take the **next free numbers: ADR-007 (GeoSphere station) and ADR-008 (ÖSPI methodology)**. Confirm against `docs/ADR/` at planning time.
- Internal module decomposition, helper naming, fixture byte content, synthetic-CSV values, and validation-report layout are the implementer's choice within the SPEC-01 contracts and REQ-ID docstrings (W-2), consistent with M1.
- GeoSphere station tie-break beyond "Graz, longest record, prefer *Graz Universität*" (ING-091) is resolved at discovery time and recorded in the station ADR.

### Deferred Ideas (OUT OF SCOPE)
- `dim_calendar` weather join (season, `hdd_18`, `cdd_22`) → M3/Phase 4 (SPEC-02 §4). Calendar here only produces the ING-110 spine.
- Canonical hourly aggregation of prices/load/generation → M3/Phase 4 (dbt staging). M2 does no aggregation.
- Consumer `peak_available`-dependent strategy formulas → M6/Phase 7 (SPEC-05). M2 only sets the `peak_available` flag on the ÖSPI data.

**Confirmed at planning time:** `docs/ADR/` currently contains ADR-001..006 only — ADR-007 and ADR-008 are indeed the next free numbers (verified by directory listing during this research session).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ING-01 | ENTSO-E (done, M1) + GeoSphere temperature + ÖSPI manual CSV (double-entry) + calendar/holidays ingested with validation gates green for 2019→latest (SPEC-01, M1+M2) | This research covers the M2 slice: GeoSphere endpoint verification (§9/ING-090..094), ÖSPI source verification + methodology resolution (§10/ING-100..104), Calendar/holiday build (§11/ING-110..111), and the shared `validate.py` gate-framework extension pattern that makes ING-094/101/103/111 gate-green. |
</phase_requirements>

## Summary

M2 completes the ingestion layer with three sources that are architecturally simpler than M1's ENTSO-E client (no auth, no retry-heavy pagination, no XML) but each has a genuine "what do I need to know before I plan this" gap the SPEC and WBS do not fully close:

1. **GeoSphere** — the API is real and reachable (confirmed via official docs at `dataset.api.hub.geosphere.at/v1/docs`); `klima-v2-1d` is a real station-based historical dataset, publicly accessible without auth (CC-BY 4.0). The critical planning-relevant finding is **not** about the external API — it's about the **internal write path**: GeoSphere's SPEC-01 §7 raw contract uses a plain `date` column, not `ts_utc`, but the already-built M1 writer `_io.write_month()` hard-requires a tz-aware UTC `ts_utc` column and raises `ContractError` otherwise. GeoSphere **cannot** call `write_month()` unmodified; the plan must extend `_io` (a small, additive, backward-compatible change) rather than duplicate a second writer or bend the §7 contract to add a `ts_utc` column it doesn't specify.

2. **ÖSPI** — this research resolves D-01/D-02 with reasonable confidence by fetching the actual AEA pages: the page at `https://www.energyagency.at/fakten/strompreisindex` (labeled "alte Methode" / old method, but still the actively-published, continuously-updated series — most recent fetched value was for a 2026 month) has published **both Base and Peak monthly values since a September 2018 methodology refinement**, so it plausibly covers 2019→present as ONE consistent series — satisfying D-01's "current-method covers 2019→present" branch directly, with Peak available throughout (favoring D-02's Base+Peak target over the Base-only fallback). A **separate, newer "Indices 2.0"** family (12 indices: monthly/quarterly/yearly × total/base/peak/off-peak) launched only in **December 2023 as a supplement, not a replacement** — it does NOT cover 2019–2023 and must NOT be spliced onto the older series (this is exactly the ING-102 methodology-break warning). No CSV/API exists — only PDF and Excel "Monatswerte" downloads — confirming the double-entry-by-hand approach (D-03..D-05) is necessary, not just conservative. **This pick must still be confirmed by the human at T2.05 transcription time (D-01 says so explicitly)** — treat it as a strong candidate, not a locked fact, for the ADR-008 draft.

3. **Calendar** — `holidays==0.100` is what's actually installed in this environment (pinned `>=0.50` in `pyproject.toml`); its `Austria` subdivisions are the digits `'1'..'9'`, and `'6'` is confirmed to be Steiermark (Styria) — **no deviation from CONTEXT's `subdiv='6'`, no ADR needed** (SG-10 resolves via test assertion only, as the WBS anticipated). The forward-horizon computation (SG-15/D-08) is architecturally simple (`latest_complete_month() + 18 months`) but has one design decision the CONTEXT leaves implicit: **where does "18 months" live?** It is derived conceptually from `strategies.yaml`'s `forward.horizon_months: 12` + a 6-month cushion, but `calendar.py` (M2) importing `epra.common.config.StrategyCfg`/`load_strategy_config()` (an M6 concept) would be a milestone-boundary violation. Recommendation: hardcode `_FORWARD_HORIZON_MONTHS = 18` as a `calendar.py`-local constant with a comment citing SG-15/D-08 and the `12 + 6` derivation — do not import M6 config into M2 code.

**Primary recommendation:** Build all three modules functional-core/imperative-shell exactly like M1 (pure parse/gate functions, thin `main()`), reuse `_io`/`timeutil`/`validate.py`'s `GateResult`/`ValidationReport` framework unmodified except for the one additive `_io.write_month()` extension GeoSphere needs, resolve ÖSPI's methodology choice provisionally toward the "old-method" continuous series pending human confirmation at T2.05, and hardcode the calendar's 18-month horizon rather than importing M6 config.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| GeoSphere daily temperature fetch + parse | Backend / Ingestion (`src/epra/ingest/geosphere.py`) | External API (GeoSphere Data Hub, no auth) | Backend owns discovery, politeness, parsing to the §7 contract; GeoSphere is a passive public data source, not a service EPRA calls back into |
| GeoSphere station discovery + ADR | Backend / Ingestion (one-off `discover_station()`) | Governance (ADR-007) | Discovery result is persisted as config + documented decision, not re-run per ingest call |
| ÖSPI manual transcription | Human / Governance (`data/manual/oespi_monthly*.csv`) | Backend / Ingestion (`oespi.py` loader + gates) | No machine API exists (A-2 no-invented-data forces human transcription); backend only validates, never fetches or "fixes" |
| ÖSPI reconciliation | Tooling (`scripts/oespi_reconcile.py`, already implemented) | — | One-shot diff utility, not part of the ingest runtime path |
| Calendar/holiday hourly spine | Backend / Ingestion (`src/epra/ingest/calendar.py`) | Common (`epra.common.timeutil`, `holidays` package) | Pure function of (config, end date); timeutil owns the peak-hour/DST logic so calendar.py never re-derives TZ math |
| Post-ingest data-quality gates (ING-094/101/103/111) | Backend / Ingestion (`src/epra/ingest/validate.py`) | Reporting (`reports/ingestion/validation_*.md`) | Gate framework lives in the ingestion layer per M1 precedent; markdown report is a thin rendering concern, not a separate tier |
| Raw persistence (parquet / CSV) | Storage (`data/raw/`, `data/manual/`) | Backend (`_io.py` writer) | Single shared writer enforces ING-003/004/005 across every ingestor; storage layout is dictated by SPEC-01 §7, not per-module choice |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | `>=2.32` (already pinned, M1) | HTTP transport for GeoSphere (no-auth GET) | Already the project's sanctioned HTTP client (ING-006/007); GeoSphere needs no new client — reuse the same retry/politeness pattern `_fetch.py` established for ENTSO-E, generalized or duplicated at small scope |
| `tenacity` | `>=8.3` (already pinned, M1) | Retry/backoff for GeoSphere requests (ING-006 applies to "every source") | Same retry policy (429/5xx/connection errors, exponential backoff, 6 attempts) as ENTSO-E — no new library needed |
| `holidays` | `>=0.50` pinned; **`0.100` confirmed installed in this environment** `[VERIFIED: local venv `python -c "import holidays; print(holidays.__version__)"` this session]` | Austrian/Styrian public holiday calendar (ING-110) | Already a runtime dependency; `Austria` locale with `subdiv='6'` gives Steiermark-specific holidays including regional ones (e.g., certain saints' days observed only in some Bundesländer) |
| `pandas` / `pyarrow` | `>=2.2,<3` / `>=18,<26` (already pinned, M1, ADR-004) | Frame construction + parquet I/O | Already the project's sanctioned data/IO stack; GeoSphere/calendar reuse `_io.write_month()` (with the extension below) rather than a second writer |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `csv` | n/a | ÖSPI CSV parsing pattern already shown in `scripts/oespi_reconcile.py` | `oespi.py`'s `load_oespi()` should use `pandas.read_csv` for the gate-checked frame (dtype control), but the reconcile script's stdlib-`csv` pattern is a useful reference for strict column-order validation |
| stdlib `json` (via `requests.Response.json()`) | n/a | GeoSphere GeoJSON response parsing | GeoSphere responses are GeoJSON per SPEC-01 §9 (`output_format=geojson`); no extra JSON library needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Generalizing `_fetch.py`'s ENTSO-E-specific transport for GeoSphere | A small GeoSphere-specific `_fetch`-shaped function (own retry/cache wrapper, same policy constants) | `_fetch.fetch_entsoe()` is typed around `EntsoeQuery`/`EntsoeRawClient` — forcing GeoSphere through it would require an abstraction neither WBS nor MODULES.md asks for. A parallel, small, ING-006/007/009-compliant function in `geosphere.py` (or a tiny shared `_http.py` helper if duplication feels excessive) is lower-risk and matches "whichever lands first owns `_io`"-style pragmatism already established in M1 |
| Manual CSV transcription for ÖSPI | Scraping the AEA page or PDF programmatically | Explicitly rejected by spec (ING-100: "no machine API ⇒ hand-curated CSV") and by D-03 (human transcribes, not agent) — A-2 (no invented data) makes any programmatic PDF-scrape-and-trust approach a correctness risk the spec deliberately avoids |
| Hardcoded 18-month calendar horizon constant | Import `StrategyCfg.forward.horizon_months` from `load_strategy_config()` into `calendar.py` | Coupling M2's calendar module to M6's strategy config is an architecture layering violation (M2 merges *before* M1 in the WBS's stated order, and long before M6); a local documented constant avoids a forward-reference import chain for a value that's static in practice |

**Installation:** No new packages required — GeoSphere/ÖSPI/Calendar all reuse dependencies already pinned in `pyproject.toml` from M1 (`requests`, `tenacity`, `holidays`, `pandas`, `pyarrow`). If a plan step still needs to run installs (e.g., first `uv sync` in a fresh worktree):

```bash
uv pip install -e ".[dev]"
```

**Version verification:** `holidays` version and subdivision behavior verified directly against the installed interpreter this session:
```
$ python -c "import holidays; print(holidays.__version__); print(sorted(holidays.Austria.subdivisions))"
holidays 0.100
['1', '2', '3', '4', '5', '6', '7', '8', '9']
```
`'6'` corresponds to Steiermark (Styria) — confirmed both by this direct package introspection and by cross-checking against public holiday-code references (`holidayapi.com/countries/at-6`) `[CITED: holidayapi.com/countries/at-6]`. **No ADR needed for SG-10** — the working code matches CONTEXT's expected `'6'` exactly.

## Package Legitimacy Audit

**No new external packages are introduced by this phase.** GeoSphere, ÖSPI, and Calendar ingestion all reuse dependencies already vetted and pinned during M1 (`requests`, `tenacity`, `holidays`, `pandas`, `pyarrow`, stdlib `csv`/`json`). The Package Legitimacy Gate is not applicable — no `npm view`/`pip index versions` verification is required for packages the codebase already depends on and has running in CI.

**Packages removed due to [SLOP] verdict:** none (no new packages).
**Packages flagged as suspicious [SUS]:** none (no new packages).

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │   GeoSphere Data Hub API     │  (public, no auth)
                    │ dataset.api.hub.geosphere.at │
                    └──────────────┬───────────────┘
                                   │ GET /station/historical/klima-v2-1d
                                   │      + /…/metadata   (geojson)
                                   ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  src/epra/ingest/geosphere.py                                 │
   │  discover_station() → StationInfo (id/name/lat/lon)           │
   │  ingest(start, end) → per-month GeoJSON fetch → parse_geojson │
   └───────────────────────────┬─────────────────────────────────--┘
                                │ frame: date, station_id, tl_mittel_c, parameter_raw
                                ▼
   ┌────────────────────────────────────────────────────────────┐
   │  src/epra/ingest/_io.py  write_month() [EXTENDED this phase]│
   │  atomic monthly parquet write + ING-004 provenance columns  │
   └───────────────────────────┬──────────────────────────────--─┘
                                ▼
                data/raw/geosphere_graz_daily/<YYYY>/…parquet


   ┌──────────────────────────────┐        ┌──────────────────────────────┐
   │  AEA strompreisindex page    │ human  │  data/manual/                │
   │  (energyagency.at) — PDF/XLS │───────►│  oespi_monthly_entry{1,2}.csv │
   │  no machine API               │reads,  │  → scripts/oespi_reconcile.py│
   │  transcribes                  │ types  │  → oespi_monthly.csv         │
   └──────────────────────────────┘        └───────────────┬──────────────┘
                                                             ▼
                                        ┌─────────────────────────────────┐
                                        │ src/epra/ingest/oespi.py         │
                                        │ load_oespi() → gate-checked      │
                                        │ month-indexed Base/Peak frame    │
                                        └─────────────────┬────────────────┘
                                                           │
                                                           ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │  src/epra/ingest/calendar.py                                       │
   │  build_calendar(end=latest_complete_month()+18mo) → hourly spine   │
   │  calls epra.common.timeutil.is_peak_hour / to_local / to_utc       │
   │  calls holidays.Austria(subdiv='6')                                │
   └───────────────────────────┬──────────────────────────────────────-┘
                                ▼
                data/raw/calendar/calendar.parquet


   ┌───────────────────────────────────────────────────────────────────┐
   │  src/epra/ingest/validate.py  (extended, not replaced, this phase) │
   │  + gate_ing_094 (GeoSphere)  + gate_ing_101/103 (ÖSPI)             │
   │  + gate_ing_111 (Calendar, if wired into run_gates)                │
   │  ValidationReport.render_markdown() → reports/ingestion/…md        │
   └───────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new top-level directories — this phase fills in existing stubs and adds fixtures:

```
src/epra/ingest/
├── geosphere.py      # discover_station, parse_geojson, ingest, main — implement
├── oespi.py          # load_oespi, main — implement
├── calendar.py       # build_calendar, main — implement
├── validate.py       # add gate_ing_094, gate_ing_101/103 (+ 111 if wired here)
└── _io.py            # EXTEND write_month/_validate_ts_utc for date-keyed datasets

tests/
├── fixtures/
│   ├── geosphere/            # NEW: metadata.json + one month of tl_mittel geojson
│   └── oespi/                # NEW: synthetic oespi_monthly.csv covering every ING-103 fail case
├── test_raw_contracts.py     # ADD a geosphere_graz_daily row to _CONTRACTS
└── unit/
    ├── test_geosphere.py     # NEW
    ├── test_oespi.py         # NEW
    └── test_calendar.py      # NEW

data/manual/
└── oespi_monthly.csv         # committed once T2.05 (human) completes

docs/ADR/
├── ADR-007_geosphere-station-selection.md   # NEW
└── ADR-008_oespi-series-methodology.md      # NEW
```

### Pattern 1: Extend the shared writer for date-keyed (non-hourly) raw datasets

**What:** `_io.write_month()` currently hard-requires a tz-aware UTC `ts_utc` column (`_validate_ts_utc` raises `ContractError` if absent). GeoSphere's §7 contract is `date, station_id, tl_mittel_c, parameter_raw` — a plain `date`, not `ts_utc`. Rather than bending GeoSphere's contract to add a `ts_utc` column it doesn't specify (which would fail the exact-column-list contract test the same way M1's did), extend `_io` with a small, additive, backward-compatible parameterization.

**When to use:** Any future daily/date-grain raw dataset that reuses the shared writer (this is the first one M2 introduces; keep the extension generic, not GeoSphere-specific naming).

**Example (illustrative, not literal code to copy verbatim — validate signature during planning):**
```python
# epra/ingest/_io.py — additive change, ENTSO-E callers unaffected (default unchanged)
def write_month(
    frame: pd.DataFrame,
    dataset: str,
    month: date,
    request_hash: str,
    settings: Settings,
    *,
    key_column: str = "ts_utc",   # NEW — existing callers get identical behavior
) -> Path:
    _validate_write_key(frame, dataset, month, key_column)
    ...

def _validate_write_key(frame, dataset, month, key_column) -> None:
    if key_column not in frame.columns:
        raise ContractError(dataset, expected=f"column '{key_column}'", actual=f"columns={list(frame.columns)}")
    if key_column == "ts_utc":
        _validate_ts_utc_dtype_and_bounds(frame, dataset, month)   # existing logic, renamed
    else:
        _validate_date_dtype_and_bounds(frame, dataset, month, key_column)  # NEW: plain date, same month-bounds check, no tz assertions
```
`geosphere.py` then calls `write_month(frame, "geosphere_graz_daily", month, req_hash, settings, key_column="date")`. This preserves ING-003 (atomic monthly overwrite), ING-004 (provenance columns unchanged), and the exact §7 column list — no ADR needed, since it's an internal engineering interface addition, not a spec deviation (the SPEC-01 §7 *output* contract is untouched).

### Pattern 2: GeoSphere discovery-then-ingest, ADR-gated

**What:** `discover_station()` is a one-time (or rarely re-run) call whose *result* is written to config + an ADR — it is not re-executed on every ingest run.
**When to use:** Any external source whose "which resource id do I even use" answer needs to be pinned once and documented (ING-091 pattern also matches T2.02's dataset-id-verification fallback: "if `klima-v2-1d` does not exist, list `/datasets`... ADR the substitution").
**Example:**
```python
# Source: SPEC-01 §9 ING-091 + docs/EXECUTION_BLUEPRINT/03_MODULES.md geosphere section
@dataclass(frozen=True)
class StationInfo:
    id: str
    name: str
    lat: float
    lon: float
    record_start: date

def discover_station(settings: Settings) -> StationInfo:
    """ING-091: fetch metadata, pick Graz station with longest record,
    prefer 'Graz Universität' on ties. Deterministic given the metadata response."""
    resp = requests.get(f"{settings.geosphere.base_url}/station/historical/"
                         f"{settings.geosphere.dataset_id}/metadata", timeout=30)
    resp.raise_for_status()
    stations = resp.json()  # geojson FeatureCollection per GeoSphere docs
    candidates = [s for s in stations["features"] if "Graz" in s["properties"]["name"]]
    if not candidates:
        raise DiscoveryError(...)  # names available stations, feeds the ADR
    # longest record, tie-break "Graz Universität"
    ...
```

### Pattern 3: Pure gate functions extending the shared `GateResult`/`ValidationReport` framework

**What:** M1 already established the exact shape M2's gates must follow — `validate.py`'s `GateResult`/`ValidationReport` classes, `gate_ing_0XX(frame) -> GateResult` pure functions (no I/O, no mutation), each with ≥1 passing + ≥1 failing synthetic test case, aggregated via `ValidationReport.add()`, rendered to `reports/ingestion/validation_<date>.md`, raised via `raise_if_failed()`.
**When to use:** ING-094 (GeoSphere), ING-101/103 (ÖSPI), and ING-111 (Calendar, if the plan chooses to route it through `validate.py` rather than only as inline `pytest` assertions — MODULES.md lists ING-111 as calendar's own "Testing" contract, not necessarily a `validate.py` gate; **planner should decide** whether calendar checks belong in `run_gates()`'s aggregate report or remain pytest-only, since SPEC-01 §11 doesn't literally list ING-111 under "§8 validation gates run after every ingest").
**Example — mirrors the exact style already in the codebase (`validate.py` `gate_ing_082`):**
```python
# Source: src/epra/ingest/validate.py (existing M1 pattern to extend, not replace)
def gate_ing_094(geosphere_daily: pd.DataFrame) -> GateResult:
    """ING-094: coverage >=99%; -30<=tl_mittel<=42; Jul mean in [15,30]; Jan mean in [-10,8]."""
    if geosphere_daily.empty:
        return GateResult("ING-094", False, "no GeoSphere data supplied to ING-094", None)
    # ... coverage / range / seasonal-mean checks, evidence frame, GateResult(...)
```

### Anti-Patterns to Avoid
- **Re-implementing `is_peak_hour` or any TZ conversion inside `calendar.py`:** `epra.common.timeutil` is the *only* sanctioned TZ layer (T-1, D-10 explicit). Calling `to_local`/`to_utc`/`is_peak_hour` directly, never re-deriving DST logic.
- **Importing M6's `StrategyCfg`/`load_strategy_config()` into `calendar.py`** to source the forward horizon. Keep the 18-month constant local to `calendar.py` with a comment citing SG-15/D-08 (see Common Pitfalls).
- **Bending the GeoSphere §7 contract to add a `ts_utc` column** just to satisfy the existing writer's hardcoded validation. Extend `_io` instead (Pattern 1).
- **Treating the ÖSPI "Indices 2.0" (Dec-2023-onward) series as usable for 2019→present.** It categorically cannot cover that window; splicing it onto the older series is the exact mistake ING-102 warns against.
- **Widening any ING-08x/09x/10x/11x plausibility band to make a gate pass.** A-2/EN-061 — a failing gate is a signal to investigate the pipeline, never to loosen the threshold without an ADR (same discipline ADR-006 documented for M1).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic monthly parquet writes | A second writer inside `geosphere.py` | Extended `_io.write_month()` (Pattern 1) | ING-003 idempotency/atomicity logic (temp-file + `os.replace`, per-process-unique temp names guarding concurrent writers) is already correct and tested in M1; duplicating it risks reintroducing the WR-02 race the M1 code review already fixed |
| Public-holiday calendars | A hardcoded Austrian/Styrian holiday date table | `holidays.Austria(subdiv='6', years=...)` | The `holidays` package already encodes regional variation (e.g., a holiday observed in some Bundesländer but not others) and handles year-to-year date shifts (Easter-relative holidays); hand-rolling this is a guaranteed source of subtle date bugs as the calendar horizon extends into future years |
| DST-correct hour counting | Manual UTC-offset arithmetic in `calendar.py` | `epra.common.timeutil.local_hours_in_day()` / `to_local()` | Already built and DST-tested in M1 specifically because naive `datetime` subtraction across a DST boundary silently returns 24h when the true count is 23/25 — the exact bug class T-1 exists to prevent |
| CSV double-entry reconciliation | A new diff script in `oespi.py` | `scripts/oespi_reconcile.py` (already implemented, ING-101) | Already implements the exact procedure (entry1/entry2 diff, mismatch listing, reconciled-file output) the spec requires; `oespi.py`'s `load_oespi()` only needs to *load and gate-check* the already-reconciled file, never re-reconcile |
| Gate result aggregation / markdown report rendering | A second report format or ad-hoc pass/fail printing in each new gate module | `validate.py`'s `GateResult`/`ValidationReport` classes | Consistency across ING-08x (M1) and ING-09x/10x/11x (M2) in one report file is exactly what `ValidationReport`'s "list every registered gate exactly once, no silent skips" invariant guarantees |

**Key insight:** every one of M2's three sources is "simple" only because M1 already paid the hard engineering cost (atomic writes, TZ correctness, retry/politeness, gate-framework rendering) — the risk in this phase is re-solving already-solved problems slightly differently per module, which would fragment the codebase's single-writer/single-TZ-layer/single-gate-framework guarantees M1 built specifically to avoid that. The one genuinely new engineering problem (date-keyed vs. ts_utc-keyed writes) should be solved once, generically, in `_io.py` — not per-module.

## Common Pitfalls

### Pitfall 1: `_io.write_month()` rejects GeoSphere's date-keyed frame out of the box
**What goes wrong:** `geosphere.py`'s `ingest()` calls the existing `write_month()` with a frame that has `date` (not `ts_utc`) and it raises `ContractError` immediately (`_validate_ts_utc` checks `"ts_utc" not in frame.columns`).
**Why it happens:** The §7 contract for `geosphere_graz_daily` is genuinely different grain (daily `date`) from every M1 dataset (hourly/sub-hourly `ts_utc`); the writer was built before M2 existed and encodes an implicit "every raw dataset has `ts_utc`" assumption that SPEC-01 §7 itself does not actually make.
**How to avoid:** Plan an explicit small `_io.py` extension task (Pattern 1) before or alongside T2.03 — do not discover this mid-implementation as a surprise. Keep the change additive (default parameter preserves M1 behavior byte-for-byte; existing M1 tests must not need any changes).
**Warning signs:** A GeoSphere unit test that mocks `write_month` and passes only because the mock doesn't validate columns — always test against the *real* `write_month`/`_validate_*` path so this surfaces immediately, not after a live pull.

### Pitfall 2: Splicing the two ÖSPI methodologies
**What goes wrong:** Transcribing early years (2019–2023) from the "old method" page and later months (Dec 2023+) from the new "Indices 2.0" monthly-total-base-peak-off-peak family produces a series with a level/definitional discontinuity exactly at the 2022-crisis-adjacent boundary — which would corrupt the ING-103 "2022 peak ≥ 3× 2019 mean" crisis-visibility gate in a way that's hard to detect after the fact (both halves individually look plausible).
**Why it happens:** Both series are published simultaneously by the same organization on adjacent pages; someone transcribing "whatever is current" each month without checking which methodology page they're on would drift between them.
**How to avoid:** ADR-008 pins ONE page/series explicitly (`https://www.energyagency.at/fakten/strompreisindex`, the continuously-published series, per this research's finding that it already carries Base+Peak since Sept 2018) as the sole transcription source for 2019→latest; the T2.05 human checkpoint transcribes only from that one page/PDF for the entire window.
**Warning signs:** A `source_url` column (already part of ING-100's schema) that changes mid-series — this should itself be asserted constant (or explicitly justified) as part of `load_oespi()`'s sanity checks, even though ING-103 doesn't explicitly list it as a gate.

### Pitfall 3: Calendar horizon coupling to M6 config
**What goes wrong:** Importing `load_strategy_config()`/`StrategyCfg` into `calendar.py` to read `forward.horizon_months` creates an import dependency from M2 (merges first) onto M6 config concepts, and worse, silently changes calendar's forward window if someone tunes `strategies.yaml` for an unrelated M6 reason later — an implicit cross-milestone coupling nobody will expect when debugging a calendar-range issue.
**Why it happens:** SG-15's rationale text literally mentions "12-month forward-risk sim... 6-month cushion," making the derivation look like it should be "read from config."
**How to avoid:** Hardcode `_FORWARD_HORIZON_MONTHS = 18` in `calendar.py` with a comment citing SG-15/D-08 and the 12+6 rationale. If the forward horizon ever needs to become genuinely configurable, that's a deliberate future ADR, not an implicit import in M2.
**Warning signs:** Any circular- or forward-import lint/mypy warning between `epra.ingest.calendar` and `epra.common.config`'s M6-specific classes.

### Pitfall 4: `holidays.Austria(subdiv='6', years=...)` needs a dynamic year range, not a fixed list
**What goes wrong:** Hardcoding `years=range(2019, 2028)` (or similar) means the calendar silently stops updating holiday flags correctly once `latest_complete_month() + 18mo` pushes past the hardcoded upper bound in some future run.
**Why it happens:** SG-15/D-08's whole point is that the calendar's end date is dynamic; the holiday library's year set must track that dynamism, not be pinned once at write-time.
**How to avoid:** Derive `years=range(2019, end.year + 1)` (or equivalent) from the same `end` value `build_calendar()` computes, every run — never a module-level constant list.
**Warning signs:** ING-111 test passing today but silently wrong in production a few years from now if the year range was hand-typed instead of derived from `end`.

### Pitfall 5: GeoSphere response parsing — GeoJSON nesting, not a flat table
**What goes wrong:** Treating the `/station/historical/klima-v2-1d` response as a flat CSV-like table when it's actually GeoJSON (per SPEC-01 §9's own `output_format=geojson` parameter and confirmed by the official docs site being a "Dataset API" with a GeoJSON-oriented resource model) — a naive `pd.DataFrame(response.json())` will likely produce a malformed or empty frame.
**Why it happens:** GeoSphere's API returns a `FeatureCollection`-shaped payload (or a parameters/timestamps nested structure per station) rather than row-per-record JSON; the exact nesting must be inspected against a real response, which this research could not fully enumerate (see Open Questions).
**How to avoid:** Treat the first successful `discover_station()` + one-month `ingest()` live call (D-07) as the moment to lock down `parse_geojson()`'s exact field paths, then immediately freeze that response as the committed fixture (`tests/fixtures/geosphere/`) so CI never depends on re-parsing this correctly from memory.
**Warning signs:** `parse_geojson()` returning silently empty/zero-row frames instead of raising — MODULES.md's contract explicitly says "missing days absent, never filled (A-2)," but an empty *frame* due to a parsing miss looks identical to "no data available" unless the parser distinguishes "0 rows because I mis-parsed the shape" from "0 rows because GeoSphere really has no data for this window."

### Pitfall 6: ING-080-style false-missing-hours does NOT apply to daily GeoSphere data the same way, but coverage arithmetic still needs the right denominator
**What goes wrong:** ING-094's "coverage ≥ 99% of days" needs to be computed against the number of calendar days in the requested window, not against a fixed 8760/8784-hours-style constant copied from the ENTSO-E gates.
**Why it happens:** Pattern-matching on `gate_ing_080`'s style (which the plan should otherwise follow closely) without noticing the denominator changes from "hours in a year" to "days in the ingested window."
**How to avoid:** `gate_ing_094`'s coverage check should compute `expected_days = (window_end - window_start).days + 1` (or similar, scoped like ADR-006's boundary-year handling if GeoSphere's window doesn't align to calendar years) rather than reusing an hours-based constant.
**Warning signs:** A coverage gate that always reports ~100% regardless of actual gaps because the denominator is wrong (too large) or that fails spuriously on a correctly-complete short test window (denominator too small).

## Code Examples

### Verified: `holidays` package Austria/Styria subdivision (installed-package introspection, this session)
```python
# Verified directly against the environment's installed package this session:
import holidays
print(holidays.__version__)                    # 0.100
print(sorted(holidays.Austria.subdivisions))    # ['1', '2', '3', '4', '5', '6', '7', '8', '9']
at_styria = holidays.Austria(subdiv="6", years=range(2019, 2029))
# '6' == Steiermark (Styria) -- matches CONTEXT D-10 exactly; no ADR needed.
```

### Existing pattern to mirror: `_io.write_month`'s atomicity (already built, M1)
```python
# Source: src/epra/ingest/_io.py (existing, read this session — do not reimplement)
tmp_path = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
out.to_parquet(tmp_path, index=False, engine="pyarrow")
os.replace(tmp_path, path)
```

### Existing pattern to mirror: `latest_complete_month()` — the M1 function `calendar.py` must wire as its dynamic `--end` default (D-09)
```python
# Source: src/epra/ingest/entsoe.py (existing, ADR-005) -- calendar.py imports and calls this,
# does not reimplement "what is the latest complete month" logic.
def latest_complete_month(settings: Settings) -> date:
    """Returns min(latest complete AT-prices month, latest complete DE-LU-prices month)."""
    ...
```

### GeoSphere endpoint shape (CITED, not exhaustively verified against a live response this session)
```
Base URL:      https://dataset.api.hub.geosphere.at/v1
Dataset id:    klima-v2-1d                          (confirmed real dataset on the Data Hub)
Data endpoint: GET /station/historical/klima-v2-1d?parameters=tl_mittel&station_ids=<ID>
                   &start=<YYYY-MM-DD>&end=<YYYY-MM-DD>&output_format=geojson
Metadata:      GET /station/historical/klima-v2-1d/metadata
Dataset list:  GET /datasets                          (fallback if klima-v2-1d is renamed/missing)
Auth:          none required for publicly accessible data (CC-BY 4.0)
```
`[CITED: dataset.api.hub.geosphere.at/v1/docs, github.com/Geosphere-Austria/dataset-api-docs]` — the base URL, dataset existence, no-auth requirement, and endpoint *pattern* are confirmed against the official docs site and its GitHub-hosted documentation source; the **exact JSON/GeoJSON field nesting of a real response body** was not independently fetched and parsed this session (see Open Questions) — SPEC-01 §9/ING-091 already anticipates this ("verify at build time") and Pitfall 5 above covers the mitigation.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| ÖSPI single overall monthly index only | AEA now also publishes a separate "Indices 2.0" family (12 indices: monthly/quarterly/yearly × total/base/peak/off-peak) alongside the original series | December 2023 | Do not use the new family for 2019→present (doesn't cover that window); the original series remains the correct, continuously-published source for this project's full window — confirmed via direct page fetch this session |

**Deprecated/outdated:** none directly affecting this phase's build — the "old method" ÖSPI page is, confusingly, still the *actively maintained* series for this project's purposes (its "old" label is relative to the newer supplementary indices, not an indication it stopped being published).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The AEA "old method" ÖSPI series (`energyagency.at/fakten/strompreisindex`) covers 2019→present as one consistent series with both Base and Peak available throughout — resolving D-01/D-02 toward Base+Peak, no fallback needed | Summary, Pitfall 2, State of the Art | If Peak was actually discontinuous somewhere in 2019–2023 (e.g., a mid-window sub-methodology tweak this research didn't surface), `oespi.py`/ADR-008 would need the ING-104 base-only fallback after all — **D-01 already requires human confirmation at T2.05 regardless**, so this is a bounded risk, not a silent one |
| A2 | GeoSphere's `/station/historical/klima-v2-1d` response is GeoJSON with a nested per-station/per-parameter structure (not a flat table) | Pitfall 5, Code Examples | If the real response shape differs from expectation, `parse_geojson()`'s first implementation attempt may need a quick rewrite once the live/fixture response is actually inspected (D-07 already schedules this as the first concrete task) |
| A3 | Extending `_io.write_month()` with a `key_column` parameter (Pattern 1) is the correct resolution to the date-vs-ts_utc mismatch, rather than (e.g.) a wholly separate `geosphere_io.py` writer | Architecture Pattern 1, Pitfall 1 | If the planner/reviewer prefers a separate writer to avoid touching M1's already-shipped `_io.py`, ING-003's atomicity guarantee would need to be re-verified independently for the new writer — more code, same guarantee, higher duplication risk |
| A4 | ING-111 belongs to calendar's own pytest suite rather than `validate.py`'s aggregate gate framework (SPEC-01 §11's ING-111 is phrased as "Test:", not "Gate:") | Architecture Pattern 3 | If the planner decides ING-111 should also appear in the `reports/ingestion/validation_*.md` aggregate report (for a single-glance M2 exit-gate view), a small `gate_ing_111` wrapper around the same pytest assertions would need to be added to `validate.py` — low effort either way, but should be a deliberate planning choice, not an oversight |

## Open Questions

1. **Exact GeoSphere GeoJSON response field paths for `tl_mittel` and station metadata**
   - What we know: base URL, dataset id, endpoint pattern, no-auth, GeoJSON output format — all confirmed against official docs this session.
   - What's unclear: the precise nested structure (e.g., is it `features[].properties.parameters.tl_mittel.data[]` keyed by timestamp, or a `timestamps[]` + `parameters.tl_mittel.data[]` parallel-array structure — GeoSphere's docs site organizes this under an "Endpoints"/OpenAPI page this research did not fetch).
   - Recommendation: D-07 already schedules a live discovery + one-month pull in-phase; treat that as the authoritative source for `parse_geojson()`'s exact implementation, and commit the raw response as the test fixture immediately (avoids re-deriving this from memory later).

2. **Whether the AEA "old method" series is truly gap-free and Base+Peak-complete for all of 2019–present, or has any silent sub-period quirk**
   - What we know: methodology has been stable enough to include both Base and Peak since a September 2018 refinement; the page is still actively published (most recent value fetched was for a 2026 month).
   - What's unclear: month-by-month completeness cannot be confirmed without the human actually transcribing the full series (which is D-05's committed human checkpoint, by design).
   - Recommendation: draft ADR-008 provisionally pointing at this series per this research, explicitly flagged "pending T2.05 human confirmation" per D-01/D-04 — do not treat as locked until transcription happens.

3. **Should ING-111 (Calendar) be wired into `validate.py`'s `ValidationReport`, or stay pytest-only?**
   - What we know: SPEC-01 §11 phrases it as a "Test," unlike §8/§9/§10's "Gate" language; MODULES.md's calendar section lists it under "Testing," not alongside `gate_ing_0XX` naming.
   - What's unclear: whether the M2 exit criteria ("ING-094/101/103/111 gates pass") in the phase's own Success Criteria implies all four should render in the same validation report, or whether "gates" there loosely includes calendar's pytest assertions.
   - Recommendation: given the phase's Success Criteria explicitly lists ING-111 alongside the other three "gates," lean toward adding a thin `gate_ing_111` wrapper into `validate.py` for report-uniformity — low cost, resolves the ambiguity in favor of the more observable/aggregatable option (see Assumption A4).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `holidays` package | Calendar (ING-110/111) | ✓ (verified this session) | 0.100 (pinned `>=0.50`) | — |
| GeoSphere Data Hub API (network) | GeoSphere live discovery/ingest (D-07) | Not verified in this research session (no outbound call attempted) | — | Committed GeoJSON fixture (D-07 explicit fallback) — CI never depends on live network regardless (D-06) |
| AEA `energyagency.at` publication pages (network) | ÖSPI source verification / human transcription (T2.04/T2.05) | ✓ — fetched successfully this session via WebFetch | — | N/A — this is a one-time human-read source, not a runtime dependency |
| `uv` / Python 3.12 toolchain | All M2 modules | ✓ (existing M1 environment, unchanged) | per `pyproject.toml` (`requires-python = ">=3.12,<3.13"`) | — |

**Missing dependencies with no fallback:** none — every M2 dependency either already verified working, or has an explicit committed-fixture fallback per D-06/D-07.
**Missing dependencies with fallback:** GeoSphere live network reachability from the execution agent's environment was not tested this research session — if blocked at implementation time, D-07's fixture fallback applies directly (already a locked decision, not a new finding).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest>=8` (already configured, M1) with `pytest.mark.live` for network-touching tests (excluded in CI via `-m "not live"`, EN-070) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (markers section already declares `live`) |
| Quick run command | `uv run pytest tests/unit/test_geosphere.py tests/unit/test_oespi.py tests/unit/test_calendar.py -m "not live"` |
| Full suite command | `uv run pytest -m "not live"` (CI) / `uv run pytest` (includes live, local/human checkpoint only) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ING-090..092 | Station discovery picks the right Graz station from a crafted multi-station metadata fixture | unit | `pytest tests/unit/test_geosphere.py::test_discover_station_prefers_graz_universitaet -x` | ❌ Wave 0 |
| ING-093 | GeoSphere ingest respects politeness sleep + cache 7-day rule (mirrors `_fetch` tests) | unit | `pytest tests/unit/test_geosphere.py::test_ingest_respects_cache_and_politeness -x` | ❌ Wave 0 |
| ING-094 | Coverage/range/seasonal-mean gate — 1 passing + 1 failing synthetic case each | unit | `pytest tests/unit/test_ingest_gates.py::test_gate_ing_094* -x` | ❌ Wave 0 |
| ING-070 (extended) | `geosphere_graz_daily` fixture row added to raw-contract test | contract | `pytest tests/test_raw_contracts.py -k geosphere -x` | ❌ Wave 0 (row to add; file exists) |
| ING-100/101 | `load_oespi()` rejects schema drift; reconcile script already covered (`test_scripts.py`) | unit | `pytest tests/unit/test_oespi.py::test_load_oespi_schema_drift_raises -x` | ❌ Wave 0 |
| ING-102/104 | Base-only fallback path (`peak_available=False`) exercised even if the real series turns out Base+Peak-complete | unit | `pytest tests/unit/test_oespi.py::test_load_oespi_base_only_fallback -x` | ❌ Wave 0 |
| ING-103 | Continuity, positivity, crisis-visibility (2022≥3×2019), MoM≤±60% — every gate's fail case on a committed synthetic CSV (D-05) | unit | `pytest tests/unit/test_ingest_gates.py::test_gate_ing_103* -x` | ❌ Wave 0 |
| ING-110 | Hourly spine correctness, DST 23/25 rows, dynamic `--end` from `latest_complete_month()+18mo` | unit | `pytest tests/unit/test_calendar.py::test_build_calendar_dst_rows -x` | ❌ Wave 0 |
| ING-111 | 2024 holiday count, Jan1/May1/Dec25 always holidays, peak-hour Monday/Sunday check, SG-10 subdiv assertion | unit | `pytest tests/unit/test_calendar.py::test_ing_111* -x` | ❌ Wave 0 |
| REQ-ING-01 (M2 slice) | Full validation suite green for 2019→latest on real GeoSphere pull + reconciled ÖSPI CSV | manual/live (human checkpoint, D-06/D-07) | `uv run python -m epra.ingest.validate` (after real data committed) | N/A — human checkpoint by design |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_<module>.py -m "not live"` (fast, module-scoped)
- **Per wave merge:** `uv run pytest -m "not live"` (full fixture/synthetic suite, network-free)
- **Phase gate:** Full suite green in CI (network-free) per D-06; separately, `make validate-ingest` green on real data is a committed human/local checkpoint, not a CI blocker

### Wave 0 Gaps
- [ ] `tests/fixtures/geosphere/metadata.json` — crafted multi-station GeoSphere metadata fixture (Graz Universität + at least one decoy station) for `discover_station()`'s tie-break test
- [ ] `tests/fixtures/geosphere/klima_2019-01.geojson` (or similar) — one committed month of real or realistic-shaped daily `tl_mittel` GeoJSON for `parse_geojson()`/ING-094 tests
- [ ] `tests/fixtures/oespi/synthetic_oespi_monthly.csv` — synthetic series covering every ING-103 fail case (gap in months, negative value, 2022 peak <3× 2019 mean, a >60% MoM jump) per D-05
- [ ] `tests/unit/test_geosphere.py`, `tests/unit/test_oespi.py`, `tests/unit/test_calendar.py` — new test files (none exist yet)
- [ ] `_CONTRACTS["geosphere_graz_daily"]` row added to `tests/test_raw_contracts.py`
- [ ] Rows removed from `tests/unit/test_stubs_fail_loudly.py`'s `STUBS` list for every M2 function as each is implemented (geosphere/oespi/calendar's 7 listed stub-rows)

*(Framework itself needs no install — `pytest>=8` + the `live` marker already exist from M1.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | GeoSphere requires no auth (ING-093); no user-facing auth surface in this phase |
| V3 Session Management | No | Not applicable — batch ingestion CLI, no sessions |
| V4 Access Control | No | Not applicable — single-operator local/CI pipeline |
| V5 Input Validation | Yes | Pydantic `Settings`/config models (existing, `epra.common.config`) + `_DATASET_NAME_RE` allowlist regex in `_io.py` (already mitigates path traversal via a crafted `dataset` string, T-02-03) + `oespi_reconcile.py`'s strict `EXPECTED_COLUMNS` check (schema drift raises `SystemExit`, not silent acceptance) |
| V6 Cryptography | No | No secrets/crypto in this phase (GeoSphere has no auth token; ÖSPI is a public CSV) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Path traversal via a crafted `dataset` string reaching `raw_month_path()` | Tampering | Already mitigated by `_io._DATASET_NAME_RE` (`^[a-z][a-z0-9_]*$`) — `geosphere_graz_daily` matches this pattern; no new module should bypass `raw_month_path()`/`write_month()` with a hand-built path |
| Malformed/oversized GeoSphere response causing a parser crash or resource exhaustion | Denial of Service | `parse_geojson()` should validate expected top-level shape before indexing deeply nested keys, and the HTTP call should carry a sane timeout (mirrors `_fetch.py`'s pattern even though GeoSphere needs its own small transport) |
| CSV injection / malformed rows in `data/manual/oespi_monthly*.csv` (human-edited file) | Tampering | `oespi_reconcile.py`'s exact-column-match check (already implemented) + `load_oespi()`'s dtype/gate validation catch malformed rows before they reach downstream analytics; never "auto-fix" a bad row (P-3, no silent data correction) |
| Leaking any future GeoSphere API key in logs (not currently applicable — no auth) | Information Disclosure | Not applicable today (no auth token exists for GeoSphere); if GeoSphere ever requires a key, apply the exact same A-7 discipline `_fetch.py`/`entsoe_token()` already established (env-var only, never logged) |

## Sources

### Primary (HIGH confidence)
- `docs/SPEC-01_data_ingestion.md` (this repo) — §1 general rules, §7 output contracts, §9 GeoSphere, §10 ÖSPI, §11 Calendar — read in full this session
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M2 (T2.01–T2.06) — read in full this session
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` — geosphere/oespi/calendar/validate module contracts — read in full this session
- `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` — SG-10, SG-14, SG-15 — read in full this session
- `docs/ADR/ADR-006_validation-gate-scope-local-year.md` — read in full this session (precedent pattern for gate scoping/boundary-year handling)
- Existing source: `src/epra/ingest/_io.py`, `_fetch.py`, `validate.py`, `exceptions.py`, `entsoe.py` (`latest_complete_month`), `src/epra/common/timeutil.py`, `src/epra/common/config.py`, `config/settings.yaml`, `config/strategies.yaml`, `scripts/oespi_reconcile.py`, `tests/test_raw_contracts.py`, `tests/unit/test_stubs_fail_loudly.py`, `tests/conftest.py`, `Makefile`, `pyproject.toml` — all read directly this session
- `holidays` package — version and Austria subdivision list confirmed by direct `python -c "import holidays; ..."` introspection against this project's installed environment this session

### Secondary (MEDIUM confidence)
- `https://www.energyagency.at/fakten/strompreisindex` — fetched directly this session (WebFetch); confirmed "old method" label, Sept-2018 Base+Peak methodology refinement, PDF/Excel-only downloads (no CSV/API), page still actively published (most recent value was for a 2026 month)
- `https://www.energyagency.at/fakten/strompreisindizes` — fetched directly this session; confirmed the newer "Indices 2.0" family (12 indices) launched December 2023 as a supplement
- `https://dataset.api.hub.geosphere.at/v1/docs/` and `.../user-guide/resource.html` — fetched/searched this session; confirmed base URL, `klima-v2-1d` dataset existence, no-auth public access, `/station/historical/<id>` + `/metadata` endpoint pattern, `/datasets` listing fallback

### Tertiary (LOW confidence)
- `holidayapi.com/countries/at-6` — cross-referenced via WebSearch only (not independently fetched) to corroborate the Austria subdivision code list; superseded in confidence by the direct package introspection above, which is the authoritative source
- Exact GeoSphere GeoJSON response field-nesting (station/parameter/timestamp structure) — WebSearch/WebFetch this session did not surface the literal OpenAPI schema; flagged in Open Questions, mitigated by D-07's live-discovery-first approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all reused from an already-shipped, working M1 dependency set, version-confirmed against the actual installed environment
- Architecture: HIGH — patterns directly extend the already-built and code-reviewed M1 `_io`/`validate.py`/`timeutil` framework; the one novel architectural decision (Pattern 1, date-keyed writer extension) is grounded in a concrete, verified code conflict (read both `_io.py` and SPEC-01 §7 directly), not speculation
- Pitfalls: HIGH for the internal ones (writer conflict, config coupling, holiday year-range) — directly derived from reading the actual code and spec; MEDIUM for GeoSphere response-shape specifics (Pitfall 5) since the literal response body was not fetched this session
- ÖSPI methodology resolution (D-01/D-02 candidate answer): MEDIUM — grounded in direct official-page fetches this session, but explicitly still pending the human T2.05 confirmation the CONTEXT itself requires before being locked

**Research date:** 2026-07-22
**Valid until:** 30 days for the internal/code-based findings (stable — M1 code won't drift on its own); GeoSphere/ÖSPI external-source specifics should be re-verified at T2.02/T2.04 implementation time if this phase is picked up materially later than 30 days from now, since both are live external publications that can change format without notice
