---
phase: 7
slug: m6-strategy-simulator
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-03
---

# Phase 7 — Validation Strategy

> Per-phase validation contract. Seeded from `07-RESEARCH.md`.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest `tests/unit/test_strategies_align.py`, `test_strategies_calibration.py`, `test_strategies_retrospective.py`, `test_strategies_forward.py`, `test_ssot.py`, `test_ssot_check.py`, `tests/test_golden_strategies.py` |
| **Quick run** | `uv run pytest tests/unit/test_strategies*.py tests/unit/test_ssot*.py tests/test_golden_strategies.py -x --no-cov` |
| **Full suite** | `uv run pytest -m "not live"` (coverage ≥ 80%) |
| **Lint** | `make lint` |
| **ST-602** | skip without 2019+2022 coverage; hard fail in `make simulate` when coverage exists |
| **Charts** | matplotlib object inspection — no pixel golden |
| **Goldens** | synthetic JSON (D-19); `generate_golden_metrics.py` dirty-tree refuse |

## Sampling Rate

- After every task commit: that module's unit tests
- After T6.05: dual-write parquet schema vs SPEC-02 §5 column list
- After T6.07: determinism ×2 on `summarize` values; N=50 smoke P5≤P50≤P95
- After T6.09: mutation test on checker
- After T6.10: `make lint && make test`; BUILD_LOG
- Before `/gsd-verify-work`: ST-603 twice on tmp; ST-601 synthetic; ST-602 skip documented

## Per-Task Verification Map

| Item | Requirement | Test | File |
|------|-------------|------|------|
| T6.01 align | 3 NULL hours → identical monthly volume; log emitted | unit | pending |
| T6.02 anchors | synthetic-2019 hand values; ST-202 docstring sentence; identities | unit | pending |
| T6.03 S1 | hand-computed month to the cent | unit | pending |
| T6.04 S2/S3/S4 | ref identity; ST-503 no-lookahead; ST-602(b) on synthetic; ST-502 in artifacts | unit | pending |
| T6.05 annual/charts | rank/delta; ST-602(a) skip/fail; parquet dual-write; ST-304 artists | unit | pending |
| T6.06 sensitivities | three blocks in one md; same engine; no fourth | unit | pending |
| T6.07 forward | cell ≡ toy path; D-08 order; SG-08 closed form; ST-602(c) on crafted; no-crisis pool filter | unit + ADR-014/015 | pending |
| T6.08 SSOT | GV-302 keys on tmp; two assemble → byte-identical; duplicate key raises | unit + ADR-016 | pending |
| T6.09 checker | half-up match; whitelist years; mutation; CI job exists | unit + ci.yml | pending |
| T6.10 goldens | dirty refuse; ST-601; ST-405; stubs gone; BUILD_LOG | unit + make | pending |

## Wave 0 Requirements

- [ ] `align` + `AlignedVolumes`
- [ ] `Anchors` + ST-201..204
- [ ] S1–S4 monthly costs + annual summary
- [ ] Dual-write procurement parquet
- [ ] Three sensitivities only
- [ ] Cost cells + seeded simulate + summarize
- [ ] ADR-014, ADR-015, ADR-016
- [ ] `epra.report.ssot` + `ssot_check` + scripts
- [ ] CI `ssot-check` job (not necessarily GitHub-required)
- [ ] Synthetic `tests/golden/strategy_annual_summary.json`
- [ ] Makefile `simulate:` / `ssot:`
- [ ] BUILD_LOG M6 entry
- [ ] M6 rows removed from `test_stubs_fail_loudly.py`

## Phase Gate (ROADMAP)

1. ST-601..604 on contracts this phase can honestly test (synthetic golden; skip-if-incomplete ST-602(a))
2. Two seeded runs → identical SSOT numeric values (tmp_settings)
3. Assembler emits GV-302 keys present in producer parquets with correct tags (tmp)

Operator on a real 2019+ warehouse: ST-602(a), `p_ref_base` band, committed `NUMERIC_SSOT.md`.

## Security / honesty

- No invented EUR in committed `reports/` strategy markdown or `NUMERIC_SSOT.md` (D-04).
- Fixture charts stay in tmp.
- No tokens.
- ST-502 sentence on S2/S3/S4 artifacts.
- Synthetic golden file must not be described as Austrian market results in BUILD_LOG.
