# ADR-016: SSOT updated_at is max input mtime (ISO-8601 UTC); GV-303 uses Decimal ROUND_HALF_UP (SG-09)

**Status:** accepted
**Date:** 2026-09-03
**Deciders:** M6 strategy simulator (EPRA-07), plan 07-08
**Related:** SPEC-08 GV-301, GV-303, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-09,
`.planning/phases/EPRA-07-m6-strategy-simulator/07-CONTEXT.md` D-17

Date: 2026-09-03  |  Status: accepted

## Context

GV-301 requires an `updated_at` column on `NUMERIC_SSOT.md`. Using wall-clock
`datetime.now` would make two `make ssot` runs differ even when inputs are
unchanged, breaking ST-405 / AN-705-style determinism. GV-303 says README
literals match SSOT "within rounding documented in the script"; Python's
builtin `round` is banker's rounding (ties to even), which would fail a
1.25 → 1.3 display check.

## Decision

1. `updated_at` is the maximum `st_mtime` of the input `ssot_inputs_*.parquet`
   files (and any other files the assembler actually reads), rendered as
   ISO-8601 UTC with a `Z` suffix and **second** precision
   (`YYYY-MM-DDTHH:MM:SSZ`). The assembler does not call `datetime.now`.
2. Two assemble runs with unchanged inputs produce **byte-identical**
   `NUMERIC_SSOT.md`.
3. GV-303 (implemented in T6.09) matches a README/EXEC literal that displays
   `d` decimals to an SSOT value iff
   `|literal − round_half_up(value, d)| = 0`, using
   `decimal.Decimal.quantize(..., rounding=ROUND_HALF_UP)`. Python `round`
   is not used.

## Consequences

- Operator clocks and CI machines can differ; the file still matches when
  the parquet bytes match.
- Checker unit tests pin 1.25 → 1.3 at one decimal (the banker-round trap).

## Spec deviations

none
