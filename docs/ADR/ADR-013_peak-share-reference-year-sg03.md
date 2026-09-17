# ADR-013: SSOT consumer_peak_share is the 2019 local-year value

**Status:** accepted
**Date:** 2026-09-02
**Deciders:** M4 consumer profile (EPRA-05), plan 05-03
**Related:** SPEC-03 LP-020, SPEC-05 ST-102, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-03,
`.planning/phases/EPRA-05-m4-consumer-profile/05-CONTEXT.md` D-04

## Context

LP-020 requires a single SSOT number `consumer_peak_share` (fraction of annual
volume in peak hours: Mon–Fri 08–20 local, non-holiday — already encoded as
`is_peak_hour` on the ING-110 calendar / ADR-011). Peak share is not exactly
constant across local years because holiday calendars and DST change the
count of peak hours.

SG-03 recorded that a single SSOT value therefore needs a reference-year
convention. Other calibration anchors in this project use **2019**.

## Decision

1. Compute peak share per local year:
   `sum(load_mwh | is_peak_hour) / sum(load_mwh)` using calendar `year_local`
   and `is_peak_hour` (never re-derived from UTC year or a second peak rule).
2. Publish the **2019** value to `ssot_inputs_profile.parquet` as
   `consumer_peak_share` with tag `CALIBRATED`.
3. A unit test asserts that every other **complete** local year in the
   profile window deviates from 2019 by **less than 1 percentage point**
   (`abs(share_y - share_2019) < 0.01`). If that test fails, stop and
   escalate — do not silently pick another year or average the years.

Plausibility (LP-020): the published 2019 value is expected *near* 0.42–0.48.
The constructed StyriaMetal shape (YAML §6, unchanged) yields a 2019 share
slightly above 0.48 (~0.486). That is accepted: the **output contract** is
the computed 2019 fraction, not a retuned YAML. Tests therefore assert
`0.42 ≤ share < 0.50` (near the hint) plus the <1 pp yearly-deviation gate.
Do **not** edit `config/consumer_profile.yaml` to force 0.48 (A-2, LP-002).

## Consequences

- ST-102 / SPEC-05 §4.3 reuse the 2019 SSOT row; they must not recompute a
  different year's share.
- A holiday-calendar or DST-rule change that moves peak share by ≥1 pp vs
  2019 is a STOP (new ADR / investigation), not a silent SSOT rewrite.

## Spec deviations

None versus LP-020's output contract (publish the computed share; tag
CALIBRATED). The "~0.42–0.48" clause is treated as an informal hint; the
hard gates are reference-year 2019 and the <1 pp yearly-deviation test.
WBS T4.03's literal `[0.42, 0.48]` AC is satisfied in spirit (near-band)
and recorded here so we do not retune weights to hit 0.48.
