---
phase: 3
slug: m2-auxiliary-data
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-22
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `03-RESEARCH.md` §Validation Architecture. Per-task rows are finalized by validate-phase once PLAN.md task IDs exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest>=8` (already configured, M1) with `@pytest.mark.live` for network-touching tests |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`live` marker already declared) |
| **Quick run command** | `uv run pytest tests/unit/test_geosphere.py tests/unit/test_oespi.py tests/unit/test_calendar.py -m "not live"` |
| **Full suite command** | `uv run pytest -m "not live"` (CI, network-free) · `uv run pytest` (includes live — local/human checkpoint only) |
| **Estimated runtime** | ~15 seconds (network-free unit + fixture suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/test_<module>.py -m "not live"` (fast, module-scoped)
- **After every plan wave:** Run `uv run pytest -m "not live"` (full fixture/synthetic suite, network-free)
- **Before `/gsd-verify-work`:** Full suite must be green in CI (network-free) per D-06
- **Max feedback latency:** ~15 seconds

*Separately, `make validate-ingest` green on real GeoSphere pull + reconciled ÖSPI CSV is a committed human/local checkpoint (D-06/D-07), NOT a CI blocker.*

---

## Per-Task Verification Map

| Req ID | Behavior | Wave | Test Type | Automated Command | File Exists | Status |
|--------|----------|------|-----------|-------------------|-------------|--------|
| ING-090..092 | Station discovery picks the right Graz station from a crafted multi-station metadata fixture | 0/1 | unit | `pytest tests/unit/test_geosphere.py::test_discover_station_prefers_graz_universitaet -x` | ❌ W0 | ⬜ pending |
| ING-093 | GeoSphere ingest respects politeness sleep + 7-day cache rule | 1 | unit | `pytest tests/unit/test_geosphere.py::test_ingest_respects_cache_and_politeness -x` | ❌ W0 | ⬜ pending |
| ING-094 | Coverage/range/seasonal-mean gate — 1 passing + 1 failing synthetic case each | 1 | unit | `pytest tests/unit/test_ingest_gates.py::test_gate_ing_094* -x` | ❌ W0 | ⬜ pending |
| ING-070 (ext) | `geosphere_graz_daily` fixture row added to raw-contract test | 1 | contract | `pytest tests/test_raw_contracts.py -k geosphere -x` | ❌ W0 (row to add) | ⬜ pending |
| ING-100/101 | `load_oespi()` rejects schema drift | 1 | unit | `pytest tests/unit/test_oespi.py::test_load_oespi_schema_drift_raises -x` | ❌ W0 | ⬜ pending |
| ING-102/104 | Base-only fallback path (`peak_available=False`) exercised | 1 | unit | `pytest tests/unit/test_oespi.py::test_load_oespi_base_only_fallback -x` | ❌ W0 | ⬜ pending |
| ING-103 | Continuity, positivity, 2022≥3×2019, MoM≤±60% — every gate's fail case on committed synthetic CSV (D-05) | 1 | unit | `pytest tests/unit/test_ingest_gates.py::test_gate_ing_103* -x` | ❌ W0 | ⬜ pending |
| ING-110 | Hourly spine, DST 23/25 rows, dynamic `--end` = `latest_complete_month()+18mo` | 1 | unit | `pytest tests/unit/test_calendar.py::test_build_calendar_dst_rows -x` | ❌ W0 | ⬜ pending |
| ING-111 | 2024 holiday count; Jan1/May1/Dec25 always holidays; peak-hour Mon/Sun; SG-10 subdiv assertion | 1 | unit | `pytest tests/unit/test_calendar.py::test_ing_111* -x` | ❌ W0 | ⬜ pending |
| REQ-ING-01 (M2 slice) | Full validation suite green 2019→latest on real GeoSphere pull + reconciled ÖSPI CSV | — | manual/live (D-06/D-07) | `uv run python -m epra.ingest.validate` (after real data committed) | N/A — human checkpoint | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · File Exists W0 = created in Wave 0.*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/geosphere/metadata.json` — crafted multi-station GeoSphere metadata fixture (Graz Universität + ≥1 decoy) for `discover_station()` tie-break
- [ ] `tests/fixtures/geosphere/klima_2019-01.geojson` — one committed month of realistic-shaped daily `tl_mittel` GeoJSON for `parse_geojson()`/ING-094
- [ ] `tests/fixtures/oespi/synthetic_oespi_monthly.csv` — synthetic series covering every ING-103 fail case (month gap, negative value, 2022 peak <3× 2019 mean, >60% MoM jump) per D-05
- [ ] `tests/unit/test_geosphere.py`, `tests/unit/test_oespi.py`, `tests/unit/test_calendar.py` — new test files (none exist yet)
- [ ] `_CONTRACTS["geosphere_graz_daily"]` row added to `tests/test_raw_contracts.py`
- [ ] Remove M2 rows from `tests/unit/test_stubs_fail_loudly.py` `STUBS` list as each stub is implemented

*Framework itself needs no install — `pytest>=8` + the `live` marker already exist from M1.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live GeoSphere station discovery + real daily pull green (ING-094 on real data) | REQ-ING-01 | Outbound network may be blocked in CI/agent env (D-07); deterministic CI runs against fixture | Run `python -m epra.ingest.geosphere --start 2019-01 --end <latest>` locally; commit validation report to `reports/ingestion/` |
| Reconciled real `data/manual/oespi_monthly.csv` present + ING-103 gate-clean on real data | REQ-ING-01 | Double-entry transcription is a human operation (D-03, T2.05); source confirmed at transcription time (D-01/D-04) | Human transcribes entry1/entry2 in separate sessions, runs `scripts/oespi_reconcile.py`, then `python -m epra.ingest.validate` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
