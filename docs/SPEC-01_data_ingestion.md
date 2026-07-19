# SPEC-01 — Data Ingestion

Governs everything between an external source and `data/raw/`. Requirement IDs: `ING-xxx`.
Any deviation forced by external reality (API change, renamed field) requires an ADR and a
parser adaptation that PRESERVES the output contracts in §7.

---

## 1. General ingestion rules (apply to every source)

- ING-001: All ingestion code lives in `src/epra/ingest/`, one module per source:
  `entsoe.py`, `geosphere.py`, `oespi.py`, `calendar.py`.
- ING-002: Every ingestor is a CLI entrypoint invokable via
  `python -m epra.ingest.<source> --start YYYY-MM-DD --end YYYY-MM-DD` and via Makefile.
- ING-003: Idempotency. Re-running an ingestor for an already-ingested window must
  produce byte-identical parquet output (same input ⇒ same output) and must not duplicate
  rows. Implementation: write one parquet file per source per calendar month, path pattern
  in §7; a re-run overwrites the month file atomically (write temp file, then rename).
- ING-004: Raw means raw. `data/raw/` parquet contains values exactly as parsed from the
  source (after XML/JSON decoding), with only these additions: `ingested_at_utc`
  (ISO-8601), `source` (string), `request_hash` (sha256 of the request URL minus token).
  No unit conversion, no gap filling, no dedup logic beyond ING-003 in raw.
- ING-005: All timestamps in raw and staging are **UTC**, column name `ts_utc`,
  parquet type TIMESTAMP (µs, UTC). Local-time columns exist ONLY in dbt marts (SPEC-02).
- ING-006: HTTP behavior: `requests` with `tenacity` retry — retry on 429, 5xx, and
  connection errors; exponential backoff `wait_exponential(multiplier=2, min=2, max=120)`;
  `stop_after_attempt(6)`. On 400/401/403: do NOT retry; raise with the response body in
  the error message.
- ING-007: Politeness: ≥ 0.5 s sleep between consecutive ENTSO-E requests; ≥ 0.2 s for
  GeoSphere. Never parallelize requests to the same host.
- ING-008: Logging: every request logs `INFO source=<s> window=<start>..<end> status=<code>
  rows=<n> elapsed_ms=<t>`. Secrets never appear in logs (assert token not in logged URL).
- ING-009: Response caching: raw HTTP responses (XML/JSON) are cached under
  `data/cache/<source>/<sha256-of-url-minus-token>.bin`. If a cache file exists AND the
  requested window ends more than 7 days in the past, the ingestor uses the cache and
  skips the network. `--no-cache` flag bypasses. `data/cache/` is gitignored.
- ING-010: `data/raw/` and `data/cache/` are gitignored. Reproducibility comes from code +
  the ability to re-pull; the repo does not version bulk data. The ONLY committed data files
  are the hand-curated CSVs in `data/manual/` (§10).

---

## 2. ENTSO-E: registration and authentication

- ING-020: Registration procedure (human task, day 0):
  1. Create a free account at `https://transparency.entsoe.eu`.
  2. Request REST API access per the current ENTSO-E documentation (historically: email
     `transparency@entsoe.eu` with subject "Restful API access" from the registered
     address; check the current help page — the process occasionally changes).
  3. Generate the security token under account settings.
- ING-021: Token is provided ONLY via environment variable `ENTSOE_API_TOKEN` (locally via
  `.env`, in CI via GitHub Actions secret). Code must fail fast with a clear message if unset.
- ING-022: Client library: use `entsoe-py` (`EntsoePandasClient`), version pinned in
  SPEC-07 §3. Wrap it — never call it from analytics code. If `entsoe-py` cannot serve a
  need, fall back to raw REST per Appendix A and write an ADR.

## 3. ENTSO-E: what to fetch

| Dataset | entsoe-py call | Underlying document | Domain(s) | Native resolution | Window |
|---------|----------------|--------------------|-----------|-------------------|--------|
| AT day-ahead prices | `query_day_ahead_prices('AT', start, end)` | A44 | `10YAT-APG------L` | PT60M (PT15M after SDAC 15-min switch) | 2019-01-01 → latest complete month |
| DE-LU day-ahead prices | `query_day_ahead_prices('DE_LU', start, end)` | A44 | `10Y1001A1001A82H` | same | same |
| AT actual load | `query_load('AT', start, end)` | A65 / processType A16 | `10YAT-APG------L` | PT15M | same |
| AT generation per type | `query_generation('AT', start, end, psr_type=None)` | A75 / processType A16 | `10YAT-APG------L` | PT15M or PT60M | same |

- ING-030: Chunking: request in ≤ 90-day windows regardless of library capabilities.
  Iterate months; group into quarters for efficiency if trivial.
- ING-031: Timezone handling with entsoe-py: pass `pd.Timestamp` with `tz='Europe/Vienna'`
  for start/end (library requirement), but convert the returned index to UTC before
  persisting (ING-005).
- ING-032: Generation per type returns a column per PSR type (possibly multi-level with
  Actual Aggregated / Actual Consumption). Persist in LONG format:
  `ts_utc, psr_type (code), psr_name, kind ('aggregated'|'consumption'), value_mw`.
  PSR code→name mapping table is Appendix B; store BOTH code and mapped name.

## 4. ENTSO-E: window management & incremental refresh

- ING-040: Full backfill command `make backfill` ingests 2019-01-01 → end of the last
  complete month, all four datasets.
- ING-041: Incremental command `make ingest` ingests a 45-day lookback from today
  (re-writing the affected month files), because ENTSO-E occasionally restates recent data.
- ING-042: "Latest complete month" = the last calendar month for which ALL days have
  price data present after ingestion. Computed, not assumed; exposed by
  `epra.ingest.entsoe:latest_complete_month()` and used by downstream modules.

## 5. Units and currencies

- ING-050: Prices: EUR/MWh as delivered by the API. Assert currency == EUR and unit ==
  MWH when parsing raw XML (Appendix A path); entsoe-py path: document the assumption in
  a test against one known fixture value.
- ING-051: Load and generation: MW (average power over the MTU). Energy per MTU =
  MW × (minutes/60) MWh — this conversion happens in dbt staging, NOT in ingestion.

## 6. Resolution handling (CRITICAL — R-2, R-3)

- ING-060: Every persisted raw price row carries `resolution` ('PT60M' or 'PT15M') as
  reported. If entsoe-py does not expose it, infer from timestamp spacing per contiguous
  day and store the inferred value; add a test that inference matches spacing.
- ING-061: The canonical analytical resolution is HOURLY. 15-min prices are aggregated to
  hourly by arithmetic mean of the 4 quarters (in staging, SPEC-02). 15-min load/generation
  aggregate to hourly by arithmetic mean of MW.
- ING-062: A dedicated pytest fixture must contain a synthetic 15-min day and assert the
  hourly aggregation is the mean of quarters (guards against sum/mean confusion).
- ING-063: Curve type A03 (repeated points omitted): when parsing raw XML (Appendix A),
  missing positions within a period inherit the last present value (forward fill within
  the period ONLY). Count of filled points per month is logged and stored in the ingestion
  report (§8). entsoe-py handles this internally in current versions — the validation
  suite (§8) still checks hour coverage independently.

## 7. Output contracts (what raw parquet must look like)

Path pattern: `data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet`

| Dataset dir | Columns (exact names, types) |
|-------------|------------------------------|
| `entsoe_prices_at` | `ts_utc` timestamp, `price_eur_mwh` double, `resolution` varchar, `zone` varchar ('AT'), + ING-004 columns |
| `entsoe_prices_delu` | same, `zone` = 'DE_LU' |
| `entsoe_load_at` | `ts_utc`, `load_mw` double, `resolution`, `zone`, + ING-004 |
| `entsoe_gen_at` | `ts_utc`, `psr_type` varchar, `psr_name` varchar, `kind` varchar, `value_mw` double, `resolution`, `zone`, + ING-004 |
| `geosphere_graz_daily` | `date` date, `station_id` varchar, `tl_mittel_c` double, `parameter_raw` json/varchar, + ING-004 |
| (committed, not parquet) `data/manual/oespi_monthly.csv` | see §10 |

- ING-070: Contract tests: `tests/test_raw_contracts.py` opens one file per dataset and
  asserts exact column names and dtypes. These tests run against a small committed fixture
  set in `tests/fixtures/` (generated once from real pulls, ≤ 200 rows each) so CI does not
  need network access.

## 8. ENTSO-E validation gates (run after every ingest; `make validate-ingest`)

Implemented in `src/epra/ingest/validate.py`, results written to
`reports/ingestion/validation_<run-date>.md`.

- ING-080 Hour coverage: for each zone-year, expected hours = 8760 (8784 leap). After
  hourly aggregation, missing hours per year must be ≤ 24; each missing hour is listed.
  DST correctness check: the count of DISTINCT local (Europe/Vienna) clock times on the
  last Sunday of March must be 23 hours and October 25 hours.
- ING-081 Price plausibility (hourly AT): global bounds −500 ≤ price ≤ 5000 EUR/MWh
  (values outside → hard fail = investigate, don't clip).
- ING-082 Annual mean plausibility gates (AT day-ahead, hourly mean per calendar year):

  | Year | Acceptable mean range (EUR/MWh) |
  |------|-------------------------------|
  | 2019 | 25 – 55 |
  | 2020 | 20 – 50 |
  | 2021 | 80 – 130 |
  | 2022 | 200 – 320 |
  | 2023 | 70 – 140 |
  | 2024 | 50 – 110 |
  | 2025 | 40 – 140 |

  Out-of-range ⇒ gate FAILS ⇒ stop, inspect parsing (most likely unit or timezone bug),
  write findings into the validation report. Do NOT widen the gate without an ADR.
- ING-083 Negative prices: at least one negative hourly price must exist in each of
  2023, 2024, 2025 for AT. Zero negatives across all years ⇒ parser bug (fail).
- ING-084 Load plausibility: AT hourly load within 3000–13000 MW; annual mean within
  6000–9000 MW.
- ING-085 Cross-dataset: for every hour with a price there must be a load value (join
  coverage ≥ 99.5% per year).

## 9. GeoSphere Austria (daily temperature, Graz)

- ING-090: API base: `https://dataset.api.hub.geosphere.at/v1`. Target dataset: daily
  climate station data, dataset id `klima-v2-1d` (verify at build time, see ING-091).
  Endpoint pattern:
  `GET /station/historical/klima-v2-1d?parameters=tl_mittel&station_ids=<ID>&start=<YYYY-MM-DD>&end=<YYYY-MM-DD>&output_format=geojson`
- ING-091: Discovery procedure (MANDATORY first step, do not skip): fetch
  `/station/historical/klima-v2-1d/metadata`, list stations, select the station whose name
  matches `Graz` with the longest record (prefer "Graz Universität"). Record the chosen
  `station_id`, name, lat/lon in `config/settings.yaml` under `geosphere:` and in an ADR.
  If dataset id `klima-v2-1d` does not exist, list datasets via `/datasets` and choose the
  daily station climate dataset; ADR the substitution.
- ING-092: Parameter: daily mean air temperature (`tl_mittel`, °C). If the parameter code
  differs, resolve via the metadata endpoint; ADR.
- ING-093: Window: 2019-01-01 → latest. No auth. Cache per ING-009.
- ING-094: Validation gates: coverage ≥ 99% of days; −30 ≤ tl_mittel ≤ 42 °C; July mean ∈
  [15, 30] °C; January mean ∈ [−10, 8] °C.

## 10. ÖSPI (manual, double-entry validated)

The ÖSPI monthly values are published by the Austrian Energy Agency
(`https://www.energyagency.at/fakten/strompreisindex`, historically with a PDF of monthly
values, Base and Peak, index base 2006 = 100). There is no machine API ⇒ hand-curated CSV.

- ING-100: File: `data/manual/oespi_monthly.csv` (committed to git). Exact schema:

  ```csv
  month,oespi_base,oespi_peak,source_url,retrieved_at
  2019-01,104.06,98.32,https://…,2026-07-20
  ```

  `month` = `YYYY-MM` string; `oespi_base`/`oespi_peak` = decimal with dot separator;
  values ≥ 2019-01 through the latest published month. (Numbers above are format examples,
  NOT real values — transcribe real ones.)
- ING-101: Double-entry procedure: (1) transcribe the full series into
  `oespi_monthly_entry1.csv`; (2) in a separate session (or by a second agent), transcribe
  again into `oespi_monthly_entry2.csv`; (3) `scripts/oespi_reconcile.py` diffs them — any
  mismatch is resolved by re-reading the source; (4) the reconciled file becomes
  `oespi_monthly.csv`; entry1/entry2 are deleted. The reconcile script and its passing run
  are referenced in the M2 gate.
- ING-102: Note on methodology break: the Energy Agency revised the ÖSPI methodology
  (old vs. new method pages exist). Use ONE consistent series; prefer the current-method
  series if it covers 2019→present, otherwise use the long-running series and record the
  choice + source URLs in an ADR. Do not splice two methods without an ADR.
- ING-103: Validation gates: continuous months, no gaps; both columns positive; the
  2022 peak of the series must be ≥ 3× its 2019 mean (crisis visibility check); month-over-
  month change never exceeds ±60%.
- ING-104: If monthly PEAK values turn out to be unavailable for part of the window,
  fall back to Base-only mode: SPEC-05 formulas define `peak_available: false` behavior.
  Record in ADR + LIMITATIONS.

## 11. Calendar

- ING-110: `src/epra/ingest/calendar.py` generates `data/raw/calendar/calendar.parquet`
  with one row per hour UTC 2019-01-01 → end of forward-risk window:
  `ts_utc, date_local (Europe/Vienna), hour_local, dow_local (0=Mon), is_weekend,
  is_holiday_at (holidays package, subdiv='6' for Styria), is_peak_hour
  (Mon–Fri and 8 ≤ hour_local < 20 and not holiday), year_local, month_local`.
- ING-111: Test: 2024 Austrian national holidays count per the `holidays` package matches
  expectation (13 nationwide incl. regional handling documented); Jan 1, May 1, Dec 25
  always holidays; peak-hour definition tested on a known Monday and a known Sunday.

---

## Appendix A — Raw ENTSO-E REST fallback (use only if entsoe-py fails; ADR required)

Base: `GET https://web-api.tp.entsoe.eu/api`
Common params: `securityToken`, `periodStart`/`periodEnd` in `yyyyMMddHHmm` **UTC**.

| Dataset | Params |
|---------|--------|
| Day-ahead prices | `documentType=A44&in_Domain=<EIC>&out_Domain=<EIC>` |
| Actual load | `documentType=A65&processType=A16&outBiddingZone_Domain=<EIC>` |
| Generation per type | `documentType=A75&processType=A16&in_Domain=<EIC>` (+ optional `psrType`) |

EIC codes: AT = `10YAT-APG------L`; DE-LU = `10Y1001A1001A82H`.

Response: XML `Publication_MarketDocument` / `GL_MarketDocument`. Parse every
`TimeSeries` → `Period`: read `timeInterval/start`, `resolution` (e.g. `PT60M`, `PT15M`),
then each `Point` with `position` (1-based) and `price.amount` or `quantity`.
`ts_utc = period_start + (position − 1) × resolution`. Apply ING-063 for omitted positions
when `curveType == 'A03'`. Reject the response if `currency_Unit.name != 'EUR'` or
`price_Measure_Unit.name != 'MWH'` (prices). A `Acknowledgement_MarketDocument` response
means "no data / bad request" — log its `Reason/text` and treat per context (no data for a
future window is OK; for a past window it's a failure).

## Appendix B — PSR type codes (persist code AND name)

| Code | Name |
|------|------|
| B01 | Biomass |
| B02 | Fossil Brown coal/Lignite |
| B03 | Fossil Coal-derived gas |
| B04 | Fossil Gas |
| B05 | Fossil Hard coal |
| B06 | Fossil Oil |
| B09 | Geothermal |
| B10 | Hydro Pumped Storage |
| B11 | Hydro Run-of-river and poundage |
| B12 | Hydro Water Reservoir |
| B13 | Marine |
| B14 | Nuclear |
| B15 | Other renewable |
| B16 | Solar |
| B17 | Waste |
| B18 | Wind Offshore |
| B19 | Wind Onshore |
| B20 | Other |

Unknown codes: keep the code, set `psr_name = 'UNKNOWN(<code>)'`, log WARN, never drop rows.
