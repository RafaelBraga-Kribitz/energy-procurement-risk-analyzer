# ADR-011: One holiday-aware `is_peak_hour` drives every peak-price computation

**Status:** accepted
**Date:** 2026-07-24
**Deciders:** M3 dbt warehouse (EPRA-04)
**Related:** SPEC-02 §5 (`fct_price_hourly`/`fct_price_daily`/`fct_price_monthly`), 14_SPEC_GAPS.md SG-14, `dim_calendar` (04-03, ING-110), Charter glossary (Mon-Fri 08-20 peak definition), ST-202 (calibration anchors)

## Context

The project Charter glossary defines "peak hours" as Mon-Fri, 08:00-20:00 local
time, without mentioning public holidays. The `dim_calendar` dimension (04-03),
however, sources `is_peak_hour` verbatim from the ING-110 calendar module,
which computes it as Mon-Fri 08-20 **excluding Austrian public holidays**
(`is_holiday_at = true` days have `is_peak_hour = false` for every hour, even
on a weekday between 08:00 and 20:00).

SG-14 flags this as an open gap: which definition applies to
`price_peak_eur_mwh` in the price marts and to the ST-202 calibration anchors
that consume it? Two tempting-but-wrong resolutions exist:

1. Recompute a separate Mon-Fri-08-20 peak flag at the mart layer that
   ignores holidays, matching the Charter glossary word-for-word but
   contradicting the calendar dimension's role as the single source of
   truth for local-attribute derivation.
2. Silently treat holiday weekday hours as "peak" in some marts and
   "off-peak" in others depending on which flag a given model happens to
   reference, producing inconsistent numbers across `fct_price_hourly`,
   `fct_price_daily`, and `fct_price_monthly`.

Both would violate DM-011's principle that local-attribute derivation
(including peak-hour classification) happens exactly once, in `dim_calendar`,
and is never recomputed downstream.

## Decision

**Exactly one** `is_peak_hour` definition exists in this warehouse: the
holiday-aware flag already computed in `dim_calendar` (ING-110, Mon-Fri
08:00-20:00 local, excluding Austrian public holidays). Every downstream
consumer of "peak" — `fct_price_hourly.is_peak_hour` (passed through from the
dim_calendar join), `fct_price_daily.price_peak_eur_mwh`,
`fct_price_monthly.price_peak_eur_mwh`/`price_offpeak_eur_mwh`, and any future
ST-202 calibration anchor — filters on this one flag. No model recomputes a
Mon-Fri-08-20-ignoring-holidays alternative.

**The empty-input edge is explicit, not silently absorbed.** On a local day
with zero peak hours (a weekday public holiday), `price_peak_eur_mwh` is
`avg(price_at_eur_mwh) filter (where is_peak_hour)` over zero rows, which
DuckDB (like standard SQL) returns as `NULL` — not `0`, not the day's base
price, and not a skipped row. `fct_price_daily`/`fct_price_monthly` retain the
row for that day/month; only the peak column is `NULL`. This is verified on
real data: 2019-06-10, 2019-06-20, 2020-10-26, 2021-05-01, and 2021-05-13
(Austrian weekday holidays) all have `price_peak_eur_mwh IS NULL` while
`price_base_eur_mwh` is populated normally.

## Consequences

- Every peak-price number in this warehouse (hourly flag, daily/monthly
  means) is internally consistent — computed from the same
  `dim_calendar.is_peak_hour` — so cross-mart comparisons (e.g. DM-064's
  monthly-vs-hourly reconciliation) are never confounded by two competing
  peak definitions.
- ÖSPI (`oespi_peak`, left-joined into `fct_price_monthly`) is an
  **externally-sourced** index and may use its own peak convention that
  treats holidays differently from `is_peak_hour`. This is a genuine,
  irreducible discrepancy between an internal computed column and an
  external reference series — documented in LIMITATIONS.md §2, not resolved
  by recomputing either side. Any ST-202 calibration anchor built from
  `oespi_peak` vs. internal `price_peak_eur_mwh` ratios absorbs this level
  offset by construction (the ratio is calibrated against the actual
  co-observed pair, not against an assumed-identical definition).
- Consumers that need a NULL-safe peak-price scalar (e.g. a downstream
  chart or summary statistic) must handle the holiday-month/day NULL
  explicitly (e.g. `coalesce` to the base price, or exclude the row) —
  this ADR does not itself provide that fallback, only the correct raw
  signal.

## Spec deviations

None. SPEC-02 §5 and 14_SPEC_GAPS.md SG-14 explicitly call for "one internal
definition everywhere" and a LIMITATIONS.md note on the ÖSPI convention gap;
this ADR documents exactly that resolution and its verification, and is the
adopting decision SG-14 designates as "proposed" until now.
