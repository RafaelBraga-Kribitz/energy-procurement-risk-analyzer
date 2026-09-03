---
phase: EPRA-06-m5-analytics
verified: 2026-09-03T10:15:00Z
status: passed
score: 2/3 ROADMAP criteria verified in this checkout — SC#2 AN-304 on real 2021–2023 is operator (no data/raw)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run make warehouse && make analyze on a machine with real 2019 plus 2021-09-01..2023-06-30 mart coverage and confirm AN-304 exits 0 (fail-closed if fractions miss 70/60)"
    expected: "a3_regime_stats.md records status pass; make analyze does not raise AN-304 failed"
    why_human: "This cloud checkout has no data/raw backfill (A-2, D-05). Fixture/CI warehouse is 2022-2024 (ADR-010) and must skip AN-304, not pass it. Do not invent 2019 prices or widen 70/60."
  - test: "Do not commit CI-fixture reports/analytics PNGs as Q2 evidence"
    expected: "Committed analytics charts, if any, come from a real warehouse run"
    why_human: "D-05 / A-2. Operator local."
  - test: "On GitHub branch protection for main, mark the dbt-check job a required status check (TP.02)"
    expected: "A PR cannot merge to main while dbt-check is failing or pending"
    why_human: "Carried from M3; operator GitHub settings."
---

# Phase 6: M5 Analytics Verification Report

**Phase Goal:** Reviewer can read market structure evidence answering Charter Q2
**Verified:** 2026-09-03T10:15:00Z
**Status:** passed (code + synthetic gates; real AN-304 deferred to operator)
**Re-verification:** No — initial verification after 06-07 SUMMARY

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Analytics artifacts in `reports/analytics/` match SPEC-04 §6 and pass plausibility gates | ✓ VERIFIED (CLI on injected marts) | `test_an701_twelve_artifacts_from_wiped_dir`: all 12 `kit.ARTIFACT_NAMES` written after wipe. AN-704 ≥400 chars on the four `.md` files. Real-dir operator charts are not committed (D-05). |
| 2 | Crisis-regime sanity gate AN-304 passes on real 2021–2023 data | → OPERATOR | Unit tests cover skip (no 2019), fail-closed (coverage present, fractions miss), and pass (constructed labels). `regimes.run` raises `RuntimeError` on fail. This checkout cannot run the gate on ENTSO-E marts (no `data/raw/`). |
| 3 | Charts carry epistemic tags and obey SPEC-06 §7 caption rules | ✓ VERIFIED | Kit `stamp_rp702` asserts FIGSIZE, `SOURCE_NOTE`, tag VERIFIED. A1 duration 2022 vermillion; A2 `axhline(0)`; A3 twin axis + regime bands; A4 weekend scatter. LP-050 not stamped on A1–A3 (D-13). |

**Score:** 2/3 verified here; SC#2 is a documented operator gate, not a silent pass.

### Plan-Level Must-Haves (spot-checked this session)

| Plan | Truth (condensed) | Status | Evidence |
|------|-------------------|--------|----------|
| 06-01 | Mart loaders raise with SQL; RP-701/702; CLI exit 1 if no warehouse | ✓ VERIFIED | `test_analytics_kit.py` (empty SQL, stamp, missing warehouse). |
| 06-02 | AN-101..105; NULL prices dropped; heatmap empty panels; 2022 vermillion | ✓ VERIFIED | `test_analytics_a1.py`. |
| 06-03 | spread_stats; zero line; you-are-not-in-Germany prose | ✓ VERIFIED | `test_analytics_a2.py`. |
| 06-04 | month FE HC1; HDD not recomputed; invariance sentence | ✓ VERIFIED | `test_analytics_a4.py`. |
| 06-05 | arithmetic d_t; HMM identity; AN-304 skip/fail; december_regime | ✓ VERIFIED | `test_analytics_a3.py`. |
| 06-06 | GARCH persistence identity; ≥1 not clamped | ✓ VERIFIED | `test_garch_persistence_identity`; `test_near_integrated_persistence_is_not_clamped`. |
| 06-07 | make analyze; AN-701/705; BUILD_LOG; no M5 stubs | ✓ VERIFIED | Makefile recipe; `test_analytics_gates.py`; BUILD_LOG 2026-09-03; stubs file has no M5 rows. |

**Score:** 7/7 plans' must-have clusters verified in code.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/epra/analytics/_kit.py` | loaders/writers | ✓ VERIFIED | upsert SSOT by key |
| `descriptive/spread/weather/regimes.py` | A1–A4 `run()` | ✓ VERIFIED | no `NotImplementedError` |
| `python -m epra.analytics` | A1→A2→A4→A3 | ✓ VERIFIED | `__main__.py` |
| `Makefile` `analyze:` | EN-050 / D-04 | ✓ VERIFIED | `python -m epra.analytics`; no dbt |
| `tests/unit/test_analytics_*.py` | unit + gates | ✓ VERIFIED | kit, a1–a4, a3, gates |
| `docs/BUILD_LOG.md` M5 | W-5 | ✓ VERIFIED | 2026-09-03 section |
| 06-01…06-07-SUMMARY.md | GSD close-out | ✓ VERIFIED | all seven present |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `make analyze` | `epra.analytics.__main__.main` | Makefile | ✓ WIRED |
| CLI | DuckDB marts | `_kit.load_price_*` | ✓ WIRED |
| A1–A4 | `ssot_inputs_analytics.parquet` | `write_ssot_rows` upsert | ✓ WIRED (M6 concatenates) |
| AN-304 fail | non-zero analyze | `RuntimeError` in `regimes.run` | ✓ WIRED |
| Charts | RP-702 | `save_png` / `stamp_rp702` | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full lint | `make lint` | ruff + mypy 34 files | ✓ PASS |
| Full pytest | `uv run pytest -m "not live"` | **330 passed, 2 skipped**, coverage **93.21%** | ✓ PASS |
| AN-701/705 | `test_analytics_gates.py` | 12 files; SSOT identity | ✓ PASS |
| AN-304 skip ≠ pass | `test_check_an304_skip_without_2019` | status skip | ✓ PASS |
| No M5 stubs | `test_stubs_fail_loudly.py` | M6/M7 only | ✓ PASS |
| Real AN-304 | needs warehouse | no `data/raw/` | → operator |
| Fixture PNGs | git | not committed | ✓ PASS |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| REQ-ANA-01 | PARTIAL | A1–A4 + AN-701/704/705 green; AN-304 real-data clause open |
| REQ-Q2 | PARTIAL | §6 files regenerate in tests; DL-3 operator copy of charts not in this repo |
| AN-101..105, 201..203, 301..303, 401..402 | ✓ SATISFIED | unit tests |
| AN-304 | SKIP/FAIL-CLOSED in code; real pass operator | D-06 |
| RP-701/702/703 | ✓ SATISFIED | kit + formatters |
| D-01..D-13 | ✓ SATISFIED | locked discuss decisions implemented |

**Coverage:** code IDs satisfied. REQ-ANA-01 / REQ-Q2 remain open in REQUIREMENTS.md until operator AN-304 + real `reports/analytics/` (not a silent checkbox).

## Human Verification Required

1. **AN-304 real marts** — `make warehouse && make analyze` with complete 2019 and 2021-09-01..2023-06-30; do not widen 70/60; do not invent 2019 prices.
2. **D-05** — commit analytics PNGs only from a real warehouse, never the CI fixture.
3. **TP.02** — mark `dbt-check` required on `main` (carried from M3).
4. **EN-072** — consumer golden regen still human.

## Gaps Summary

**No code gaps for M5 implementation.** Phase 6 ROADMAP checkbox stays open until SC#2 is run on real data. Ready to plan Phase 7 (M6 strategies) in parallel with that operator gate. Charter §4.2 still applies (no fifth analytics block, no forecasting).

---

## Verification Metadata

**Verification approach:** Goal-backward against ROADMAP Phase 6 success criteria + AN-701/705 + full non-live suite
**Must-haves source:** 06-01..06-07 PLAN.md `must_haves.truths`
**Automated checks:** `make lint`; pytest 330 passed / 93.21% coverage; AN-304 skip/fail unit tests
**Human checks required:** AN-304 real warehouse; D-05 PNG policy; TP.02; EN-072
**Basis:** commits through 06-07 SUMMARY + BUILD_LOG; verified 2026-09-03
