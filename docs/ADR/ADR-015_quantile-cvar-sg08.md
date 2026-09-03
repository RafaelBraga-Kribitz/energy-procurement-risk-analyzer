# ADR-015: Forward P-quantiles use numpy linear interpolation; CVaR95 is the mean of the ceil(0.05 N) highest paths (SG-08)

**Status:** accepted
**Date:** 2026-09-03
**Deciders:** M6 strategy simulator (EPRA-07), plan 07-07
**Related:** SPEC-05 ST-403, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-08,
`.planning/phases/EPRA-07-m6-strategy-simulator/07-CONTEXT.md` D-11

Date: 2026-09-03  |  Status: accepted

## Context

ST-403 requires mean, std, P5, P50, P95, and CVaR95 (mean of the worst 5% =
highest costs) per strategy. NumPy offers several quantile interpolation
methods; "worst 5%" is ambiguous between a quantile cutoff and a count of
paths. SG-08 proposed a pin so CI goldens and operator reruns cannot drift.

## Decision

1. P5 / P50 / P95 are `numpy.quantile(costs, q, method="linear")` with
   `q` in `{0.05, 0.50, 0.95}`.
2. CVaR95 is the mean of the `k` highest annual path costs, where
   `k = ceil(0.05 * N)` and `N` is the number of paths (`N=2000` → `k=100`).
   It is **not** a quantile and is **not** the mean of paths above P95 unless
   those two sets coincide.
3. Both pins live only in `epra.strategies.forward_risk.summarize`.
   Simulation code does not reimplement them.

## Consequences

- Closed-form unit tests can assert exact P-quantiles and CVaR on a crafted
  vector without depending on pandas `quantile`.
- Changing interpolation method or CVaR count requires a new ADR and ST-601
  golden regeneration (EN-072).

## Spec deviations

none
