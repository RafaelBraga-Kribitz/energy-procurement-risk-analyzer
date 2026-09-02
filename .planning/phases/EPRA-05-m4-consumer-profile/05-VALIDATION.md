---
phase: 5
slug: m4-consumer-profile
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-02
---

# Phase 5 — Validation Strategy

> Per-phase validation contract. Seeded from `05-RESEARCH.md`. Validate-phase re-keys rows to `05-NN-MM` after planning.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`tests/unit/test_profile.py` + existing bootstrap/warehouse tests) |
| **Config** | `pyproject.toml` `[tool.pytest.ini_options]` — unchanged; no live marker |
| **Quick run** | `uv run pytest tests/unit/test_profile.py -x --no-cov` |
| **Full suite** | `uv run pytest -m "not live"` (coverage ≥ 80% still required) |
| **Lint** | `make lint` (ruff + mypy `--strict` on `src/epra`) |
| **Warehouse smoke (after D-08)** | isolated `bootstrap --force --data-root` then `dbt build` (existing dbt-check path) |
| **Estimated runtime** | profile unit tests: seconds (reuse one module-scoped calendar); full pytest: existing suite + new cases |

## Sampling Rate

- **After every task commit:** `uv run pytest tests/unit/test_profile.py -m "not live" --no-cov` plus any touched analog tests (bootstrap, stubs, warehouse report)
- **After every plan wave:** `make lint && make test`
- **Before `/gsd-verify-work`:** full `make lint && make test`; grep AC; LP-040 twice for bit-stability; isolated dbt-check if sources.yml/bootstrap changed
- **Phase gate:** ROADMAP SC#1–#3 (LP-040..042, 50 GWh ±0.01, peak share SSOT-ready)
- **Max feedback latency:** ~full pytest (existing)

## Per-Task Verification Map

| Item | Requirement | Secure / correct behavior | Test type | Automated command | File exists |
|------|-------------|---------------------------|-----------|-------------------|-------------|
| T4.01 weights | LP §2 steps 1–4, SG-04 | day_type precedence; 2022 Aug 1–7; holiday Monday weekend; Dec 25=Dec 26 weights; no `0.18\|0.60\|1.06` in `src/` | unit + grep | `pytest tests/unit/test_profile.py` + `rg` | ❌ W0 |
| T4.02 normalize | LP-004, LP-034 | full years 50000±0.01 incl. DST years; 6-month volumes match full-year months | unit | pytest | ❌ W0 |
| T4.03 outputs | LP-003, LP-020, LP-021 | parquet schemas; 2019 share ∈ [0.42,0.48]; yearly Δ < 1 pp; SSOT producer row | unit + I/O on tmp_path | pytest | ❌ W0 |
| T4.03 dbt path | D-08, SG-06 | sources.yml single file; bootstrap writes it; mart still builds | bootstrap pytest + dbt-check | pytest bootstrap; `dbt build` isolated | ❌ W0 (modify existing) |
| T4.04 goldens | LP-030, LP-040..042 | ratio band; Aug&lt;Jul; Dec25=Dec26 load; sha256 file; 50001 breaks digest; flat_baseload | unit + golden file | pytest; run twice | ❌ W0 |
| T4.05 make | EN-050, LP-051 | `make profile` twice byte-identical; stubs gone; LIMITATIONS §1 unchanged; BUILD_LOG | make + pytest | `make profile` on tmp/data; `make lint && make test` | ❌ W0 |
| ADR-012/013 | GV-201 | files exist; SG rows marked adopted | file exists | path check in plan verify | ❌ W0 |

*Status: ⬜ pending at plan time.*

## Wave 0 Requirements

- [ ] `src/epra/consumer/profile.py` real implementation + CLI
- [ ] `tests/unit/test_profile.py`
- [ ] `tests/golden/consumer_load_2023.sha256`
- [ ] `docs/ADR/ADR-012_*`, `docs/ADR/ADR-013_*` + `14_SPEC_GAPS.md` status
- [ ] `dbt/models/sources.yml` consumer single-file location
- [ ] `scripts/bootstrap_fixture_warehouse.py` + `test_bootstrap_fixture_warehouse.py`
- [ ] `Makefile` `profile:` + `all:` order
- [ ] `test_stubs_fail_loudly.py` M4 rows removed
- [ ] `warehouse.report` stand-in list drops consumer mart
- [ ] `docs/BUILD_LOG.md` M4 entry
- [ ] `tmp_settings` redirects `data_processed` (if CLI tests write files)

## Phase Gate (ROADMAP)

1. LP-040..042 green with committed checksum
2. Each full local year sums to 50,000.00 ± 0.01 MWh
3. `consumer_peak_share` in `ssot_inputs_profile.parquet` (2019, CALIBRATED)

## Security / honesty

- No network; no token; no invented prices (A-2 N/A — constructed profile is in-scope CALIBRATED).
- LP-051 text already in LIMITATIONS §1 — confirm, do not invent SSOT euros.
