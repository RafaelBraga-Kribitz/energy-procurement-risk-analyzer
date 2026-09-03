---
phase: EPRA-07-m6-strategy-simulator
verified: 2026-09-03T19:30:00Z
status: passed
score: 2/3 ROADMAP criteria verified in this checkout — SC#1 ST-602(a) on real 2019+2022 and SC#3 committed NUMERIC_SSOT are operator (no data/raw, D-04)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run make warehouse && make simulate on a machine with real 2019 plus 2022 S1/S3 coverage and confirm ST-602(a) exits 0 (fail-closed if cost_S1 ≤ cost_S3)"
    expected: "retrospective.run does not raise; if (a) fails, debug calibration (T-5) — do not widen the gate"
    why_human: "This cloud checkout has no data/raw backfill (A-2, D-04). CI fixture is 2022–2024 with no 2019 (ADR-010) and must skip ST-602(a), not pass it. Do not invent 2019 prices or ÖSPI."
  - test: "Commit reports/NUMERIC_SSOT.md only from a real make ssot; do not commit fixture-warehouse euros as Q1/Q3 evidence"
    expected: "GV-302 keys present with producer tags; two make ssot runs byte-identical"
    why_human: "D-04 / A-2. Operator local. Assembler + checker are unit-tested on tmp_settings."
  - test: "Replace tests/golden/strategy_annual_summary.json with real-warehouse euros only after human-approved old-vs-new diff (EN-072)"
    expected: "Current JSON remains labeled SYNTHETIC / not Austrian market evidence"
    why_human: "D-19 / AGENTS §2.6. Current file pins annual_summary on toy 10 MWh costs."
  - test: "On GitHub branch protection for main, mark dbt-check and ssot-check required status checks (TP.02)"
    expected: "A PR cannot merge to main while those jobs are failing or pending"
    why_human: "Operator GitHub settings; code added the ssot-check job in T6.09."
---

# Phase 7: M6 Strategy Simulator Verification Report

**Phase Goal:** Reviewer can read retrospective costs and forward risk distributions answering Charter Q1 and Q3
**Verified:** 2026-09-03T19:30:00Z
**Status:** passed (code + synthetic gates; real ST-602(a) and committed SSOT deferred to operator)
**Re-verification:** No — initial verification after 07-10 SUMMARY

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ST-601..604 gates pass; ST-602 sanity relations hold (calibration first if (a) fails) | ✓ VERIFIED on contracts this checkout can honest-test; ST-602(a) real marts → OPERATOR | ST-601: `tests/test_golden_strategies.py` vs synthetic JSON (D-19). ST-602(a)/(b) skip/fail/pass unit tests; (c) fail-closed on crafted P95. ST-603/405: two `simulate` calls identical. ST-604: year-adaptive GV-302 on tmp complete frames. |
| 2 | Two consecutive runs with the same seed produce identical SSOT numeric values | ✓ VERIFIED (tmp) | Assemble ×2 byte-identical (`test_ssot.py`). Forward `simulate` ×2 identical summaries (`test_st405_two_simulate_calls_identical`). |
| 3 | `reports/NUMERIC_SSOT.md` contains the 5-year cost matrix and forward-risk table with correct epistemic tags | → OPERATOR | Assembler writes that table from producers (tags copied, E-2). File is **not** committed (D-04). Fixture years omit missing years rather than zero-fill. |

**Score:** 2/3 verified here; SC#3 (committed real SSOT) and the real-data half of SC#1 are documented operator gates, not silent passes.

### Plan-Level Must-Haves (spot-checked this session)

| Plan | Truth (condensed) | Status | Evidence |
|------|-------------------|--------|----------|
| 07-01 | ST-101 NULL drop once; w_peak from profile parquet | ✓ VERIFIED | `test_strategies_align.py` |
| 07-02 | ST-201..204 anchors; incomplete 2019 raises | ✓ VERIFIED | `test_strategies_calibration.py` |
| 07-03 | S1 monthly FULL_SPOT to the cent | ✓ VERIFIED | `test_cost_s1_hand_computed_month_to_the_cent` |
| 07-04 | S2/S3/S4; ST-503; ST-502 sentence | ✓ VERIFIED | `test_strategies_retrospective.py` |
| 07-05 | annual rank/delta; dual-write; ST-602 skip/fail; cost_* SSOT keys | ✓ VERIFIED | `test_strategies_annual.py` |
| 07-06 | exactly three ST-303 blocks; no peak_available heading | ✓ VERIFIED | `test_strategies_sensitivities.py` |
| 07-07 | ST-406 cells; ADR-014/015; ST-602(c) | ✓ VERIFIED | `test_strategies_forward.py`; ADRs 014–015 |
| 07-08 | assemble concat; ADR-016; no fake SSOT commit | ✓ VERIFIED | `test_ssot.py`; ADR-016 |
| 07-09 | HALF_UP vs banker; whitelist 2022; CI job | ✓ VERIFIED | `test_ssot_check.py`; `ci.yml` `ssot-check` |
| 07-10 | synthetic golden; Makefile CLIs; BUILD_LOG; M7 stub only | ✓ VERIFIED | golden test + `test_strategies_gates.py`; BUILD_LOG 2026-09-03 M6 |

**Score:** 10/10 plans' must-have clusters verified in code.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/epra/strategies/{align,calibration,retrospective,annual,sensitivities,forward_risk}.py` | un-stubbed | ✓ VERIFIED | no M6 rows in `test_stubs_fail_loudly.py` |
| `src/epra/report/ssot.py` / `ssot_check.py` | GV-301..303 | ✓ VERIFIED | thin `scripts/generate_ssot.py` / `check_ssot_consistency.py` |
| ADR-014, ADR-015, ADR-016 | SG-07/08/09 | ✓ VERIFIED | files present; `14_SPEC_GAPS.md` adopted |
| `tests/golden/strategy_annual_summary.json` | ST-601 synthetic | ✓ VERIFIED | disclaimer names D-19 |
| `Makefile` `simulate:` / `ssot:` | EN-050 / D-03 | ✓ VERIFIED | no `cd dbt` |
| `docs/BUILD_LOG.md` M6 | W-5 | ✓ VERIFIED | 2026-09-03 section; no market EUR |
| 07-01…07-10-SUMMARY.md | GSD close-out | ✓ VERIFIED | all ten present |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `make simulate` | retrospective then forward_risk | Makefile | ✓ WIRED |
| `make ssot` | `scripts/generate_ssot.py` | Makefile | ✓ WIRED |
| Producers | `NUMERIC_SSOT.md` | `epra.report.ssot.assemble` | ✓ WIRED |
| README/EXEC | SSOT literals | `ssot_check` / CI job 4 | ✓ WIRED (whitelist until M7 euros) |
| ST-602 fail | non-zero simulate | `RuntimeError` in `_enforce_st602` / `check_st602c` | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full lint | `make lint` | ruff + mypy 40 files | ✓ PASS |
| Full pytest | `uv run pytest -m "not live"` | **392 passed, 2 skipped**, coverage **92.55%** | ✓ PASS |
| ST-601 | `test_golden_strategies.py` | S1=120, S3=100 toy EUR | ✓ PASS |
| No committed SSOT | `reports/NUMERIC_SSOT.md` | absent | ✓ PASS (D-04) |
| M7 stub only | `test_stubs_only_m7_charts` | M7 charts | ✓ PASS |
| Real ST-602(a) | needs warehouse | no `data/raw/` | → operator |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| REQ-ST-01 | PARTIAL | Engine + synthetic ST-601 + skip-if-incomplete ST-602; real (a) operator |
| REQ-Q1 | PARTIAL | Annual matrix + wrong-strategy keys on tmp; committed SSOT operator |
| REQ-Q3 | PARTIAL | Forward P95/CVaR SIMULATED keys on tmp; seed-reproducible in unit tests |
| ST-101..107, 201..204, 301..304, 401..406, 502, 503, 601..604 | code SATISFIED as testable | unit + golden |
| GV-301..303 | code SATISFIED | assembler + checker + CI job |
| D-01..D-20 | SATISFIED in code | locked discuss decisions |

**Coverage:** code IDs satisfied. REQ-ST-01 / REQ-Q1 / REQ-Q3 remain open in REQUIREMENTS.md until operator ST-602(a) + committed `NUMERIC_SSOT.md` (not a silent checkbox).

## Human Verification Required

1. **ST-602(a) real marts** — `make warehouse && make simulate` with 2019 anchors and 2022 S1/S3; do not widen; do not invent prices.
2. **D-04** — commit SSOT only from a real `make ssot`.
3. **EN-072** — real-euro golden replacement is human-approved.
4. **TP.02** — mark `dbt-check` and `ssot-check` required on `main`.
5. **Forward horizon profile** — production `forward_risk.run()` currently reuses pool hours when `horizon_hours` is omitted; operator/M7 should feed the SPEC-03 forward window.

## Gaps Summary

**No code gaps for M6 implementation on the contracts this phase can honest-test.** Phase 7 ROADMAP checkbox stays open until SC#1 real ST-602(a) and SC#3 committed SSOT. Ready to plan Phase 8 (M7 reporting) in parallel with those operator gates. Charter §4.2 still applies (no fifth strategy, no extra sensitivities, no forecasting). `.pbix` remains human (AGENTS §2.5).

---

## Verification Metadata

**Verification approach:** Goal-backward against ROADMAP Phase 7 success criteria + ST-601/405/602 unit contracts + full non-live suite
**Must-haves source:** 07-01..07-10 PLAN.md `must_haves.truths`
**Automated checks:** `make lint`; pytest 392 passed / 92.55% coverage; ST-601 synthetic; GV-303 missing-SSOT skip
**Human checks required:** ST-602(a) real warehouse; NUMERIC_SSOT commit; EN-072; TP.02
**Basis:** commits through 07-10 SUMMARY + BUILD_LOG; verified 2026-09-03
