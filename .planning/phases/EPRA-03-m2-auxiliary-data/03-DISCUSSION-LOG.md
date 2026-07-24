# Phase 3: M2 Auxiliary Data - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-22
**Phase:** 3-M2 Auxiliary Data
**Areas discussed:** ÖSPI series & fallback, Real-data boundary, ÖSPI transcription, Calendar horizon

Area selection (multiSelect): all four offered areas selected. Framing noted the phase is heavily spec-locked (SPEC-01 §§9–11); unpicked areas would have defaulted to spec.

---

## ÖSPI series & fallback (ING-102 / ING-104)

**Q1 — series choice**

| Option | Description | Selected |
|--------|-------------|----------|
| Current-method if it covers 2019→present | Spec preference (ING-102); fall back to legacy only if coverage insufficient; confirmed at transcription, ADR-recorded; no splicing | ✓ |
| Long-running / legacy series | Force legacy regardless of current-method coverage | |
| Decide at transcription | Leave fully open until the AEA source is examined | |

**Q2 — Base/Peak**

| Option | Description | Selected |
|--------|-------------|----------|
| Base+Peak, Base-only fallback | Target both; drop to peak_available:false per ING-104 if Peak missing; record in ADR + LIMITATIONS | ✓ |
| Base-only from the start | Commit to Base-only now | |

**User's choice:** Current-method (with legacy fallback) + Base+Peak with ING-104 fallback.
**Notes:** Feeds SPEC-05 strategy formulas; final series pick confirmed against the real publication before transcription.

---

## Real-data boundary & phase close

**Q1 — close definition**

| Option | Description | Selected |
|--------|-------------|----------|
| M1 pattern (fixtures green in CI) | Loaders + ING-094/103/111 green on fixtures/synthetic in CI; live GeoSphere + real ÖSPI as committed checkpoints; consistent with ADR-006/EN-070 | ✓ |
| Hold until real-data gates pass now | Block phase close until gates green on real GeoSphere + real reconciled ÖSPI this session | |

**Q2 — GeoSphere live timing (no auth, ING-093)**

| Option | Description | Selected |
|--------|-------------|----------|
| Attempt live in-phase, fixture fallback | Try discover_station()+real pull live (no token); fall back to committed GeoJSON fixture + human checkpoint if network blocked | ✓ |
| Defer live, build on GeoJSON fixture | Treat like ENTSO-E in M1; live pull as human checkpoint only | |

**User's choice:** M1 pattern for close; GeoSphere attempts live in-phase with fixture fallback.
**Notes:** CI stays network-free and deterministic either way.

---

## ÖSPI transcription (ING-101 double-entry)

**Q1 — entry ownership**

| Option | Description | Selected |
|--------|-------------|----------|
| Agent drafts entry1, you do entry2 | Fastest independent double-entry if source is machine-readable | |
| You do both, separate sessions | Spec's literal human procedure; most robust against a bad source read (A-2) | ✓ |
| Two agent sessions | Agent-only transcription with reconcile as the check | |

**Q2 — source availability**

| Option | Description | Selected |
|--------|-------------|----------|
| Have URL, machine-readable | Source URL supplied, HTML/clean PDF | |
| Have it, but PDF/scan | Have publication but layout-heavy/scanned | |
| Don't have it yet | Source not located; locating it is part of the checkpoint | ✓ |

**User's choice:** Human transcribes both entries in separate sessions; source not yet located.
**Notes:** Agent locates/verifies the AEA strompreisindex publication + drafts the methodology ADR first (T2.04); human confirms source, then transcribes (T2.05). Loader/gates ship against a synthetic CSV.

---

## Calendar horizon (SG-15 / ING-110)

**Q1 — horizon_months**

| Option | Description | Selected |
|--------|-------------|----------|
| 12 months + round to year end | Cover the 12-mo forward-risk window, extend to Dec 31 of that year | |
| Exactly 12 months | Minimal spine, partial trailing year risk | |
| 18 months | 6-month cushion beyond the 12-mo sim | ✓ |

**Q2 — bootstrap --end**

| Option | Description | Selected |
|--------|-------------|----------|
| 2027-12-31 | Fixed WBS AC example value | |
| Compute dynamically from M1 | Wire latest_complete_month() as default; fixed --end only in tests | ✓ |

**User's choice:** horizon = 18 months; compute --end dynamically from M1.
**Notes:** M1 is complete, so latest_complete_month() is the default; fixed --end (e.g. 2027-12-31) reserved for tests. is_peak_hour from timeutil (never re-implemented); holidays subdiv='6' (SG-10).

---

## Claude's Discretion

- ADR numbering: new GeoSphere-station and ÖSPI-methodology ADRs take ADR-007 and ADR-008 (WBS "ADR-003/004" labels collide with existing M1 ADRs).
- Module decomposition, helper naming, fixture byte content, synthetic-CSV values, validation-report layout (W-2).
- GeoSphere station tie-break beyond ING-091's "Graz, longest record, prefer Graz Universität".

## Deferred Ideas

- dim_calendar weather join (season/hdd_18/cdd_22) → M3/Phase 4.
- Canonical hourly aggregation → M3/Phase 4.
- peak_available-dependent strategy formulas → M6/Phase 7.
