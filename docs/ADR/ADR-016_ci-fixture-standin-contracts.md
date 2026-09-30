# ADR-016: CI fixture bootstrap — single-file processed stand-ins, ÖSPI CSV never written
Date: 2026-09-30  |  Status: accepted

Supersedes ADR-010 (GV-201: ADRs are append-only). Everything ADR-010 decided
still holds except where this ADR restates it. The changes are: the committed
`data/manual/oespi_monthly.csv` is never written in any mode, the processed
stand-ins follow the SPEC-03 LP-003 / SPEC-05 ST-001 single-file contracts,
and the stand-in ids come from the seed and settings, not hardcoded values.
Related: SPEC-02 §5, SPEC-03 LP-003, SPEC-05 ST-001, 14_SPEC_GAPS.md SG-06,
EN-080, ADR-014, `.planning/AUDIT-2026-09-30.md` §2.

## Context

M3's exit gate needs `dbt build` to succeed in two environments that have
fundamentally different starting data:

1. **CI** (a fresh checkout): `data/raw/` and `data/processed/` are
   empty; `data/manual/oespi_monthly.csv` is committed and therefore
   present. No network access is available (EN-070), and no
   ENTSO-E/GeoSphere credentials exist in CI.
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

1. **Synthesize, don't copy.** `scripts/bootstrap_fixture_warehouse.py`
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
   both environments:
   - Default / `--force`: synthesizes the full raw window (ENTSO-E prices
     AT/DE-LU, load, generation; GeoSphere daily; the ING-110 calendar
     spine) *and* the `data/processed` stand-ins, for a fresh/disposable
     checkout. Refuses (`return 1`, writes nothing) if `data/raw` already
     contains data and `--force` is not passed (03_MODULES.md: never
     clobber real ingested data).
   - `--processed-only`: writes *only* the two `data/processed` stand-in
     files. The consumer load is aligned to the local calendar window
     (incl. the forward-risk horizon, LP-003) read from
     `data/raw/calendar/calendar.parquet`; the strategy costs are aligned to
     the local months actually covered by raw AT prices (costs cannot exist
     for a month without a spot price, ST-001). This mode never writes
     `data/raw`/`data/manual`, so it is always safe to run against a real,
     already-populated warehouse.

   **`data/manual/oespi_monthly.csv` is never read or written by the
   generator, in any mode, `--force` included** (amended 2026-09-30,
   audit §2). It is committed, human-reconciled ÖSPI data (ING-101/102)
   present in every checkout, so dbt reads the real series in CI too;
   synthesizing index values would be invented data (A-2), and the former
   `--force` path overwrote the reconciled file when run locally.

3. **`fct_consumer_load_hourly`/`fct_procurement_cost_monthly` never fork on
   milestone status (SG-06).** Both marts are plain `select` loaders over
   `source('raw_processed', ...)` (type-pinning casts only, ADR-014).
   Whether that source is currently backed by this generator's stand-ins
   (M3-M5) or the real M4/M6 module outputs (M6+) is invisible to the
   mart SQL -- no `enabled: false`, no build-order conditional.

4. **The stand-ins honour the module output contracts exactly** (audit 2026-09-30 §2). They are written as the single files the specs
   name, with exactly the spec columns and no ING-004 provenance columns
   (they are module outputs, not raw ingests, so they do not go through
   `write_month`):
   - `data/processed/consumer_load_hourly.parquet` — `ts_utc, load_mwh`
     (SPEC-03 LP-003, SPEC-02 §5);
   - `data/processed/strategy_costs_monthly.parquet` — `year_local,
     month_local, strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh`
     (SPEC-05 ST-001, SPEC-02 §5 `fct_procurement_cost_monthly`).
   `dbt/models/sources.yml` (`raw_processed.consumer_load_hourly`,
   `raw_processed.strategy_costs_monthly`) reads exactly these files, so
   the real M4/M6 outputs replace the stand-ins with no dbt change. The
   stand-in strategy ids are read from `dbt/seeds/dim_strategy.csv` and the
   synthetic GeoSphere station id from `config/settings.yaml` (ADR-007),
   never hardcoded.

## Consequences

- CI can run `dbt build` end-to-end with zero network access and zero
  committed multi-megabyte parquet, keeping the repository lean (ADR-001
  posture): `python scripts/bootstrap_fixture_warehouse.py --force && cd dbt && dbt build`.
- Locally, `python scripts/bootstrap_fixture_warehouse.py --processed-only`
  populates just the two stand-in sources without any risk to the real
  `data/raw`/`data/manual` trees populated by M1/M2.
- Once M4/M6 land, their real module outputs write the exact same
  `data/processed/consumer_load_hourly.parquet` /
  `data/processed/strategy_costs_monthly.parquet` files this generator
  uses today; `fct_consumer_load_hourly`/`fct_procurement_cost_monthly`
  require no change. From then on `--processed-only` must not be run
  (it would overwrite the real module outputs with stand-ins).
- The synthetic price/load/generation/weather values are for CI plausibility
  only (DM-061 accepted ranges, DM-064 reconciliation-by-construction) --
  never used for any real analytical conclusion; this is the same
  "internal fixture" epistemic tag every other CI-only test fixture in
  this repo already carries.

## Spec deviations

WBS T3.06 describes the bootstrap script as building `data/raw` "from
fixtures" (implying a copy of committed parquet, the `tests/fixtures/`
convention). This ADR deviates toward run-time synthesis because a
capped, hand-authored fixture cannot satisfy the M3 exit gate's row-count
and DST tests over a full multi-year window. No other SPEC-02 contract is
affected: the synthesized data still matches the exact SPEC-01 §7 raw
column layout and the SPEC-02 §5 mart contracts byte-for-byte.
