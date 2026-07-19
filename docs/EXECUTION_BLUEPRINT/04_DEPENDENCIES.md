# 04 — DEPENDENCY GRAPHS, CRITICAL PATH, PARALLELISM

## 4.1 Module dependency graph (import-level; arrows = "may import")

```mermaid
graph TD
    subgraph common
        CFG[common.config]
        LOG[common.logging]
        TU[common.timeutil]
        DB[common.db]
    end
    IO[ingest._io] --> CFG & TU
    FETCH[ingest._fetch] --> CFG & LOG & IO
    ENTSOE[ingest.entsoe] --> FETCH & IO & TU
    GEO[ingest.geosphere] --> FETCH & IO
    OESPI[ingest.oespi] --> CFG
    CAL[ingest.calendar] --> CFG & TU
    VAL[ingest.validate] --> CFG & TU
    PROF[consumer.profile] --> CFG & TU
    KIT[report kit: format/style/artifact writers]
    A1[analytics.descriptive] --> DB & KIT
    A2[analytics.spread] --> DB & KIT
    A3[analytics.regimes] --> DB & KIT
    A4[analytics.weather] --> DB & KIT
    SCAL[strategies.calibration] --> DB & CFG
    SRETRO[strategies.retrospective] --> SCAL & KIT
    SFWD[strategies.forward_risk] --> SRETRO & A3
    CHARTS[report.charts] --> KIT & DB
    SSOT[report.ssot / ssot_check] --> CFG
```

**Import law (enforced by review, testable via grep):** `common` imports nothing
from epra; `ingest` never imports analytics/strategies/report; `analytics` and
`strategies` never import `ingest` (marts are the only interface — DM/AN
preambles); only `strategies.forward_risk` may consume A3 regime output (as a
mart/parquet, not a Python import of the module — the arrow above is data-level).
Circular imports are structurally impossible if this law holds.

## 4.2 Milestone dependency graph

```mermaid
graph LR
    M0 --> M2 --> M1 --> M3 --> M4 --> M5 --> M6 --> M7
    TOKEN([ENTSO-E token ~day 3]) -.blocks.-> M1
    HUMAN1([ÖSPI transcription]) -.blocks.-> M2
    HUMAN2([golden approval]) -.blocks.-> M6
    HUMAN3([.pbix + screenshots + EXEC §5]) -.blocks.-> M7
```

Merge order is M2 before M1 (Charter R-1 sanction); everything downstream of M3
depends on real warehouse data and merges strictly sequentially.

## 4.3 Execution dependency graph (task level, abridged to decision-relevant edges)

```mermaid
graph TD
    T101[T1.01 io] --> T102[T1.02 fetch] --> T104[T1.04 prices]
    T103a[T1.03a fixtures] --> T104 --> T105[T1.05 load] & T106[T1.06 gen] --> T107[T1.07 contracts] --> T108[T1.08 window/CLI]
    T108 --> T109v[T1.09 gates]
    TP01[TP.01 token] --> T110[T1.10 live backfill] --> T111[T1.11 M1 PR]
    T109v --> T110
    T201[T2.01 calendar] --> T206[T2.06 M2 PR]
    T202[T2.02 discovery+ADR] --> T203[T2.03 geo ingest] --> T206
    T204[T2.04 oespi loader] --> T206
    T205[T2.05 HUMAN transcribe] --> T204
    T206 --> T111
    T111 --> T301[T3.01 sources] --> T302[T3.02 staging] --> T303[T3.03 dims] --> T304[T3.04 marts] --> T305[T3.05 tests] --> T306[T3.06 CI job3] --> T307[M3 PR]
    T307 --> T401[T4.01 weights] --> T402[T4.02 norm] --> T403[T4.03 outputs] --> T404[T4.04 goldens] --> T405[M4 PR]
    T405 --> T501[T5.01 kit] --> T502[A1] & T503[A2] & T504[A4] & T505[A3 HMM]
    T505 --> T506[A3 GARCH]
    T502 & T503 & T504 & T506 --> T507[M5 PR]
    T507 --> T601[T6.01 align] --> T602[T6.02 anchors] --> T603[S1] --> T604[S2-S4] --> T605[summary] --> T606[sens] & T607[bootstrap]
    T605 & T607 --> T608[SSOT gen] --> T609[SSOT check] --> T610[M6 PR]
    T610 --> T701[exports] --> T702[exec charts] --> T704[README/LIM]
    T703[EXEC_SUMMARY] --> T704 --> T707[release]
    T705[refresh.yml] --> T707
    T706[PowerBI HUMAN] --> T707
```

## 4.4 Critical path

`TP.01 → T1.10` joins the code path `T1.01→T1.02→T1.04→(T1.05/06)→T1.07→T1.08→T1.09`;
thereafter strictly `M2-PR → M1-PR → T3.01→…→M3-PR → T4.01→…→M4-PR → T5.01→T5.05
→M5-PR → T6.01→T6.02→T6.03→T6.04→T6.05→T6.07→T6.08→T6.09→M6-PR → T7.01→T7.02→
T7.04→T7.07`. Everything else hangs off this spine. Budget along the spine
(Charter §7): ~11.5 focused days.

**Slack exploitation:** the ~3-day token wait covers T2.* entirely plus
T1.01–T1.09 development — the critical path resumes with zero idle time at
token arrival (Phase W in [01_PHASES.md](01_PHASES.md)).

## 4.5 Parallel lanes (safe to run concurrently, different agents)

| Window | Lane A | Lane B | Lane C |
|--------|--------|--------|--------|
| Token wait | T1.01→T1.02→T1.04 chain | T2.01 calendar; T2.02→T2.03 geosphere | T2.04 loader (synthetic-CSV tests); human does T2.05 |
| Post-M3 | T4.01→… (critical) | — (M4 is short; don't split) | — |
| Post-T5.01 | T5.02 (A1) | T5.03 (A2) + T5.04 (A4) | T5.05→T5.06 (A3) |
| Post-T6.05 | T6.07 bootstrap | T6.06 sensitivities | T6.09 checker design (against SSOT draft from T6.08 skeleton) |
| M7 | T7.02 charts | T7.05 refresh.yml | T7.03 EXEC (human+agent), T7.06 (human) |

Coordination rule for parallel agents: shared files (`validate.py`, report kit)
are owned by ONE lane per window (owner listed first above); the other lane
stacks a branch on the owner's branch rather than editing concurrently.

## 4.6 Blocked / risky / API-dependent work

- **Token-blocked (only):** TP.01, T1.03b, T1.10 — and transitively every merge
  from M1-PR onward. Nothing else touches the live API.
- **Human-blocked:** T2.05 (ÖSPI), T6.10 golden approval, T7.03 §5, T7.06 (.pbix).
- **Risky (see [12_RISK_REGISTER.md](12_RISK_REGISTER.md)):** T1.02/T1.04
  (entsoe-py RawClient behavior drift — RB-9), T3.01 (dbt-duckdb schema naming —
  RB-10), T5.05 (HMM platform determinism — RB-11), T6.07 (bootstrap
  correctness — highest scientific risk), T1.10 (real-data gate surprises — R-8).
- **Non-API work to finish before the token arrives (checklist):**
  T2.01–T2.04 ✚ T1.01, T1.02, T1.03a, T1.04–T1.09 ✚ ADRs for SG-01, SG-02,
  SG-04, SG-10 ✚ optionally T3.01–T3.02 on a stacked branch against fixtures.
