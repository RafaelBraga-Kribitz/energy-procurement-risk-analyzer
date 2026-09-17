# ADR-014: ST-401 day mapping is (day-of-month index, hour_local) with weekend-type overflow (SG-07)

**Status:** accepted
**Date:** 2026-09-03
**Deciders:** M6 strategy simulator (EPRA-07), plan 07-07
**Related:** SPEC-05 ST-401 step 3, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-07,
`.planning/phases/EPRA-07-m6-strategy-simulator/07-CONTEXT.md` D-10

Date: 2026-09-03  |  Status: accepted

## Context

ST-401 step 3 maps a drawn historical month's hourly prices onto a target
horizon month by "(day-of-month index, hour_local)". When the target month is
longer than the drawn month, the spec says to reuse the drawn month's "last
same-weekday-type day". DST mismatches are "local-hour alignment with forward
fill for the missing hour". SG-07 recorded that this is not a unique algorithm
until those phrases are pinned.

## Decision

1. Map each **target** local hour independently. Do not assume 24 hours/day
   (`dim_calendar` already has 23- and 25-hour local days).
2. Primary key is `(day-of-month index, hour_local)` into the drawn month.
3. If target day-of-month `d` exceeds the drawn month's length, reuse the drawn
   month's **last calendar day whose `is_weekend` equals the target day's
   `is_weekend`** (weekday-type; holidays are not a third class unless already
   encoded in `is_weekend`).
4. DST-missing hour on the **drawn** side (target has a local hour the drawn
   day lacks): forward-fill from the previous mapped local hour in target
   time order. Never invent a price from another month.
5. DST-extra hour on the **target** side: reuse the drawn day's 02:00 local
   price (first 02:00 if the drawn day is not a 25-hour day; occurrence-aligned
   if both sides have two 02:00 rows).
6. The mapper is deterministic given the two frames. Documented on
   `epra.strategies.forward_risk.map_month`.

## Consequences

- Cost cells (ST-406) can map any pool year of calendar month `c` onto any
  horizon month with the same `c` without resampling clocks in pandas.
- A different overflow rule (ISO weekday, holiday class, or "repeat last
  calendar day regardless of weekend") needs a new ADR.

## Spec deviations

none
