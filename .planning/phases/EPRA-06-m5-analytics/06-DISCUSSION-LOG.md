# Phase 6: M5 Analytics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-02
**Phase:** 6-M5 Analytics
**Areas discussed:** Mart kit & SSOT producer, operator interface, AN-304 vs fixture window, incomplete 2021–2025 heatmap, HMM/GARCH determinism, chart tags / LP-050
**Mode:** `/gsd-discuss-phase 6 --auto` (recommended options selected)

---

## Mart kit & SSOT producer

**Q1 — How do analytics read prices without violating "marts only"?**

| Option | Description | Selected |
|--------|-------------|----------|
| `db.connect` read-only + pure functions on frames | `run(settings)` queries marts; unit tests inject synthetic DataFrames | ✓ |
| Read `data/raw` parquet in tests and marts in prod | Two code paths; AN preamble forbids raw in analytics | |
| Always require a built DuckDB even for unit tests | Couples A1 arithmetic tests to dbt; slow; fails on empty checkout | |

**User's choice:** read-only marts in `run()`; synthetic frames in unit tests (Recommended).

**Q2 — Where do VERIFIED SSOT rows go before M6 concatenation?**

| Option | Description | Selected |
|--------|-------------|----------|
| `data/processed/ssot_inputs_analytics.parquet` (profile producer schema) | Matches D-05/M4 pattern; M6 concatenates `ssot_inputs_*.parquet` | ✓ |
| Write `reports/NUMERIC_SSOT.md` now | M6 owns `generate_ssot.py`; would invent the renderer | |
| Append into `ssot_inputs_profile.parquet` | Mixes CALIBRATED consumer rows with VERIFIED market rows | |

**User's choice:** `ssot_inputs_analytics.parquet` (Recommended).

---

## Operator interface

**Q1 — What does `make analyze` invoke?**

| Option | Description | Selected |
|--------|-------------|----------|
| `python -m epra.analytics` running A1→A2→A4→A3; no dbt | Matches profile/calendar two-step: data/warehouse already built | ✓ |
| `make warehouse && python -m …` inside `analyze` | Hides transform inside analytics; breaks "loud missing warehouse" | |
| Four separate make targets only | WBS wants one `make analyze` for AN-701 | |

**User's choice:** single module CLI, no nested dbt (Recommended).

**Q2 — Commit the 12 §6 PNGs/MDs from this environment?**

| Option | Description | Selected |
|--------|-------------|----------|
| Do not commit fixture-generated charts; tests write tmp_settings | A-2: fixture prices are not Austrian market evidence; same class as not committing processed parquet | ✓ |
| Commit fixture `make analyze` output as DL-3 | Would publish synthetic 2022–2024 structure as Q2 evidence | |
| Block M5 until a human runs real `make analyze` | Code+tests can land; DL-3 files remain operator (like M3 real dbt report) | (compatible with ✓) |

**User's choice:** no fixture charts in git (Recommended).

---

## AN-304 vs fixture window

**Q1 — How can AN-304 (needs 2019 calm) coexist with ADR-010's 2022–2024 CI warehouse?**

| Option | Description | Selected |
|--------|-------------|----------|
| Hard gate when coverage exists; pytest skip when 2019/crisis window incomplete; real `make analyze` fails closed | Honest; does not invent 2019; does not widen 70%/60% | ✓ |
| Extend bootstrap to 2019 so CI always runs AN-304 | Changes ADR-010 window; still synthetic 2019 prices — not the gate's intent | |
| Soft-pass AN-304 in CI like old ING-103 | Spec says M5 exit gate; widening/softening needs ADR | |
| Fabricate a calm 2019 series in tests and call it AN-304 | A-2 | |

**User's choice:** skip-if-incomplete, fail-if-complete-and-violated (Recommended).

---

## Incomplete heatmap years

**Q1 — AN-102 wants 5 panels 2021–2025; latest complete year may be 2024.**

| Option | Description | Selected |
|--------|-------------|----------|
| Five panel slots; missing years empty with "no complete data"; shared scale from present years | Literal 5 panels; A-2 | ✓ |
| Drop missing years and show 4 panels | Violates "5 panels" | |
| Fill 2025 with copies of 2024 | Invents a year | |

**User's choice:** empty panel, no invented heatmap (Recommended).

---

## HMM / GARCH determinism

**Q1 — How to make AN-705 survive BLAS threads (RB-11)?**

| Option | Description | Selected |
|--------|-------------|----------|
| Pin BLAS to 1 thread inside `fit_hmm`; spec seeds 42..51; tie-break lower seed on equal LL | Matches 03_MODULES; no ADR yet | ✓ |
| Commit regime parquet on first green run | RB-11 last resort; needs human ADR-014 | |
| Skip HMM in CI | Would skip the fiddly module the milestone exists to pin | |

**User's choice:** thread pin + spec seeds (Recommended).

**Q2 — GARCH scale warning?**

| Option | Description | Selected |
|--------|-------------|----------|
| Unscaled first; rescale `d_t` / 10 on scale warning; document; never clamp α+β | Literal AN-303 | ✓ |
| Always rescale | Spec says *if* the optimizer warns | |
| Fix α+β ≥ 1 to 0.999 | Forbidden | |

**User's choice:** conditional rescale (Recommended).

---

## Chart tags / LP-050

**Q1 — Epistemic tag on A1–A3 price charts?**

| Option | Description | Selected |
|--------|-------------|----------|
| VERIFIED + RP-702 source note; CALIBRATED only if constructed load shown | Prices/load/weather are D1–D3 | ✓ |
| CALIBRATED on every analytics PNG | Wrong tag; consumer profile is not the series | |
| LP-050 sentence on every A1 chart | LP-050 is for consumer-load-derived numbers; A1–A3 don't use StyriaMetal MWh | |

**User's choice:** VERIFIED market charts; AN-402 invariance sentence on A4 (Recommended).

---

## Notes for planners

- WBS order is A1→A2→A4→A3 even though T5.03/T5.04 are parallel after T5.01.
- `december_regime` is implemented in M5, consumed in M6.
- Next ADR number is 014 — do not create it speculatively.
