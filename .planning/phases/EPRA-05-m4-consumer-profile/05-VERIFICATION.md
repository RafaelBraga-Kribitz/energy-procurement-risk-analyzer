---
phase: EPRA-05-m4-consumer-profile
verified: 2026-09-02T14:30:00Z
status: passed
score: 3/3 ROADMAP criteria met — LP-040..042 + golden digest; full local years 50 000.00 ± 0.01; consumer_peak_share SSOT-ready (ADR-013)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Approve any future regeneration of tests/golden/consumer_load_2023.sha256 (EN-072)"
    expected: "Digest changes only after a human-approved old-vs-new diff and why"
    why_human: "AGENTS.md stop-list: golden regeneration is never silent. Current digest 3dd8c08c… is committed and stable (LP-040 run twice this session)."
  - test: "On GitHub branch protection for main, mark the dbt-check job a required status check (TP.02)"
    expected: "A PR cannot merge to main while dbt-check is failing or pending"
    why_human: "Operator GitHub settings; out of code scope since M3. Isolated fixture dbt build still PASS=64 after the D-08 single-file consumer path."
---

# Phase 5: M4 Consumer Profile Verification Report

**Phase Goal:** Deterministic hourly load profile available for all strategy cost calculations
**Verified:** 2026-09-02T14:30:00Z
**Status:** passed
**Re-verification:** No — initial verification (GSD close-out after 05-05 SUMMARY)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Golden and property tests (LP-040..042) pass with fixed seed/config | ✓ VERIFIED | `test_lp040_2023_golden_ratio_aug_lt_jul_dec25_eq_dec26` **passed twice** this session (bit-stable). Digest `3dd8c08c139df9d531e0fc0f3159a2c310defdf8baf7319422f08131ede8d821` matches `tests/golden/consumer_load_2023.sha256`. LP-041/042 in the same module: 2023 no NaN/negative; `annual_consumption_mwh=50001` breaks the digest. Zero randomness (LP-001); YAML numerics not in `src/epra/consumer`. |
| 2 | Each local calendar year sums to 50,000.00 MWh ± 0.01 after normalization | ✓ VERIFIED | `test_full_local_year_sums_to_annual` parametrized **2019, 2020, 2023, 2024** (DST years included) — all passed. LP-034 H1-2023 partial months match the full-year months ± 0.01. |
| 3 | `consumer_peak_share` is computed and ready for SSOT inputs | ✓ VERIFIED | `write_profile_outputs` writes `ssot_inputs_profile.parquet` columns `key, value, unit, tag, produced_by` with `key=consumer_peak_share`, `unit=fraction`, `tag=CALIBRATED`, `produced_by=epra.consumer.profile`. 2019 share ~0.486 (ADR-013; tests `0.42 ≤ share < 0.50`); yearly \|Δ\| < 1 pp. YAML was **not** retuned (A-2). |

**Score:** 3/3 ROADMAP criteria verified.

### Plan-Level Must-Haves (spot-checked this session)

| Plan | Truth (condensed) | Status | Evidence |
|------|-------------------|--------|----------|
| 05-01 | Vectorized weights; ADR-012 2022 Aug 1–7; no YAML literals in consumer src | ✓ VERIFIED | ADR-012 present; `rg '0\.18\|0\.60\|1\.06' src/epra/consumer` empty; rule tests in `test_profile.py`. |
| 05-02 | LP-004/LP-034 normalize; `build_profile` → `ts_utc, load_mwh` | ✓ VERIFIED | Full-year sums + LP-034 tests green. |
| 05-03 | Outputs + ADR-013 + D-08 single-file `sources.yml` | ✓ VERIFIED | Roundtrip writer test; isolated dbt still reads `../data/processed/consumer_load_hourly.parquet`. |
| 05-04 | `flat_baseload` + LP-040 golden committed | ✓ VERIFIED | Golden file + twice-run LP-040; `test_flat_baseload_unit_weights_then_same_annual`. |
| 05-05 | CLI / `make profile` / `all:` profile then transform / stand-in flag / LP-051 / BUILD_LOG | ✓ VERIFIED | Makefile `all: profile transform …`; warehouse `_STAND_IN_MARTS = (fct_procurement_cost_monthly,)`; LIMITATIONS.md §1 has LP-051 sentence; BUILD_LOG 2026-09-02 entry. Full suite **287 passed, 2 skipped**, coverage **92.64%**. |

**Score:** 5/5 plans' must-have clusters verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/epra/consumer/profile.py` | Weight engine + CLI | ✓ VERIFIED | `main()`, `build_profile`, writers; no `NotImplementedError` |
| `tests/unit/test_profile.py` | LP + CLI tests | ✓ VERIFIED | Included in 287-pass suite |
| `tests/golden/consumer_load_2023.sha256` | LP-040 digest | ✓ VERIFIED | `3dd8c08c…ede8d821` |
| `docs/ADR/ADR-012_*` / `ADR-013_*` | SG-04 / SG-03 | ✓ VERIFIED | Files present; `14_SPEC_GAPS.md` adopted |
| `dbt/models/sources.yml` | Single-file consumer parquet | ✓ VERIFIED | Isolated `dbt build` PASS=64 |
| `Makefile` `profile:` + `all:` order | EN-050 / D-08 | ✓ VERIFIED | `python -m epra.consumer.profile`; profile before transform |
| `LIMITATIONS.md` §1 | LP-051 | ✓ VERIFIED | Constructed-not-measured + RLM + flat_baseload sentence |
| `docs/BUILD_LOG.md` M4 entry | W-5 | ✓ VERIFIED | 2026-09-02 section |
| `05-01`…`05-05-SUMMARY.md` | GSD close-out | ✓ VERIFIED | All five present |

**Artifacts:** 9/9 verified

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `make profile` | `epra.consumer.profile.main` | Makefile | ✓ WIRED |
| CLI | ING-110 `calendar.parquet` | `_dataset_root` / D-01 | ✓ WIRED |
| Profile parquet | `fct_consumer_load_hourly` | `sources.yml` single file | ✓ WIRED (isolated PASS=64) |
| Peak share | SSOT producer file | `ssot_inputs_profile.parquet` | ✓ WIRED (concat is M6) |
| `all:` | profile then transform | Makefile | ✓ WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| LP-040 twice | pytest `test_lp040_…` ×2 | both pass, same digest | ✓ PASS |
| Annual sums | `test_full_local_year_sums_to_annual` | 4 years passed | ✓ PASS |
| Isolated dbt-check | bootstrap `--force --data-root /tmp/iso-epra-m4/data` then `dbt build` | **PASS=64 WARN=0 ERROR=0 TOTAL=64** | ✓ PASS |
| Committed ÖSPI | `git status --porcelain data/manual/oespi_monthly.csv` | empty | ✓ PASS |
| No repo `data/processed` consumer parquet | path check | absent (gitignored / not created) | ✓ PASS |
| `make lint` + full pytest | 05-05 session | ruff/mypy clean; 287 passed | ✓ PASS |
| TP.02 required-check flip | GitHub settings | out of code scope | → human |
| Real-data `make profile` | needs local calendar | this checkout has no `data/raw/` backfill (A-2) | → operator local |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| REQ-LP-01 | ✓ SATISFIED | SC#1/#2/#3 all verified |
| LP-040..042 | ✓ SATISFIED | Golden + properties |
| LP-051 | ✓ SATISFIED | LIMITATIONS.md §1 confirmed |
| EN-050 | ✓ SATISFIED | CLI byte-identical second run |
| ADR-012 / ADR-013 | ✓ SATISFIED | Files + tests |

**Coverage:** 5/5 in-scope IDs satisfied. TP.02 remains operator GitHub settings. EN-072 regen remains human.

## Human Verification Required

1. **EN-072** — do not regenerate the 2023 golden digest without a human-approved diff.
2. **TP.02** — mark `dbt-check` required on `main` (carried from M3).
3. **Operator local** — `make profile` on a machine with `calendar.parquet` (not this cloud checkout).

## Gaps Summary

**No code gaps.** Phase goal achieved. Ready to proceed to Phase 6 (M5 analytics). `fct_procurement_cost_monthly` remains a stand-in until M6. LP-050 captions deferred to M5/M7 artifacts.

---

## Verification Metadata

**Verification approach:** Goal-backward against ROADMAP Phase 5 success criteria + independent LP-040 double-run + isolated fixture `dbt build` after D-08 path change
**Must-haves source:** 05-01..05-05 PLAN.md `must_haves.truths`
**Automated checks:** LP-040 ×2; annual-sum + peak-share tests; isolated `dbt build` PASS=64; 05-05 full suite 287 passed / 92.64% coverage
**Human checks required:** 2 blocking-policy (EN-072, TP.02) + 1 operator-local `make profile`
**Basis:** commits through `6f932ff` (05-05 SUMMARY + BUILD_LOG); verified 2026-09-02

---

*Verified: 2026-09-02*
