---
phase: EPRA-03-m2-auxiliary-data
verified: 2026-07-23T18:39:58Z
status: passed
resolved: 2026-07-23T21:00:00Z  # sole human_needed item (ÖSPI double-entry) reconciled this session — see Post-Verification Resolution
score: 22/22 must-haves verified (21/22 at initial verify; ÖSPI resolved post-verify)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Perform real ÖSPI double-entry transcription and reconciliation: transcribe the AEA strompreisindex monthly series (Base+Peak) twice into data/manual/oespi_monthly_entry1.csv and oespi_monthly_entry2.csv (already present, unreconciled), then run `uv run python scripts/oespi_reconcile.py` until it exits 0 and writes data/manual/oespi_monthly.csv, then delete the two entry files, then re-run `make validate-ingest` and confirm ING-103 shows a real-data PASS (not the current informational soft-pass)."
    expected: "data/manual/oespi_monthly.csv exists, is double-entry reconciled, and gate_ing_103 evaluates real continuity/positivity/crisis-visibility/MoM checks against it (all passing)."
    why_human: "Double-entry transcription from a PDF/web publication is explicitly a human-only operation (D-03); an agent must not fabricate or auto-approve the second transcription, per every plan's prohibitions (03-05, 03-06) and LIMITATIONS.md §6."
---

# Phase 3: M2 Auxiliary Data Verification Report

**Phase Goal:** All non-ENTSO-E sources ingested and ingestion layer complete
**Verified:** 2026-07-23T18:39:58Z
**Status:** passed (initial verify returned human_needed; sole human item resolved same day — see Post-Verification Resolution)
**Re-verification:** No — initial verification

> **Post-Verification Resolution (2026-07-23):** The single outstanding human_needed item — real ÖSPI double-entry reconciliation — was completed by the user this session. The two independent transcriptions were verified identical (`entry1 == entry2`) and reconciled via `uv run python scripts/oespi_reconcile.py` (exit 0, 92 months 2019-01→2026-08) into `data/manual/oespi_monthly.csv` (committed `9ab8999`). `make validate-ingest` re-run → **exit 0, ING-103 substantive real-data PASS** ("continuity/positivity/crisis-visibility/MoM checks all pass" — no longer the informational soft-pass), all 9 gates PASS. This upgrades truths **1c, 2b (real-data half), 2c, 2e** from NOT-MET/soft-pass to **VERIFIED on real data**, and closes truth 3's caveat. All 9/9 ROADMAP sub-truths now met; REQ-ING-01 fully satisfied.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1a | GeoSphere daily temperature is present and gate-clean | ✓ VERIFIED | 60 monthly parquet files under `data/raw/geosphere_graz_daily/2019..2023/`; `gate_ing_094` independently re-run → PASS (coverage 1.0000, 1826/1826 days; range/July/January all in-band) |
| 1b | Calendar parquet is present and gate-clean | ✓ VERIFIED | `data/raw/calendar/calendar.parquet` present (762,074 bytes, 78,888 rows per SUMMARY); `gate_ing_111` independently re-run → PASS (holiday_count_2024=13, fixed holidays present, Mon/Sun peak-hour correct) |
| 1c | Reconciled ÖSPI CSV is present and gate-clean | ✗ NOT MET (human-pending) | `data/manual/oespi_monthly.csv` does **not exist**. Only `oespi_monthly_entry1.csv`/`entry2.csv` (unreconciled, human-transcribed) exist. `gate_ing_103` shows an **informational soft-pass** ("real ÖSPI data not yet transcribed ... not a gate failure"), not a real-data pass. Documented as a design-sanctioned deferral (D-06) in LIMITATIONS.md §6 and deferred-items.md — not a code defect. Routed to Human Verification below. |
| 2a | ING-094 gate passes | ✓ VERIFIED | Independently re-ran `uv run python -m epra.ingest.validate` → `gate=ING-094 passed=True` |
| 2b | ING-101 (double-entry reconciliation tooling) passes | ✓ VERIFIED (tooling only) | `scripts/oespi_reconcile.py` exists, implements the diff-and-write workflow; `tests/unit/test_scripts.py` (5 tests: accepts-matching-entries, rejects-mismatch, requires-both-entries, token-guard) all pass. The *tool* is correct and tested; it has not yet been *run* against real transcriptions (see 1c). |
| 2c | ING-103 gate passes | ✓ VERIFIED (soft-pass by design) | Independently re-ran → `gate=ING-103 passed=True`, but on the informational/absent-data path, not a real-series pass. `gate_ing_103`'s four sub-checks (continuity/positivity/crisis-visibility/MoM) are implemented and unit-tested against a synthetic CSV (`tests/unit/test_ingest_gates.py`, 6 ING-103 cases pass) but have not evaluated real transcribed data yet. |
| 2d | ING-111 gate passes | ✓ VERIFIED | Independently re-ran → `gate=ING-111 passed=True` |
| 2e | data/manual/oespi_monthly.csv is double-entry reconciled | ✗ NOT MET (human-pending) | Same gap as 1c — file absent. |
| 3 | Full ingestion validation suite passes for 2019→latest complete month | ✓ VERIFIED (with caveat) | Independently re-ran `uv run python -m epra.ingest.validate` → exit code 0, all 9 gates (ING-080..085, ING-094, ING-103, ING-111) report `passed=True`, report regenerated at `reports/ingestion/validation_2026-07-23.md` matching the committed one byte-for-byte (`git status` shows no diff). Caveat: ING-103's PASS is the informational soft-pass (2c), not a real-data validation — the suite is green by design (D-06), not because real ÖSPI data was validated. |

**Score:** 6/9 roadmap-criteria sub-truths fully verified as literally worded; the 3 unmet sub-truths (1c, 2b's real-data half, 2e) all reduce to the single outstanding item: the real double-entry ÖSPI reconciliation, which is explicitly a human-only, design-sanctioned deferral (D-03/D-06), not a code gap.

### Plan-Level Must-Haves (all 6 plans, must_haves.truths)

| Plan | Truth | Status | Evidence |
|------|-------|--------|----------|
| 03-01 | `write_month` accepts additive `key_column="ts_utc"` kwarg; ENTSO-E callers unchanged | ✓ VERIFIED | `src/epra/ingest/_io.py:196-203` — keyword-only `key_column: str = "ts_utc"`; `entsoe.py` call sites unmodified (confirmed no `key_column` references in entsoe.py) |
| 03-01 | `write_month(..., key_column="date")` accepts plain date-keyed frame, enforces month bounds | ✓ VERIFIED | `_validate_date_key()` at `_io.py:162-193`, no tz assertion, shares `_month_bounds()` |
| 03-01 | Missing key column → ContractError; out-of-month → ValueError (both modes) | ✓ VERIFIED | `_io.py:132-137` (ts_utc), `:175-180` (date) raise `ContractError`; both `_validate_*` raise `ValueError` on out-of-month rows |
| 03-01 | ING-004 provenance + ING-003 atomic write unchanged for both key modes | ✓ VERIFIED | `_io.py:243-259` — single provenance-append/`os.replace` tail shared by both branches |
| 03-02 | `build_calendar` returns ING-110 spine 2019→forward-window end with exact columns | ✓ VERIFIED | `calendar.py` 100% test coverage; `data/raw/calendar/calendar.parquet` exists with 9 columns |
| 03-02 | DST spring/fall days have 23/25 rows via timeutil | ✓ VERIFIED | `tests/unit/test_calendar.py::test_build_calendar_dst_rows` passes (full suite green) |
| 03-02 | `is_peak_hour` sourced from `epra.common.timeutil`, not re-implemented | ✓ VERIFIED | `grep -n "is_peak_hour" src/epra/ingest/calendar.py` shows only import/call, no local re-def |
| 03-02 | Styrian holidays via `holidays.Austria(subdiv='6', ...)`; 2024 count + fixed holidays correct | ✓ VERIFIED | `gate_ing_111` independently re-run → holiday_count_2024=13 match, Jan1/May1/Dec25 all True |
| 03-02 | Calendar persists as single file, not via `_io.write_month` | ✓ VERIFIED | `data/raw/calendar/calendar.parquet` is one file (not a monthly-partitioned tree) |
| 03-03 | `discover_station` picks Graz station with longest record, prefers "Graz Universität" | ✓ VERIFIED | `geosphere.py` `discover_station`/`StationInfo`; live-discovered station id "30" recorded in `config/settings.yaml` and `docs/ADR/ADR-007_geosphere-station-selection.md` (file exists) |
| 03-03 | Discovery is live-first with fixture fallback | ✓ VERIFIED | `tests/fixtures/geosphere/metadata.json` exists with "Graz Universität" + decoy; live discovery succeeded per 03-03 SUMMARY and ADR-007 |
| 03-04 | `parse_geojson` → §7 columns (date, station_id, tl_mittel_c, parameter_raw) | ✓ VERIFIED | `tests/test_raw_contracts.py -k geosphere` passes (own-columns assertion); `_GEOSPHERE_COLUMNS` in `validate.py` matches |
| 03-04 | `ingest` writes via `write_month(..., key_column="date")` into date-keyed monthly parquet | ✓ VERIFIED | `data/raw/geosphere_graz_daily/<YYYY>/*.parquet` — 60 files present 2019-2023 |
| 03-04 | `gate_ing_094` checks coverage/range/seasonal-mean with days-in-window denominator | ✓ VERIFIED | `validate.py:498-572`; independently re-run, PASS with `1826/1826 days` denominator (not hours) |
| 03-04 | Raw-contract test recognizes geosphere as date-keyed, zone-less | ✓ VERIFIED | `tests/test_raw_contracts.py -k geosphere` passes |
| 03-05 | `load_oespi` loads + validates ING-100 schema, month-indexed, raises on drift | ✓ VERIFIED | `src/epra/ingest/oespi.py`; `tests/unit/test_oespi.py` (schema-drift, malformed-value tests pass in full suite) |
| 03-05 | `load_oespi` asserts constant `source_url`; ING-104 base-only fallback | ✓ VERIFIED | Source asserts nunique via `oespi.py`; `test_load_oespi_source_url_splice_raises`/`test_load_oespi_base_only_fallback` pass |
| 03-05 | `gate_ing_103` checks continuity/positivity/2022-crisis-3x/MoM-60% with fail cases | ✓ VERIFIED | `validate.py:575-675`; `tests/unit/test_ingest_gates.py` 6 ING-103 cases (1 pass + 5 fail-case tests) all pass |
| 03-05 | Synthetic CSV exercises every ING-103 fail case | ✓ VERIFIED | `tests/fixtures/oespi/synthetic_oespi_monthly.csv` (60-row clean series); fail cases derived via in-test mutation per SUMMARY |
| 03-05 | ADR-008 pins ONE AEA series, pending human confirmation | ✓ VERIFIED | `docs/ADR/ADR-008_oespi-series-methodology.md` exists; per 03-06 SUMMARY the human confirmed the pick against the live publication |
| 03-06 | `run_gates` loads GeoSphere/ÖSPI/calendar and runs ING-094/103/111 alongside ING-080..085, each exactly once | ✓ VERIFIED | `validate.py:920-929` — all 9 `report.add(...)` calls, one per gate id, confirmed by grep (no duplicates) |
| 03-06 | `gate_ing_111` is a thin wrapper over `build_calendar` producing a `GateResult` | ✓ VERIFIED | `validate.py:678-755` |
| 03-06 | `make validate-ingest` produces `reports/ingestion/validation_<date>.md`, exits non-zero on any failure | ✓ VERIFIED | Independently re-ran `uv run python -m epra.ingest.validate` → exit 0, report regenerated identical to committed `reports/ingestion/validation_2026-07-23.md` |
| 03-06 | Real reconciled ÖSPI CSV + live GeoSphere pull land as human/local checkpoints, not CI blockers | ⚠️ PARTIALLY MET | Live GeoSphere pull **completed** (60 real monthly parquet files, station 30, 2019-01→2023-12). Real ÖSPI double-entry reconciliation **not completed** — this is the one open item, correctly treated as a human checkpoint (not a CI blocker) per D-06, and correctly NOT auto-approved by the executor (D-03 respected). |

**Score:** 21/22 plan-level must-have truths fully verified; 1 partially met (the ÖSPI human checkpoint, by design not yet executed).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/epra/ingest/_io.py` | `key_column` dispatcher | ✓ VERIFIED | Exists, substantive, wired (imported by geosphere.py, entsoe.py) |
| `src/epra/ingest/calendar.py` | `build_calendar`/`main` | ✓ VERIFIED | 100% test coverage, no stub markers |
| `src/epra/ingest/geosphere.py` | `discover_station`/`parse_geojson`/`ingest`/`main` | ✓ VERIFIED | 94% coverage; no `NotImplementedError` remaining |
| `src/epra/ingest/oespi.py` | `load_oespi`/`main` | ✓ VERIFIED | 73% coverage (lower — some `main()` CLI branches untested per plan's own noted convention of manual-only main() testing); no stub markers |
| `src/epra/ingest/validate.py` | `gate_ing_094`/`gate_ing_103`/`gate_ing_111`/`run_gates` extension | ✓ VERIFIED | 95% coverage; all 9 gates registered exactly once |
| `data/raw/calendar/calendar.parquet` | single-file calendar output | ✓ VERIFIED | Present on disk |
| `data/raw/geosphere_graz_daily/**/*.parquet` | monthly date-keyed GeoSphere parquet | ✓ VERIFIED | 60 files present, 2019-01→2023-12 |
| `data/manual/oespi_monthly.csv` | reconciled double-entry ÖSPI CSV | ✗ MISSING | Absent — human checkpoint pending (see Human Verification) |
| `docs/ADR/ADR-007_geosphere-station-selection.md` | station discovery ADR | ✓ VERIFIED | Exists |
| `docs/ADR/ADR-008_oespi-series-methodology.md` | ÖSPI series methodology ADR | ✓ VERIFIED | Exists, confirmed by human per 03-06 SUMMARY |
| `reports/ingestion/validation_2026-07-23.md` | aggregate validation report | ✓ VERIFIED | Exists, committed (commit `9ded31e`), independently reproduced byte-identical |
| `scripts/oespi_reconcile.py` | ING-101 double-entry reconciliation tool | ✓ VERIFIED | Exists, tested (5 passing tests in `tests/unit/test_scripts.py`), not yet run against real transcriptions |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `geosphere.ingest` | `_io.write_month` | `key_column="date"` | ✓ WIRED | `geosphere.py` calls `write_month(..., key_column="date")` per 03-04 grep acceptance criterion; 60 real parquet files prove it executed |
| `entsoe.ingest_dataset` | `_io.write_month` | default (no `key_column`) | ✓ WIRED | Zero edits to `entsoe.py`; M1 suites (`test_entsoe_orchestration.py`, `test_ingest_gates.py`, `test_raw_contracts.py`) all green |
| `calendar.py` | `epra.ingest.entsoe.latest_complete_month` | dynamic default `--end` | ✓ WIRED | `_default_end()` imports and calls it (per SUMMARY; `NoDataError` degrade path present in `validate.py::_load_calendar`) |
| `validate.run_gates` | `oespi.load_oespi` | `_oespi_gate_result()` guarded call | ✓ WIRED | `validate.py:854-884` — deferred import (avoids circular import), catches `FileNotFoundError`, degrades to informational PASS |
| `validate.run_gates` | `gate_ing_094`/`gate_ing_103`/`gate_ing_111` | `report.add(...)` | ✓ WIRED | All three registered in `run_gates`, confirmed via independent re-run producing matching report |
| `oespi_reconcile.py` | `data/manual/oespi_monthly.csv` | double-entry diff | ⚠️ NOT YET EXECUTED | Tool exists and is tested, but has not been run against `entry1.csv`/`entry2.csv` to produce the reconciled output (human checkpoint pending) |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|--------------|--------|----------|
| REQ-ING-01 | 03-01 through 03-06 (all) | ENTSO-E + GeoSphere + ÖSPI (double-entry) + calendar ingested with validation gates green for 2019→latest | ⚠️ OPEN (recommend staying open) | GeoSphere/calendar/ENTSO-E ingestion is complete and gate-clean. ÖSPI ingestion tooling (loader + gate) is complete and unit-tested, but the REQUIREMENT explicitly names "ÖSPI manual CSV (double-entry)" as ingested — that half is not yet done on real data. `.planning/REQUIREMENTS.md` traceability table already lists REQ-ING-01 as "Pending" and unchecked (`- [ ]`); this verification confirms that status is still accurate and should NOT be flipped to complete until `data/manual/oespi_monthly.csv` is reconciled. |
| ING-003/004/005/070 | 03-01 | Writer contract extension | ✓ SATISFIED | Verified above |
| ING-090/091/092 | 03-03 | GeoSphere station discovery | ✓ SATISFIED | Verified above |
| ING-093/094 | 03-04 | GeoSphere ingest + gate | ✓ SATISFIED | Verified above (real data present, gate green) |
| ING-100/102/104 | 03-05 | ÖSPI loader, schema, single-series, base-only fallback | ✓ SATISFIED (tooling) | Loader logic verified against synthetic data; real-data application pending human checkpoint |
| ING-101 | 03-05/03-06 (tooling), human checkpoint (outcome) | ÖSPI double-entry reconciliation | ⚠️ PARTIAL | Tool built + tested; outcome (reconciled file) not yet produced |
| ING-103 | 03-05/03-06 | ÖSPI series gates | ✓ SATISFIED (tooling); ⚠️ soft-pass on real data | Gate logic fully tested against synthetic fail cases; real-data run is an informational soft-pass by design, not a substantive pass |
| ING-110/111 | 03-02/03-06 | Calendar spine + gate | ✓ SATISFIED | Verified above |

No orphaned requirements found — `.planning/REQUIREMENTS.md` maps REQ-ING-01 to Phase 3 only, and all 6 plans declare it.

### Anti-Patterns Found

None. Scanned `_io.py`, `calendar.py`, `geosphere.py`, `oespi.py`, `validate.py` for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and stray `NotImplementedError` — zero matches. `tests/unit/test_stubs_fail_loudly.py`'s `STUBS` list no longer references any M2 (`cal.*`, `geosphere.*`, `oespi.*`) function — only M4/M5/M6/M7 stubs remain, which is correct (future milestones, out of this phase's scope).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full deterministic suite passes | `uv run pytest -m "not live" -q` | All green, 94.89% coverage (matches SUMMARY's claimed ~94.9%) | ✓ PASS |
| Lint clean | `uv run ruff check src tests scripts` | All checks passed | ✓ PASS |
| Type-check clean | `uv run mypy` | Success: no issues found in 30 source files | ✓ PASS |
| Aggregate validation gate suite | `uv run python -m epra.ingest.validate` | Exit code 0; all 9 gates `passed=True`; report byte-identical to committed one (`git status` shows no diff) | ✓ PASS |
| ING-101 reconciliation tool correctness | `uv run pytest tests/unit/test_scripts.py -m "not live" -q --no-cov` | 5 passed | ✓ PASS |
| Raw-contract drift guard (GeoSphere) | `uv run pytest tests/test_raw_contracts.py -k geosphere -m "not live" -q --no-cov` | Passed | ✓ PASS |

### Human Verification Required

### 1. Real ÖSPI double-entry transcription and reconciliation

**Test:** Transcribe the AEA strompreisindex monthly series (Base + Peak) into `data/manual/oespi_monthly_entry1.csv` and `oespi_monthly_entry2.csv` (already present locally, per plan 03-06's human checkpoint, but not yet reconciled), then run `uv run python scripts/oespi_reconcile.py` until it exits 0 and writes `data/manual/oespi_monthly.csv`. Delete the two entry files. Re-run `make validate-ingest`.

**Expected:** `data/manual/oespi_monthly.csv` exists; `gate_ing_103` evaluates the real series (continuity/positivity/2022-crisis-visibility/MoM-stability) and passes substantively (not the current informational soft-pass); `reports/ingestion/validation_<date>.md` shows a genuine ING-103 PASS with an evidence table (mirroring ING-094/111's evidence-table format), not the "not yet transcribed" message.

**Why human:** Double-entry transcription from a published PDF/web source is explicitly a human-only operation (D-03) — every plan in this phase (03-05, 03-06) states an agent must never auto-approve or fabricate the second transcription. This is by design, not an oversight; the code and tests supporting it are complete and verified above.

## Gaps Summary

No code-level gaps were found. All artifacts, key links, and plan-level must-haves across all 6 plans (03-01 through 03-06) are verified present, substantive, and wired — independently confirmed by re-running the deterministic test suite (green, 94.89% coverage), ruff/mypy (clean), and the live `make validate-ingest` equivalent (`python -m epra.ingest.validate`, exit 0, all 9 gates pass, report reproduced byte-identical to the committed one).

The phase's ingestion **layer** — the code, gates, ADRs, and validation-report assembly — is complete and correctly built to the SPEC-01 contracts (§9 GeoSphere, §10 ÖSPI, §11 Calendar), reusing the shared `_io.write_month` writer and `validate.py` `GateResult` framework exactly as the RESEARCH/plans intended, with zero anti-patterns or debt markers.

One substantive item is outstanding and is NOT a code defect: the real, double-entry-reconciled `data/manual/oespi_monthly.csv` does not exist yet. Two of the three ROADMAP success criteria (1 and 2) explicitly name the *reconciled ÖSPI CSV* as a condition, and REQ-ING-01 explicitly names "ÖSPI manual CSV (double-entry)" as part of what must be ingested. Per this phase's own design (D-03: double-entry transcription is human-only; D-06: it is a human/local checkpoint, never a CI/agent blocker), this is correctly deferred rather than fabricated — the executor built and unit-tested the loader/gate against a synthetic CSV, drafted ADR-008, and stopped exactly where it should. This verification treats it as a human-verification item, not a gap requiring a closure plan.

**Recommendation:** Keep `REQ-ING-01` OPEN (unchecked) in `.planning/REQUIREMENTS.md` — consistent with its current "Pending" traceability entry — until a human completes the double-entry ÖSPI transcription and reconciliation and `make validate-ingest` shows a substantive (non-informational) ING-103 PASS on real data. At that point, a lightweight re-verification (re-run `make validate-ingest` and confirm ING-103's evidence table is populated) is sufficient to close REQ-ING-01; no further code changes are anticipated.

---

*Verified: 2026-07-23T18:39:58Z*
*Verifier: Claude (gsd-verifier)*
