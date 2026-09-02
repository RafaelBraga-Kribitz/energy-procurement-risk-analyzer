# ADR-012: August maintenance week is the first Monday on or after 1 August through the following Sunday

**Status:** accepted
**Date:** 2026-09-02
**Deciders:** M4 consumer profile (EPRA-05), plan 05-01
**Related:** SPEC-03 §3.3, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-04, `.planning/phases/EPRA-05-m4-consumer-profile/05-CONTEXT.md` D-02

## Context

SPEC-03 §3.3 defines the annual maintenance window as "the FIRST full Mon–Sun
week of August (the first Monday of August through the following Sunday)" with
`maintenance_factor` applied on top of the day's weekday/weekend shape
(maintenance does **not** switch `day_type` to shutdown).

That wording is ambiguous when 1 August is itself a Monday: is the "first full
week" 1–7 August, or does "full week within August" mean the week starting
Monday 8 August? SG-04 recorded the gap; this ADR adopts the proposed
resolution so T4.01 does not silently pick an edge convention.

## Decision

1. Let `m` be the first Monday with `m ≥ 1 August` of the local year
   (`m = 1 August` when that date is a Monday).
2. The maintenance window is the closed interval `[m, m+6]` (Monday through
   the following Sunday).
3. Because `m ≤ 7 August` always, `m+6 ≤ 13 August`, so the window always
   lies entirely inside August.

**Edge check (mandatory test):** 1 August 2022 was a Monday → maintenance is
**2022-08-01 through 2022-08-07**.

## Consequences

- Weight-engine tests pin 2022-08-01..07 as maintenance and 2022-08-08 as
  not.
- A future ISO-week or "first Monday *after* the 1st" reading would require
  a new ADR and a golden regeneration (EN-072).
- Christmas shutdown remains a separate window (Dec 24–Jan 1) and continues
  to override `day_type` to `shutdown`.

## Spec deviations

None versus SPEC-03's output contract. This ADR only binds the SG-04 edge
that the spec left open. YAML `maintenance.rule: first_full_week_august` is
unchanged.
