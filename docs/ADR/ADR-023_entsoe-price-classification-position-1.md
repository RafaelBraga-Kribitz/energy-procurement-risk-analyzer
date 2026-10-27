# ADR-023: Keep only the price TimeSeries with classificationSequence position 1 (SDAC day-ahead)
Date: 2026-10-28  |  Status: accepted

## Context
The first real-data run (2026-10-27) surfaced a defect in the price path.
An ENTSO-E A44 `Publication_MarketDocument` for AT and DE-LU contains TWO
`TimeSeries` per delivery period. They differ only in
`<classificationSequence_AttributeInstanceComponent.position>` (1 or 2):

- Position 1 is the SDAC day-ahead price. Its resolution is PT60M until
  2025-09 and PT15M from 2025-10 (the 15-minute MTU go-live).
- Position 2 is a second PT15M series with different prices (it is not the
  SDAC day-ahead price).

Evidence (data/cache/entsoe, 170 of 256 cached responses carry the element):
AT, 2022-08-15 00:00 UTC has a PT60M row of 375.03 EUR/MWh and a PT15M row of
484.90 EUR/MWh in `data/raw/entsoe_prices_at`. `src/epra/ingest/entsoe.py`
kept both series, so raw had two rows per `ts_utc` (ADR-015 keeps rows that
differ in value). Downstream effects:

1. dbt staging (`stg_prices_at_native`, `stg_prices_delu_native`) dedups with
   `row_number() over (partition by ts_utc order by ingested_at_utc desc)`.
   `ingested_at_utc` ties inside one month file, so the winner was arbitrary
   (violates A-4).
2. `stg_prices_*_hourly` averaged a mixture of both series.
3. `predup_count_prices` (DM-020) warned in all 186 zone-months.
4. ING-082 2022 annual mean (264.41) did not equal the warehouse mean (264.02).

## Decision
- `parse_publication_xml` keeps a price `TimeSeries` only when its
  `classificationSequence_AttributeInstanceComponent.position` equals 1.
  Series with another position are dropped at the parse boundary, and the
  count of dropped series is logged at INFO (never silent).
- If a `TimeSeries` has no position element, it is kept as-is (older
  documents and the synthetic fixtures do not carry it). This is the
  behaviour before this ADR.
- Conservative guard for missing positions: if a document contains more than
  one `TimeSeries` for the same zone WITHOUT a position element, and their
  periods overlap with different values, parsing raises `ContractError`
  (fail loudly). We do not guess which series is the SDAC price (A-2).
  Overlapping series with identical values stay allowed (ADR-015 handles
  refetch duplicates).
- The dbt native staging dedup gets a deterministic tie-breaker after
  `ingested_at_utc desc`: `resolution, price_eur_mwh`. The result no longer
  depends on row order (A-4; DM-020 stays the only place where duplicates are
  resolved).
- The raw price parquet is rebuilt from the cached responses with the fixed
  parser (ING-009 cache hits, no new network need for settled windows).

## Consequences
- Raw has one price row per `ts_utc` per zone after the rebuild. The 15-minute
  period from 2025-10 stays PT15M in raw (position 1); aggregation to hourly
  stays in dbt staging (ING-061/062, T-2).
- All price-derived numbers change (annual means, S1..S3 costs, wrong-strategy
  cost, forward risk). Docs take the new numbers from `reports/NUMERIC_SSOT.md`
  only (A-6).
- `predup_count_prices` is expected to stay silent. If it warns again, the
  parser or ENTSO-E changed and the cause must be found (A-2).
- ADR-015 is not superseded: it still governs refetch overlap. This ADR only
  narrows which `TimeSeries` enter the parsed frame.
- Load (A65) and generation (A75) parsers are not affected.

## Spec deviations
None. SPEC-01 does not define the classificationSequence element. The change
serves ING-003 (idempotency) and ING-004 (one source fact per row in raw),
and ING-080..085 (annual mean reconciliation). DM-020 (dedup rule) is
extended with a tie-breaker only.
