# ADR-010: CI fixture bootstrap synthesizes data at run time; environment-aligned data/processed stand-ins feed the local build too

**Status:** accepted
**Date:** 2026-07-24
**Deciders:** M3 dbt warehouse (EPRA-04), plan 04-05
**Related:** docs/EXECUTION_BLUEPRINT/03_MODULES.md (`bootstrap_fixture_warehouse.py` scripts-table contract), SPEC-02 §5 (`fct_consumer_load_hourly`, `fct_procurement_cost_monthly`), 14_SPEC_GAPS.md SG-06 (never-disable policy), D-03..D-06 (04-CONTEXT.md)

## Context

M3's exit gate needs `dbt build` to succeed in two environments that have
fundamentally different starting data:

1. **CI** (a fresh checkout): `data/raw/`, `data/manual/`, and
   `data/processed/` are all empty. No network access is available
   (EN-070), and no ENTSO-E/GeoSphere/OESPI credentials exist in CI.
2. **Local** (this repo, right now): `data/raw/` and
   `data/manual/oespi_monthly.csv` already hold real ingested data
   (2019 -> latest, M1/M2 complete). `data/processed/` does not exist yet
   at all -- M4 (consumer profile) and M6 (procurement strategy simulator)
   have not been built, so `fct_consumer_load_hourly` and
   `fct_procurement_cost_monthly` (SPEC-02 §5) have no source data to load
   in *either* environment, and SG-06 explicitly forbids disabling them or
   forking the build by which milestone has landed.

The WBS (T3.06) describes the CI fixture bootstrap script as building
`data/raw` "from fixtures" -- i.e. copying committed sample parquet, the
same convention `tests/fixtures/entsoe/*_2024-01.parquet` already uses for
the M1 contract-drift tests (`tests/test_raw_contracts.py`, capped at 200
rows per file).

## Decision

1. **Synthesize, don't copy (D-04).** `scripts/bootstrap_fixture_warehouse.py`
   generates the CI raw window (contiguous 2022-01-01..2024-12-31,
   including the 2022-08 crisis month and both 2024 DST transition days)
   *programmatically*, seeded with a single `numpy.random.default_rng`
   constant so two runs are data-identical. It never copies a committed
   fixture parquet. This deviates from the WBS's "from fixtures" wording:
   a copied 200-row excerpt cannot satisfy the M3 exit gate's DM-062 row-
   count test (`fct_price_hourly` per `year_local` = 8760/8784 ± 24) or the
   DM-065 DST test, both of which need a full contiguous multi-year window,
   not a handful of sample rows.

2. **Two distinct, guarded invocation modes.** The same generator serves
   both environments (D-06):
   - Default / `--force`: synthesizes the full raw window (ENTSO-E prices
     AT/DE-LU, load, generation; GeoSphere daily; the ING-110 calendar
     spine) *and* the `data/processed` stand-ins, for a fresh/disposable
     checkout. Refuses (`return 1`, writes nothing) if `data/raw` or
     `data/manual/oespi_monthly.csv` already contain data and `--force`
     is not passed (03_MODULES.md: never clobber real ingested data).
   - `--processed-only`: writes *only* the `data/processed` stand-ins
     (`consumer_load_hourly`, `procurement_cost_monthly`), aligned to the
     real local ingestion window discovered from the already-committed
     `data/raw/calendar/calendar.parquet` spine. This mode never reads or
     writes `data/raw`/`data/manual` at all, so it is always safe to run
     against a real, already-populated warehouse -- this is the mode used
     for the local verification of this very plan, since this repository's
     `data/raw`/`data/manual` already hold real 2019-2024 ingested data
     that must never be overwritten by synthetic rows.

3. **`fct_consumer_load_hourly`/`fct_procurement_cost_monthly` never fork on
   milestone status (SG-06).** Both marts are plain `select` loaders over
   `source('raw_processed', ...)`. Whether that source is currently backed
   by this generator's stand-ins (M3-M5) or the real M4/M6 module outputs
   (M6+) is invisible to the mart SQL -- no `enabled: false`, no
   build-order conditional.

## Consequences

- CI can run `dbt build` end-to-end with zero network access and zero
  committed multi-megabyte parquet, keeping the repository lean (ADR-001
  posture): `python scripts/bootstrap_fixture_warehouse.py && cd dbt && dbt build`.
- Locally, `python scripts/bootstrap_fixture_warehouse.py --processed-only`
  populates just the two stand-in sources without any risk to the real
  `data/raw`/`data/manual` trees populated by M1/M2 -- verified for this
  plan's Task 3 by running that exact command against this repository's
  real `data/` root and confirming `git status` reports zero changes to
  `data/raw`/`data/manual`.
- Once M4/M6 land, their real module outputs write into the exact same
  `data/processed/consumer_load_hourly/**` /
  `data/processed/procurement_cost_monthly/**` paths this generator uses
  today; `fct_consumer_load_hourly`/`fct_procurement_cost_monthly` require
  no change.
- The synthetic OESPI/price/load/generation values are for CI plausibility
  only (DM-061 accepted ranges, DM-064 reconciliation-by-construction) --
  never used for any real analytical conclusion; this is the same
  "internal fixture" epistemic tag every other CI-only test fixture in
  this repo already carries.

## Spec deviations

WBS T3.06 describes the bootstrap script as building `data/raw` "from
fixtures" (implying a copy of committed parquet, the `tests/fixtures/`
convention). This ADR deviates toward run-time synthesis (D-04) because a
capped, hand-authored fixture cannot satisfy the M3 exit gate's row-count
and DST tests over a full multi-year window. No other SPEC-02 contract is
affected: the synthesized data still matches the exact SPEC-01 §7 raw
column layout and the SPEC-02 §5 mart contracts byte-for-byte.
