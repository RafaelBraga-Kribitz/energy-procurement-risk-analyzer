# ADR-005: latest_complete_month() = min(AT prices, DE-LU prices) (adopts SG-02)
Date: 2026-07-21  |  Status: accepted

## Context
ING-042 defines "latest complete month" as "the last calendar month for
which ALL days have price data present after ingestion," computed by
`epra.ingest.entsoe:latest_complete_month()`. The spec text says "price
data" without naming a zone, but the ingestion fetches day-ahead prices for
**two** zones (AT, DE-LU per SPEC-01 §3). AN-2xx spread analytics (M5) need
both zones' data present for any month they use — using only AT's
completeness could hand downstream code a month where DE-LU is still
missing days, silently breaking the spread calculation. This is SG-02 in
`docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md`, proposed decision:
"min(latest complete month of AT prices, of DE-LU prices)."

## Decision
Adopt SG-02 literally. `latest_complete_month(settings)` returns the first
day of `min(complete_month(AT prices), complete_month(DE-LU prices))`,
where "complete" for a given zone-month means every calendar day in that
local month has at least one price row after hourly aggregation (ING-061
mean-of-quarters), per the same completeness notion ING-080's hour-coverage
gate checks. Load and generation completeness are checked by their own
gates (ING-084, ING-085) but are explicitly **not** part of this function's
definition — `latest_complete_month()` is a prices-only, two-zone
computation.

If AT and DE-LU disagree (e.g. DE-LU lags AT by a month, the exact failure
mode research Pitfall 5 warns about), the earlier (more conservative) of the
two wins, so no downstream window ever assumes data that isn't there for
both day-ahead zones.

## Consequences
- `entsoe.py`'s `latest_complete_month()` implementation (02-05) computes
  both zones' completeness from ingested raw parquet, takes the min, and
  returns its first-of-month `date`.
- Downstream consumers (dbt freshness checks, SPEC-05 forward window start)
  get a single unambiguous window end that is always safe for AT/DE-LU
  spread analysis.
- If DE-LU ingestion lags AT significantly, the effective window shrinks
  accordingly — this is the intended conservative behavior, not a bug; it
  surfaces as a smaller backfill range rather than a silent gap in spread
  inputs.

## Spec deviations
ING-042 (zone left unspecified in the literal text). Output contract
preserved: `latest_complete_month()` keeps its existing public signature
(`settings: Settings -> date`) and "computed, not assumed" guarantee; only
the zone-selection rule is made explicit. Cross-reference:
`docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-02, now `adopted (ADR-005)`.
