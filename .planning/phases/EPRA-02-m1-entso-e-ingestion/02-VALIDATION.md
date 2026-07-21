---
phase: 2
slug: m1-entso-e-ingestion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-21
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for M1 ENTSO-E ingestion (EPRA-02).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-cov |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/unit/test_entsoe_parse.py tests/unit/test_aggregate_hourly.py -x` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~60 seconds (fixtures only; no live network) |

---

## Sampling Rate

- **After every task commit:** Run the plan task's `<automated>` verify command
- **After every plan wave:** Run `uv run pytest -m "not live"`
- **Before `/gsd-verify-work`:** `make lint && make test` green
- **Phase gate (human):** `make validate-ingest` with `ENTSOE_API_TOKEN` on real 2019→latest data
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ADR-003/004/005 | manual | ADR files on disk + grep EntsoeRawClient | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ING-070 | unit | `uv run python -c "import pyarrow; import pandas as pd; pd.io.parquet.get_engine('pyarrow')"` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | ING-006 | unit | `uv run python -c "from epra.ingest.exceptions import GateFailure"` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | ING-003/004 | unit | `uv run pytest tests/unit/test_io.py -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | ING-030 | unit | `uv run pytest tests/unit/test_fetch.py -k EntsoeQuery -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | ING-006..009 | unit | `uv run pytest tests/unit/test_fetch.py -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 4 | ING-062/063 | unit | `uv run pytest tests/unit/test_aggregate_hourly.py tests/unit/test_entsoe_parse.py -x` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 4 | ING-031/050 | unit | `uv run pytest tests/unit/test_entsoe_parse.py -k "utc or dst" -x` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 5 | ING-002/042 | integration | `uv run pytest tests/unit/test_entsoe_orchestration.py -x` | ❌ W0 | ⬜ pending |
| 02-06-01 | 06 | 5 | ING-080..085 | unit | `uv run pytest tests/unit/test_ingest_gates.py -x` | ❌ W0 | ⬜ pending |
| 02-07-01 | 07 | 6 | ING-070 | integration | `uv run pytest tests/test_raw_contracts.py -x` | ❌ W0 | ⬜ pending |
| 02-07-02 | 07 | 6 | REQ-ING-01 | manual | `make validate-ingest` (human token) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/ADR/ADR-003..005` — SG-01, pyarrow, SG-02 decisions
- [ ] `pyarrow` in `pyproject.toml`
- [ ] `tests/conftest.py` — tmp data paths
- [ ] `tests/fixtures/entsoe/*` — XML fixtures per T1.03a
- [ ] `tests/unit/test_io.py`, `test_fetch.py`, `test_entsoe_parse.py`, `test_aggregate_hourly.py`, `test_ingest_gates.py`
- [ ] `tests/test_raw_contracts.py` — ING-070 contract tests
- [ ] Makefile targets: `backfill`, `ingest`, `validate-ingest`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live ENTSO-E backfill | ING-080..085 on real data | Requires `ENTSOE_API_TOKEN` (human-owned) | Set token in `.env`; run `make backfill` then `make validate-ingest`; commit validation report |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
