# Phase 7: M6 Strategy Simulator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-03
**Phase:** 7-M6 Strategy Simulator
**Areas discussed:** Shared aligner & w_peak, operator interface, parquet vs dbt glob, 2019 vs fixture, ST-406 cells, SG-07/08/HMM, captions/sensitivities, SSOT/goldens/ADRs
**Mode:** `/gsd-discuss-phase 7 --auto` (recommended options selected)

---

## Shared aligner & w_peak

**Q1 — Where does ST-101 NULL-price drop live?**

| Option | Description | Selected |
|--------|-------------|----------|
| Once in a shared aligner; all strategies consume `AlignedVolumes` | ST-501 fairness by construction; one log line | ✓ |
| Each strategy drops NULLs independently | Easy to diverge S4 spot leg from S1 | |
| Drop only in S1; leave S2/S3 on full monthly volume | Violates ST-101 “rescale other strategies identically” | |

**User's choice:** shared aligner (Recommended).

**Q2 — Where does `w_peak` come from?**

| Option | Description | Selected |
|--------|-------------|----------|
| `ssot_inputs_profile.parquet` key `consumer_peak_share` | ST-102; ADR-013; never retyped | ✓ |
| Hardcode 0.486 / copy YAML | A-2 / ST-102 violation | |
| Recompute peak share inside calibration | Duplicate LP-020; can drift from SSOT | |

**User's choice:** profile SSOT producer file (Recommended).

---

## Operator interface

**Q1 — What does `make simulate` invoke?**

| Option | Description | Selected |
|--------|-------------|----------|
| retrospective CLI then forward_risk CLI; no dbt | Matches analyze/profile; loud missing warehouse | ✓ |
| Nest `make warehouse` inside simulate | Hides transform; breaks stand-in vs real reasoning | |
| One mega-module CLI only | Spec ST-002 names two entry points | |

**User's choice:** two CLIs, no nested dbt (Recommended).

**Q2 — Commit strategy charts / NUMERIC_SSOT from this environment?**

| Option | Description | Selected |
|--------|-------------|----------|
| Do not commit fixture euros as Q1/Q3 evidence | A-2; same class as M5 analytics PNGs | ✓ |
| Commit fixture `make simulate` output as DL-2 | Would publish synthetic 2022–2024 costs as Austrian results | |

**User's choice:** no fixture strategy artifacts in git (Recommended).

---

## Stand-in parquet path

**Q1 — ST-001 names `strategy_costs_monthly.parquet`; dbt reads `procurement_cost_monthly/**`.**

| Option | Description | Selected |
|--------|-------------|----------|
| Dual-write: spec filename + ADR-010 glob file; mart SQL unchanged | Spec + SG-06 / ADR-010 both honored | ✓ |
| Change sources.yml to the spec filename only | Touches DM-004 path; bootstrap glob must move in the same PR | |
| Write only the glob path | Violates ST-001 name | |

**User's choice:** dual-write (Recommended).

---

## 2019 vs ADR-010 fixture

**Q1 — Calibration needs 2019; CI warehouse is 2022–2024.**

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic-2019 unit tests; skip-if-incomplete on real-data gates; fail-closed when 2019 exists | Honest; matches M5 D-06 | ✓ |
| Extend bootstrap to 2019 so CI always computes anchors | Changes ADR-010; still synthetic 2019 — not ST-201's intent | |
| Soft-pass ST-602(a) in CI | Spec is a hard sanity relation; widening needs ADR | |
| Invent a 2019 price series in fixtures | A-2 | |

**User's choice:** skip-if-incomplete, fail-if-complete-and-violated (Recommended).

---

## Vectorized bootstrap

**Q1 — When to implement ST-406 cells?**

| Option | Description | Selected |
|--------|-------------|----------|
| Vectorized cells from the first T6.07 commit | Spec recommended; 03_MODULES pin; avoids a slow N=2000 rewrite | ✓ |
| Hourly-path prototype first, vectorize if slow | Extra code path; equivalence tests still required later | |

**User's choice:** cells from day one (Recommended).

**Q2 — Cell index grain?**

| Option | Description | Selected |
|--------|-------------|----------|
| `(horizon_month, pool_year, strategy)` with forward volumes + SG-07-mapped prices/ÖSPI | Matches ST-402 volumes and ST-401 mapping | ✓ |
| Generic `(calendar_month, pool_year)` using historical volumes | Cheaper but wrong volume/DST for the forward window | |

**User's choice:** horizon-month cells (Recommended).

---

## SG-07 / SG-08 / HMM

**Q1 — Day-mapping when months differ in length / DST?**

| Option | Description | Selected |
|--------|-------------|----------|
| SG-07 proposed rule + ADR-014 | Spec gap; deterministic | ✓ |
| Truncate/pad with NaN and skip those hours | Changes billed volume vs ST-501 | |
| Linearly interpolate extra days | Invents prices | |

**User's choice:** SG-07 + ADR-014 (Recommended).

**Q2 — P95 / CVaR method?**

| Option | Description | Selected |
|--------|-------------|----------|
| `numpy.quantile(method="linear")`; CVaR = mean of ceil(0.05 N) highest | SG-08; 03_MODULES | ✓ |
| Inclusive/exclusive percentile variants | Unspecified; would drift goldens | |

**User's choice:** SG-08 + ADR-015 (Recommended).

**Q3 — No-crisis December labels?**

| Option | Description | Selected |
|--------|-------------|----------|
| Call M5 `fit_hmm` + `december_regime` (calm wins ties) | Reuse; no new A3 parquet | ✓ |
| Persist labels in M5 (out of phase) / reimplement HMM | Scope creep or nondeterminism fork | |
| Guide 5.5 “higher-volatility wins ties” | Contradicts shipped M5 D-10 | |

**User's choice:** reuse M5 functions, calm wins (Recommended).

---

## Captions, sensitivities

**Q1 — ST-502 enforcement?**

| Option | Description | Selected |
|--------|-------------|----------|
| Shared constant + helper; tests assert substring on every S2/S3/S4 artifact | Load-bearing honesty (A-8) | ✓ |
| Manual captions in each writer | Will drift | |

**User's choice:** helper + tests (Recommended).

**Q2 — Fourth sensitivity (e.g. peak_available false as a table row)?**

| Option | Description | Selected |
|--------|-------------|----------|
| Exactly three ST-303 reruns; ST-104 is a unit-tested branch, not a sensitivity table row | A-3 / O-7 | ✓ |
| Add peak-off as a fourth block | Scope creep | |

**User's choice:** three only (Recommended).

---

## SSOT, goldens, ADRs

**Q1 — `updated_at` vs ST-405 byte identity?**

| Option | Description | Selected |
|--------|-------------|----------|
| max(input mtime) ISO-8601 UTC (SG-09) + ADR-016 | Two ssot runs identical if inputs unchanged | ✓ |
| `datetime.now()` | Breaks determinism | |
| Omit `updated_at` | Violates GV-301 columns | |

**User's choice:** SG-09 mtime (Recommended).

**Q2 — First ST-601 golden contents?**

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic hand-computable matrix in CI; real-euro replacement is human | A-2 + AGENTS §2.6 | ✓ |
| Write fixture-warehouse 2022–2024 costs as accepted goldens | Fake Austrian euros | |
| Skip ST-601 until operator warehouse | Milestone incomplete in CI | |

**User's choice:** synthetic CI golden (Recommended).

**Q3 — ADR numbers?**

| Option | Description | Selected |
|--------|-------------|----------|
| 014 SG-07, 015 SG-08, 016 SG-09 at the implementing tasks | Next free is 014 (HMM did not consume it) | ✓ |
| One bundled ADR | Harder to trace; WBS says per-gap | |

**User's choice:** three ADRs at T6.07/T6.08 (Recommended).

---

## Notes for planners

- WBS order is mandatory (align → anchors → S1 → S2/S3/S4 → annual → sensitivities; forward after annual cells exist).
- `december_regime` is consumed, not re-litigated.
- ST-602(a) on real data is operator (no 2019 in fixture).
- M7 still owns README euros; M6 checker must pass without them.
