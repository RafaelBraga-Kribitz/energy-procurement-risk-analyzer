---
phase: 6
slug: m5-analytics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-02
---

# Phase 6 — Validation Strategy

> Per-phase validation contract. Seeded from `06-RESEARCH.md`.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest `tests/unit/test_analytics_kit.py`, `test_analytics_a1.py`, `test_analytics_a2.py`, `test_analytics_a4.py`, `test_analytics_a3.py` (names flexible) |
| **Quick run** | `uv run pytest tests/unit/test_analytics*.py -x --no-cov` |
| **Full suite** | `uv run pytest -m "not live"` (coverage ≥ 80%) |
| **Lint** | `make lint` |
| **AN-304** | skip without 2019+crisis window; hard fail in `make analyze` when coverage exists |
| **Charts** | matplotlib object inspection — no pixel golden |

## Sampling Rate

- After every task commit: analytics unit tests
- After T5.07: `make lint && make test`; grep 12 filenames in kit constants vs SPEC-04 §6
- Before `/gsd-verify-work`: AN-701 on tmp_settings; AN-705 twice on SSOT parquet bytes/values; AN-304 skip documented

## Per-Task Verification Map

| Item | Requirement | Test | File |
|------|-------------|------|------|
| T5.01 kit | RP-701/702, SSOT schema, empty-SQL raise | unit | ❌ W0 |
| T5.02 A1 | AN-101..105, AN-704, neg_hours keys | unit + prose length | ❌ W0 |
| T5.03 A2 | AN-201..203, zero line, spread_mean keys | unit | ❌ W0 |
| T5.04 A4 | AN-401..402, HDD coef > 0 on synthetic, invariance sentence | unit | ❌ W0 |
| T5.05 HMM | AN-301/302/304, determinism, december_regime | unit; AN-304 skip path | ❌ W0 |
| T5.06 GARCH | AN-303 persistence identity; α+β≥1 reported | unit | ❌ W0 |
| T5.07 make | AN-701/705, BUILD_LOG, stubs gone | make + pytest | ❌ W0 |

## Wave 0 Requirements

- [ ] `_kit.py` + `__main__.py`
- [ ] Four `run()` implementations
- [ ] 12 artifact filenames constant matching SPEC-04 §6
- [ ] `ssot_inputs_analytics.parquet` writer
- [ ] Makefile `analyze:`
- [ ] AN-304 skip/fail split
- [ ] BUILD_LOG M5 entry
- [ ] M5 rows removed from `test_stubs_fail_loudly.py`

## Phase Gate (ROADMAP)

1. §6 artifacts regenerate from `make analyze` (tmp or real reports)
2. AN-304 on **real** 2021–2023 data (operator if this checkout has no warehouse)
3. SPEC-06 §7 notes/tags on PNGs (object inspection)

## Security / honesty

- No invented EUR in committed markdown.
- Fixture charts stay in tmp.
- No tokens.
