# ADR-006: Validation gates assert over complete Vienna-local years within the ingested window

**Status:** accepted
**Date:** 2026-07-22
**Deciders:** M1 ingestion (EPRA-02)
**Related:** SPEC-01 §8 (ING-080..085), AGENTS.md T-1 (UTC storage / Vienna-local analytics), A-2 (no invented data, fail-closed), ADR-005 (`latest_complete_month`)

## Context

The M1 validation gates ING-080 (hour coverage), ING-082 (annual-mean plausibility),
ING-083 (negative-price sanity), ING-084 (load plausibility) and ING-085 (price/load
join coverage) grouped their per-year checks by **UTC calendar year**
(`ts_utc.dt.year`), and ING-083 additionally hard-coded the required years to
`(2023, 2024, 2025)`.

Running the first real 2019→latest backfill surfaced two defects this created:

1. **A phantom leading year.** The backfill window starts at `2019-01-01`
   *Europe/Vienna* = `2018-12-31 23:00 UTC`. Grouped by UTC year, that single real
   hour becomes a "2018" year with 1/8760 hours, failing ING-080 coverage and
   ING-082 (no 2018 table entry) — even though it is a completely valid hour that
   belongs to the **local** year 2019 (`2019-01-01 00:00` Vienna). This directly
   contradicts T-1: the analytic domain is Vienna-local, so year boundaries must be
   Vienna-local.

2. **Horizon-brittle assertions.** ING-083's hard-coded `(2023, 2024, 2025)` and the
   trailing partial year (the current/most-recent incomplete year — here 2024, the
   real ENTSO-E data horizon) fail purely because the data does not extend as far as
   the constants assume, not because of any data-quality problem.

Neither is a pipeline defect; both are the gates asserting over the wrong domain and
over years the ingest window does not fully cover. Two tempting "fixes" are wrong:
trimming the boundary hour **discards real data** (the analytic layer needs that
`2019-01-01 00:00` Vienna hour), and widening ranges/skipping years violates A-2.

## Decision

The M1 gates assert data quality over **complete Vienna-local calendar years within
the ingested window**:

1. **Group by Vienna-local year**, not UTC year (T-1). Convert `ts_utc` →
   `Europe/Vienna` before deriving the year for coverage, plausibility, negative-price
   and join checks. This folds the UTC-boundary hour into its correct local year; the
   phantom 2018 year disappears because the gate is now *correct*, not because data
   was hidden.

2. **Scope pass/fail to complete years.** A local year `Y` is *complete* iff the data
   range fully spans it (`min_local ≤ Y-01-01 00:00` and `max_local ≥ Y-12-31 23:00`).
   The leading local year at the window start and the trailing local year at the data
   horizon may be partial by construction; they are reported in the evidence as
   `scope="boundary"` with `ok=True` (informational) and never fail a gate.

3. **Derive year sets from the data, not constants.** ING-083 checks the intersection
   of its spec-required negative-price years and the complete years present, so it
   asserts only years the data actually covers in full (today: 2023) and automatically
   extends to 2024/2025 once those years complete — no code change needed.

Fail-closed behaviour is preserved for everything that is a real data problem:
interior complete years still fail on >24 missing hours (ING-080), out-of-band annual
means (ING-082/084), missing negatives in a complete required year (ING-083), or join
coverage <99.5% (ING-085); hourly out-of-range prices/loads (ING-081/084) are checked
on every row regardless of year.

## Consequences

- Gates align with the Vienna-local analytic contract (T-1) and are robust to any
  window start and data horizon (no year constants to maintain except the SPEC-01 §8
  reference tables, which still require an ADR to extend).
- No real data is discarded; the boundary hour is retained in raw (UTC) and attributed
  to its correct local year by the gates.
- `GateResult` / `ValidationReport` output contracts are unchanged; evidence frames
  gain a `scope` column (`complete` | `boundary`). Gate IDs and semantics for complete
  years are unchanged, so this preserves the SPEC-01 §8 output contract (A-1).
- On the real 2019→2024-01 dataset, ING-080..085 pass: complete years 2019–2023 meet
  every threshold; 2024 (data horizon) is reported as a boundary partial.

## Spec deviations

SPEC-01 §8 specifies the gates but does not pin UTC-vs-local year bucketing; this ADR
resolves that ambiguity toward the Vienna-local domain (T-1) and generalises ING-083's
illustrative `2023/2024/2025` to "spec-required years that are complete in the data".
The plausibility ranges (ING-082) and load bands (ING-084) are unchanged and still
require an ADR to widen (A-2).
