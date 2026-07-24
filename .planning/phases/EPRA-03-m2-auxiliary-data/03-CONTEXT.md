# Phase 3: M2 Auxiliary Data - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning
**Mode:** Interactive discuss — spec-supremacy project (SPEC-01 §§9–11 lock *what* to build); this discussion captures the operational/data-supply decisions the spec explicitly leaves open (ING-102/104 series choice, live-vs-fixture boundary, transcription ownership, SG-15 calendar horizon).

<domain>
## Phase Boundary

Ingest the three non-ENTSO-E sources and complete the ingestion layer (REQ-ING-01). One milestone, one PR — merges **first** in the M2→M1 order (R-1).

- **GeoSphere** (SPEC-01 §9) — daily mean air temperature (`tl_mittel`, °C) for the Graz station, 2019→latest, into monthly parquet `data/raw/geosphere_graz_daily/<YYYY>/…` per the §7 contract. No auth. Gates ING-094.
- **ÖSPI** (SPEC-01 §10) — hand-curated monthly index (Base + Peak, base 2006=100) in the committed CSV `data/manual/oespi_monthly.csv`, double-entry reconciled. No machine API. Gates ING-103; reconcile via `scripts/oespi_reconcile.py` (ING-101).
- **Calendar** (SPEC-01 §11) — hourly UTC spine 2019-01-01 → forward-window end, with local attributes, Styrian holidays, and peak flags, into `data/raw/calendar/calendar.parquet`. Gates ING-111.

**Out of this phase:** ENTSO-E ingestion (M1, complete); dbt staging/marts + canonical hourly aggregation (M3/Phase 4); load-profile calibration (M4); anything downstream of `data/raw/`.

</domain>

<decisions>
## Implementation Decisions

### ÖSPI series & methodology (SPEC-01 §10 · ING-102/104)
- **D-01:** Use the **current-method** AEA ÖSPI series if it covers 2019→present as one consistent series; fall back to the long-running/legacy series **only** if current-method coverage is insufficient. **Never splice two methods.** Final pick is confirmed against the actual publication at transcription time and recorded in the methodology ADR.
- **D-02:** Target **Base + Peak**. If monthly Peak values are not published for part of 2019→latest, drop to **Base-only** (`peak_available: false`, SPEC-05 base-only behavior per ING-104) and record it in the ADR **and** `LIMITATIONS.md`.

### ÖSPI acquisition & double-entry (SPEC-01 §10 · ING-101, T2.04/T2.05)
- **D-03:** The **human (operator) transcribes both entry1 and entry2 in separate sessions** — the spec's literal double-entry procedure (most robust against a bad source read; A-2 no-invented-data). Not agent-transcribed.
- **D-04:** The AEA *strompreisindex* source is **not located yet** — locating the current publication is part of this checkpoint. The agent **finds/verifies the source URL and drafts the methodology ADR (series + source URLs) first (T2.04)**; the human confirms the source, then transcribes (T2.05).
- **D-05:** `load_oespi()` + the ING-103 gate set (continuity, positivity, 2022 peak ≥ 3× 2019 mean, MoM ≤ ±60%) are **built and unit-tested against a committed synthetic CSV** covering every gate's fail case. The **real reconciled `oespi_monthly.csv` is a committed human checkpoint**, not a blocker for shipping the loader/gates.

### Real-data boundary & phase close (reprises M1 ADR-006 / EN-070)
- **D-06:** M2 closes on **code + fixture/synthetic gates green in CI** (network-free). Live GeoSphere pull + the reconciled real ÖSPI CSV land as **committed human/local checkpoints** with a validation report under `reports/ingestion/`. Do not gate CI on live network or real ÖSPI transcription.
- **D-07:** **GeoSphere (no auth, ING-093):** attempt `discover_station()` (ING-091) **live in-phase** and, if reachable, a real pull to get ING-094 green on real data now. If the agent env blocks outbound network, **fall back to a committed GeoJSON fixture** for parse/gate tests and mark the live pull as a human checkpoint. Either way, ship the parser + ING-094 gates against a fixture so CI is deterministic.

### Calendar forward horizon (SPEC-01 §11 · SG-15)
- **D-08:** Forward-window end = **`latest_complete_month() + 18 months`**, recomputed each run (18 = the 12-month forward-risk sim per REQ-Q3 + a 6-month cushion for later convention shifts).
- **D-09:** **Compute the default `--end` dynamically from M1** (M1 is complete, so wire `epra.ingest.entsoe.latest_complete_month()` as the default). A fixed `--end` is used **only in tests** for determinism (e.g., `--end 2027-12-31`). The SG-15 "pre-M1 `--end` bootstrap" is moot since M1 exists.
- **D-10:** `is_peak_hour` comes from `epra.common.timeutil` — **never re-implemented** in `calendar.py`. Holidays via the `holidays` package, `subdiv='6'` for Styria (SG-10); the ING-111 test asserts the **working** subdiv code, and an ADR is written **only if** the working code deviates from `'6'`.

### Claude's Discretion
- **ADR numbering:** the WBS labels the new ADRs "ADR-003" (GeoSphere station) and "ADR-004" (ÖSPI methodology), but those numbers are already used (ADR-003 = entsoe-raw-client, ADR-004 = pyarrow). The GeoSphere-station ADR and ÖSPI-methodology ADR must take the **next free numbers: ADR-007 (GeoSphere station) and ADR-008 (ÖSPI methodology)**. Confirm against `docs/ADR/` at planning time.
- Internal module decomposition, helper naming, fixture byte content, synthetic-CSV values, and validation-report layout are the implementer's choice within the SPEC-01 contracts and REQ-ID docstrings (W-2), consistent with M1.
- GeoSphere station tie-break beyond "Graz, longest record, prefer *Graz Universität*" (ING-091) is resolved at discovery time and recorded in the station ADR.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Binding spec (authority)
- `docs/SPEC-01_data_ingestion.md` §§9–11 — GeoSphere (ING-090..094), ÖSPI (ING-100..104), Calendar (ING-110..111); §1 general rules (ING-001..010); §7 output contracts.
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M2 — tasks T2.01 (calendar), T2.02 (GeoSphere discovery+ADR), T2.03 (GeoSphere ingest+gates), T2.04 (ÖSPI loader+gates+ADR), T2.05 (ÖSPI human double transcription), T2.06 (M2 PR assembly).
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` — module contracts for `geosphere.py`, `oespi.py`, `calendar.py`, `validate.py`.

### Spec-gap proposals adopted here (need ADRs at planning/exec)
- `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` — SG-10 (`subdiv='6'`), SG-14 (holiday-aware peak, aligns with ING-110/LP-020), SG-15 (dynamic calendar end = latest_complete_month + horizon).
- `.planning/INGEST-CONFLICTS.md` — SG-10/14/15 disposition (all INFO/WARNING, no blockers); ADR-on-adoption guidance.

### Precedent / patterns to reuse
- `docs/ADR/ADR-006_validation-gate-scope-local-year.md` — gates scoped to complete Vienna-local years; the real-data boundary (D-06) reprises this + EN-070 (live isolated behind `@pytest.mark.live`, CI runs `-m "not live"`).
- `docs/ADR/ADR-004_pyarrow-parquet-engine.md`, `docs/ADR/ADR-003_entsoe-raw-client-sg01.md`, `docs/ADR/ADR-005_latest-complete-month-sg02.md` — M1 ADRs; note ADR-003/004 numbers are **taken** (see Claude's Discretion).
- `.planning/phases/EPRA-02-m1-entso-e-ingestion/02-CONTEXT.md` — M1 decisions carried forward (functional core/imperative shell, REQ-ID docstrings, atomic monthly writes, live-vs-fixture pattern).

### Reporting / downstream consumers (context, not modified here)
- `docs/SPEC-02_data_model.md` §4 — `dim_calendar` consumes the calendar parquet (season, hdd_18, cdd_22 join happen in M3).
- `docs/SPEC-05_strategy_simulator.md` — consumes ÖSPI (Base/Peak, `peak_available` behavior for ING-104).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/epra/ingest/_io.py` — atomic monthly-parquet writer built in M1; **GeoSphere reuses it** (§7 contract, `os.replace` temp-file pattern). Whichever of GeoSphere/ENTSO-E landed first owns `_io`; it exists.
- `src/epra/ingest/validate.py` — the ING-080..085 gate framework + report writer from M1. **Add ING-094 (GeoSphere) and ING-103 (ÖSPI) gate classes to the shared framework**; keep gate functions pure (no I/O) with a thin report writer to `reports/ingestion/validation_*.md`.
- `src/epra/common/timeutil.py` — `is_peak_hour(ts_local, *, is_holiday=False)` **already exists** (line 39); `to_utc`, `to_local`, `local_hours_in_day` (DST-tested). Only sanctioned TZ layer (T-1). Calendar must call these, not re-implement.
- `scripts/oespi_reconcile.py` — **already implemented**; the double-entry reconcile step (ING-101) uses it as-is.
- `config/settings.yaml` — `geosphere:` block present with `base_url`, `dataset_id: klima-v2-1d`, `parameter: tl_mittel`; `station_id`/`station_name` are `null` and get filled by ING-091 discovery. `window.start_date: 2019-01-01`. `ingest.geosphere_sleep_s: 0.2`, `cache_min_age_days: 7`.
- `holidays>=0.50` — already a runtime dep (`pyproject.toml`).

### Established Patterns
- Functional core / imperative shell: pure parsers + pure gate functions; I/O confined to fetch/`_io`/thin `main()`.
- CLI entrypoints `python -m epra.ingest.<source> --start … --end …` wired to Makefile (ING-002).
- Public functions cite REQ IDs in docstrings (`Implements: ING-094`) per W-2.
- Live network isolated behind `@pytest.mark.live`; CI runs `-m "not live"` (EN-070) — the real-data boundary (D-06/D-07) rides on this.
- Raw contract tests: `tests/test_raw_contracts.py` enumerates all §7 datasets and fails on drift — **add a `geosphere_graz_daily` row** (T1.03 AC coordinates with T2.03).

### Integration Points
- Stubs to implement: `src/epra/ingest/geosphere.py` (`discover_station`, `ingest`, `main`), `oespi.py` (`load_oespi`, `main`), `calendar.py` (`build_calendar`, `main`) — all currently raise `NotImplementedError`.
- Makefile targets for the auxiliary sources + `validate-ingest` extend the M1 wiring.
- `tests/test_stubs_fail_loudly.py` — remove the M2 rows as each stub is implemented.
- New fixtures under `tests/fixtures/` — GeoJSON excerpt (GeoSphere) and synthetic ÖSPI CSV (all-gate-fail-case coverage).

</code_context>

<specifics>
## Specific Ideas

- ÖSPI source is the Austrian Energy Agency *strompreisindex* publication (`https://www.energyagency.at/fakten/strompreisindex`, historically a PDF of monthly Base/Peak values, base 2006=100). No machine API — hand-curated CSV only. The agent locates/verifies the current publication URL before the human transcribes.
- GeoSphere target dataset `klima-v2-1d`, endpoint `/station/historical/klima-v2-1d`, discovery via `/station/historical/klima-v2-1d/metadata` (verify dataset id at build time; ADR the substitution if it differs).
- WBS AC uses `python -m epra.ingest.calendar --end 2027-12-31` as the fixed-`--end` test example.

</specifics>

<deferred>
## Deferred Ideas

- `dim_calendar` weather join (season, `hdd_18`, `cdd_22`) → M3/Phase 4 (SPEC-02 §4). Calendar here only produces the ING-110 spine.
- Canonical hourly aggregation of prices/load/generation → M3/Phase 4 (dbt staging). M2 does no aggregation.
- Consumer `peak_available`-dependent strategy formulas → M6/Phase 7 (SPEC-05). M2 only sets the `peak_available` flag on the ÖSPI data.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-M2 Auxiliary Data*
*Context gathered: 2026-07-22*
