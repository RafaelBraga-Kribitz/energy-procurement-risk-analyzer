# 02 — WORK BREAKDOWN STRUCTURE

Every task ≈ one coding session. Conventions, labels, and the **global DoR/DoD**
that every task inherits are in [00_MASTER_PLAN.md](00_MASTER_PLAN.md) §0.5–0.7;
task cards list only *deltas*. Module-level behavior contracts live in
[03_MODULES.md](03_MODULES.md); how-to detail in
[05_IMPLEMENTATION_GUIDES.md](05_IMPLEMENTATION_GUIDES.md). "AC" = acceptance
criteria (objective, runnable).

---

## TP — Preparatory / operations tasks

#### TP.01 — Activate ENTSO-E token `[HUMAN]` `[CP]`
- **Objective:** working `ENTSOE_API_TOKEN` in local `.env` and (later) GitHub secret.
- **Traces:** ING-020, ING-021, EN-041 · **Effort:** S
- **AC:** `python -c "from epra.common.config import entsoe_token; entsoe_token()"` exits 0; a 1-day `query_day_ahead_prices('AT', …)` smoke call returns data (run manually, not committed).
- **DoD delta:** token never appears in any file, log, or shell history artifact (A-7).

#### TP.02 — GitHub remote, branch protection, CI secret `[HUMAN]`
- **Objective:** push `main`; protect it (require `lint`, `test`; later jobs 3–4); add `ENTSOE_API_TOKEN` secret.
- **Traces:** EN-080, EN-090, EN-041 · **Effort:** S · **Depends:** none (any time before M7; before M3 preferred so CI job evidence accumulates).
- **AC:** PR cannot merge with failing lint/test; secret visible to Actions; `git push` round-trips.

---

## M1 — ENTSO-E ingestion (SPEC-01 §§2–8) — merge after M2

#### T1.01 — Raw parquet writer + ING-004 metadata columns `[PAR]` `[CP]`
- **Objective:** one reusable persistence function: DataFrame → `data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet`, atomic (temp file + `os.replace`), with `ingested_at_utc`, `source`, `request_hash` columns appended.
- **Rationale:** ING-003 idempotency and ING-004 provenance are cross-dataset; write once, reuse for all four datasets + GeoSphere.
- **Traces:** ING-003, ING-004, ING-005, ING-010 · **Effort:** M · **Depends:** —
- **Inputs:** in-memory frame with `ts_utc` (tz-aware UTC); dataset name; month key; request hash.
- **Outputs:** `epra.ingest._io.write_month(frame, dataset, month, request_hash, settings) -> Path` (module private to `ingest`); TIMESTAMP µs UTC enforced on write.
- **Implementation notes:** see [03_MODULES.md](03_MODULES.md) §ingest._io; reject naive timestamps (reuse `timeutil.to_utc` upstream); byte-identical rewrite requirement means fixed column order + fixed parquet writer options + `ingested_at_utc` **excluded** from the byte-stability contract (documented: idempotency = same rows/values for data columns; test compares data columns only).
- **Validation:** unit tests: write→read round-trip preserves dtypes; overwrite leaves exactly one file; interrupted write (simulated temp-file leftover) never corrupts the target.
- **AC:** contract test asserting exact ING-004 column names/dtypes passes; re-run on same input produces equal data-column bytes.

#### T1.02 — Fetch layer: cached raw client + retry + politeness `[PAR]` `[CP]`
- **Objective:** `epra.ingest._fetch`: wraps **EntsoeRawClient** (SG-01 decision) — returns raw XML text; caches under `data/cache/entsoe/<sha256(url-minus-token)>.bin` (ING-009 semantics incl. 7-day rule and `--no-cache`); tenacity retry per ING-006; ≥0.5 s sleep between live requests (ING-007); ING-008 log line per request; asserts token not in any logged string.
- **Traces:** ING-006..009, ING-022, A-7 · **Effort:** L · **Depends:** T1.01 (hash helper co-located)
- **Failure modes:** 400/401/403 → raise immediately with response body; `Acknowledgement_MarketDocument` → classified per Appendix A (future window = empty OK, past window = error).
- **Validation:** unit tests with a stubbed transport (no network): retry schedule on 429/5xx; no-retry on 401; cache hit skips transport; cache respects the 7-day recency rule; log line format matches ING-008 regex; token-absence assertion.
- **AC:** all listed unit tests green; `grep -R "securityToken" src/` finds only the guard-safe pattern.

#### T1.03a — Handcrafted parser fixtures (pre-token) `[PAR]`
- **Objective:** minimal, spec-shaped XML fixtures in `tests/fixtures/entsoe/`: PT60M price day; **PT15M price day (ING-062)**; A03 curve with omitted positions (ING-063); DST-March and DST-October days; load PT15M day; generation multi-PSR day incl. unknown PSR code; an Acknowledgement document.
- **Rationale:** parsers and tests must be finished before the token arrives; handcrafted fixtures are legitimate **test inputs** (they are never published data — A-2/P-1 govern published numbers, not test scaffolding; state this in the fixtures README).
- **Traces:** ING-062, ING-063, EN-070, T-2 · **Effort:** M · **Depends:** —
- **AC:** each fixture parses; a `tests/fixtures/entsoe/README.md` documents provenance ("handcrafted per Appendix A shape, replaced by real excerpts in T1.03b") and each file's purpose.

#### T1.03b — Real-excerpt fixture refresh `[TOKEN]`
- **Objective:** replace/augment handcrafted fixtures with ≤200-row excerpts from real pulls (one per dataset, ING-070), preserving the handcrafted edge-case fixtures that real data may not exhibit on demand (A03 omission, mixed resolution).
- **Traces:** ING-070, EN-070 · **Effort:** S · **Depends:** TP.01, T1.04–T1.06
- **AC:** contract tests (T1.07) run against real-excerpt fixtures; fixtures README updated with pull date + request parameters.

#### T1.04 — Price ingestion AT + DE-LU `[CP]`
- **Objective:** fetch (T1.02) → parse XML per Appendix A → frame per ING §7 contract (`ts_utc, price_eur_mwh, resolution, zone`) → persist (T1.01). Currency/unit assertions (ING-050); resolution recorded per row, inferred-from-spacing fallback + inference test (ING-060); A03 forward-fill with per-month fill count logged (ING-063); ≤90-day chunking iterating months (ING-030); Vienna-tz request boundaries, UTC persisted (ING-031).
- **Traces:** ING-030, ING-031, ING-050, ING-060, ING-063 · **Effort:** L · **Depends:** T1.01, T1.02, T1.03a
- **Validation:** fixture tests: 24/23/25 rows on normal/DST days; PT15M day yields 96 rows in raw (NOT aggregated — T-2 aggregation belongs to dbt); A03 fixture fill count == expected; known fixture value → exact EUR/MWh.
- **AC:** all fixture tests green; parse of every T1.03a price fixture produces contract-exact columns/dtypes.

#### T1.05 — Load ingestion AT `[PAR]`
- **Objective:** as T1.04 for A65/A16 load → `ts_utc, load_mw, resolution, zone`.
- **Traces:** ING §3 row 3, ING §7, ING-051 · **Effort:** M · **Depends:** T1.04 (reuses its parse skeleton)
- **AC:** PT15M fixture → 96 raw rows, MW untouched (no MWh conversion — that is dbt's job, ING-051); contract test green.

#### T1.06 — Generation ingestion AT (long format) `[PAR]`
- **Objective:** A75/A16 → long rows `ts_utc, psr_type, psr_name, kind, value_mw, resolution, zone`; Appendix B code→name mapping as a module-level dict; unknown code → `UNKNOWN(<code>)` + WARN, row kept.
- **Traces:** ING-032, Appendix B · **Effort:** M · **Depends:** T1.04
- **AC:** multi-PSR fixture round-trips; unknown-code fixture keeps the row and logs WARN (caplog test); both `aggregated` and `consumption` kinds persisted.

#### T1.07 — Raw contract tests `[PAR]`
- **Objective:** `tests/test_raw_contracts.py` opening one file per dataset (from fixtures) asserting exact column names + dtypes per SPEC-01 §7 table.
- **Traces:** ING-070 · **Effort:** S · **Depends:** T1.04–T1.06
- **AC:** the test enumerates ALL five §7 datasets (incl. geosphere once M2 lands — coordinate with T2.03) and fails on any drift.

#### T1.08 — Window management + CLI + Makefile `[CP]`
- **Objective:** `backfill()` (2019-01-01 → end of last complete month, all datasets), `ingest_incremental()` (45-day lookback), `latest_complete_month()` (computed per ING-042 + SG-02 ADR), argparse CLI per ING-002; wire `make backfill|ingest`.
- **Traces:** ING-002, ING-040..042 · **Effort:** M · **Depends:** T1.04–T1.06
- **Validation:** unit test `latest_complete_month` on synthetic raw trees (full month, month with 1 missing day, empty); CLI `--help` snapshot; Makefile targets stop failing with "not implemented".
- **AC:** `python -m epra.ingest.entsoe --start 2019-01-01 --end 2019-01-31 --no-cache` exercises the full path against a mocked transport in a test.

#### T1.09 — Validation gates ING-080..085 + report writer `[CP]`
- **Objective:** implement `ingest/validate.py` ENTSO-E section: hour coverage incl. DST distinct-local-hour check, price bounds, the ING-082 per-year mean table, negative-price existence, load plausibility, price↔load join coverage; markdown report to `reports/ingestion/validation_<date>.md`; hard-fail semantics (EN-061). Uses `GateResult`/`ValidationReport` classes ([03_MODULES.md](03_MODULES.md)).
- **Traces:** ING-080..085, EN-061 · **Effort:** L · **Depends:** T1.04–T1.06, M2's calendar for local-time checks (merge order holds: M2 first)
- **Validation:** synthetic-data unit tests: each gate has ≥1 passing and ≥1 failing case; report renders all gates with PASS/FAIL + evidence rows.
- **AC:** deliberately corrupted fixture (×1000 unit error) trips ING-082 exactly as predicted; report file appears and lists the failure.

#### T1.10 — Live backfill + committed validation report `[TOKEN]` `[HUMAN-adjacent]` `[CP]`
- **Objective:** run `make backfill` (token via env), then `make validate-ingest`; investigate any failure per the guide's protocol; commit the passing validation report.
- **Traces:** ING-040, ING-080..085, M1 exit gate · **Effort:** M (elapsed hours; politeness sleeps dominate) · **Depends:** TP.01, T1.01–T1.09
- **AC:** ING-080..085 all PASS on 2019→latest; report committed under `reports/ingestion/`; no cache/raw files committed (`git status` clean of `data/`).

#### T1.11 — M1 PR assembly `[CP]`
- **Objective:** one PR; description ticks every M1 exit-gate item (AGENTS.md §3-M1) with evidence snippets; BUILD_LOG entry.
- **Traces:** A-5, W-5, EN-090 · **Effort:** S · **Depends:** T1.10, T1.03b
- **AC:** PR checklist rows from [06_CHECKLISTS.md](06_CHECKLISTS.md) §M1 all ticked; CI green.

---

## M2 — Auxiliary data (SPEC-01 §§9–11) — merge FIRST (R-1)

#### T2.01 — Calendar module `[PAR]` `[CP]`
- **Objective:** `build_calendar()` per ING-110: hourly UTC spine 2019-01-01 → end of forward window (SG-15: end = last day of `latest_complete_month + horizon_months`, recomputed each run; before M1 exists, CLI accepts `--end`), local attributes via `timeutil`, holidays `subdiv` for Styria (verify code, SG-10), `is_peak_hour` from `timeutil` (never re-implemented); persist parquet.
- **Traces:** ING-110, ING-111, SG-10, SG-15 · **Effort:** M · **Depends:** —
- **Validation:** ING-111 tests (2024 holiday count, fixed holidays, peak Monday/Sunday); DST days produce 23/25 rows; row count for a full year = 8760/8784.
- **AC:** `python -m epra.ingest.calendar --end 2027-12-31` writes parquet; all ING-111 assertions green; SG-10 resolved (test asserts the working subdiv code; ADR only if it deviates from `'6'`).

#### T2.02 — GeoSphere discovery + station ADR `[PAR]`
- **Objective:** implement `discover_station()` against the metadata endpoint; run it live (no auth); choose per ING-091 (Graz, longest record, prefer "Graz Universität"); write `station_id/station_name` into `config/settings.yaml`; author **ADR-003** with id/name/lat/lon and dataset id verification; flip the pending-discovery config test to assert the chosen id.
- **Traces:** ING-090..092, GV-203 · **Effort:** M · **Depends:** —
- **AC:** ADR-003 merged in-milestone; `settings.geosphere.station_id` non-null; updated test green.

#### T2.03 — GeoSphere ingestion + gates `[PAR]`
- **Objective:** daily `tl_mittel` 2019→latest into monthly parquet per §7 contract (reuse T1.01 writer; if built before T1.01, implement the writer here and T1.01 consumes it — whichever lands first owns `_io`); ≥0.2 s politeness; ING-009 cache; ING-094 gates added to `validate.py` (+ report section) — this may precede T1.09; keep the gate framework classes shared.
- **Traces:** ING-090, ING-093, ING-094 · **Effort:** M · **Depends:** T2.02
- **Validation:** fixture (GeoJSON excerpt) parse test; gate unit tests pass/fail cases; live run committed to validation report.
- **AC:** ING-094 PASS on real 2019→latest data; raw contract test row added for `geosphere_graz_daily`.

#### T2.04 — ÖSPI loader + gates + methodology ADR
- **Objective:** `load_oespi()` reading `data/manual/oespi_monthly.csv` (schema ING-100), ING-103 gate set (continuity, positivity, crisis-visibility 2022 peak ≥3× 2019 mean, MoM ≤ ±60%) wired into `validate.py`; **ADR-004** records the series/methodology choice + source URLs (ING-102); ING-104 base-only fallback path implemented behind `peak_available`.
- **Traces:** ING-100, ING-102..104 · **Effort:** M · **Depends:** T2.05 (real CSV) for the live gate run; loader+tests build against synthetic CSV first
- **AC:** gates green on the reconciled real CSV; ADR-004 merged; synthetic-CSV unit tests cover every gate's fail case.

#### T2.05 — ÖSPI double transcription `[HUMAN]` `[CP]`
- **Objective:** human transcribes the full 2019→latest series twice (entry1/entry2) from the AEA publication; runs `python scripts/oespi_reconcile.py`; commits reconciled `oespi_monthly.csv`; deletes entry files.
- **Traces:** ING-101, A-2 · **Effort:** M (human) · **Depends:** ADR-004 series choice proposal (T2.04 drafts it; human confirms source before transcribing)
- **AC:** reconcile exits 0; committed CSV covers 2019-01 → latest published month; entry files absent from the repo.

#### T2.06 — M2 PR assembly `[CP]`
- As T1.11, for M2 (gates ING-094/101/103/111; ADR-003/004; BUILD_LOG).
- **AC:** [06_CHECKLISTS.md](06_CHECKLISTS.md) §M2 fully ticked; CI green.

---

## M3 — dbt warehouse (SPEC-02)

#### T3.01 — Sources + schema-name macro + external parquet plumbing `[CP]`
- **Objective:** `models/sources.yml` exposing each raw dataset via `read_parquet` glob exactly once (DM-004); `generate_schema_name` macro so schemas are literally `staging`/`marts` (SG-13); smoke model proving source reads work.
- **Traces:** DM-003, DM-004, SG-13 · **Effort:** M · **Depends:** M1+M2 merged (real data locally); fixtures enough for CI
- **AC:** `dbt build --select smoke` green from `dbt/`; schemas named without prefixes (query `information_schema.schemata`).

#### T3.02 — Staging models (8) `[CP]`
- **Objective:** the eight §3 models with exact grains/columns; hourly aggregation = **mean** of sub-hourly (T-2), `n_subhours` recorded; the single sanctioned dedup (DM-020) + pre-dedup count test (warn > 30/month).
- **Traces:** DM-005, DM-020, §3 table · **Effort:** L · **Depends:** T3.01
- **Validation:** dbt tests per model grain (unique+not_null); a PT15M fixture month aggregates to means (recheck ING-062 at warehouse level).
- **AC:** `dbt build --select staging` green on real + fixture data; column names/units match §3 exactly (schema test in T3.05 will pin them).

#### T3.03 — dim_calendar + dim_strategy `[PAR]`
- **Objective:** `dim_calendar` from calendar parquet + weather join (season rule, `hdd_18`, `cdd_22` repeated across the local day's 24 h); seed already present — add relationship test scaffolding.
- **Traces:** SPEC-02 §4, DM-011 · **Effort:** M · **Depends:** T3.02
- **AC:** DST edge hours present exactly once each (DM-012 test data); HDD/CDD spot values match hand-computed fixture expectations.

#### T3.04 — Marts `[CP]`
- **Objective:** `fct_price_hourly` (column list per SG-05 enumeration), `fct_price_daily`, `fct_price_monthly` (+ ÖSPI join), `fct_generation_monthly` (share_of_total), `fct_consumer_load_hourly` + `fct_procurement_cost_monthly` as thin loaders over processed parquet — enabled but fed by **fixture stand-ins** until M4/M6 produce real files (SG-06).
- **Traces:** SPEC-02 §5, DM-050, SG-05, SG-06 · **Effort:** L · **Depends:** T3.03
- **AC:** month-spine no-gap test green; `price_peak_eur_mwh` NULL on no-peak days verified on a holiday fixture.

#### T3.05 — dbt test suite DM-060..066 + schema contract `[CP]`
- **Objective:** full DM test set incl. custom row-count test (±24), 2022-08 reconciliation singular test (0.01 tolerance), DST hour-count tests, freshness (refresh-only, DM-066 via `dbt build --select ... --vars`), and the **schema contract test**: information_schema vs committed `dbt/contracts/marts_contract.yml`.
- **Traces:** DM-060..066, M3 exit gate · **Effort:** L · **Depends:** T3.04
- **AC:** `dbt build` green with zero skipped tests on real data; editing any mart column name breaks the contract test (verify once, revert).

#### T3.06 — CI fixture bootstrap + job 3 `[CP]`
- **Objective:** `scripts/bootstrap_fixture_warehouse.py` creating `data/raw` + processed stand-ins from `tests/fixtures/` parquet; `.github/workflows/ci.yml` job `dbt-check` running it + `dbt build`; make job required (TP.02).
- **Traces:** EN-080 job 3 · **Effort:** M · **Depends:** T3.05
- **AC:** CI green on a PR touching dbt; job runtime < 5 min.

#### T3.07 — M3 PR assembly `[CP]` — as T1.11 (gate: dbt build green real+fixtures; schemas byte-match). BUILD_LOG.

---

## M4 — Consumer profile (SPEC-03)

#### T4.01 — Weight engine (algorithm steps 1–4) `[CP]`
- **Objective:** pure function producing per-hour weights from calendar frame + `ConsumerProfileCfg`: day_type precedence (shutdown > holiday→weekend > Sat/Sun > weekday), maintenance week per SG-04 rule, Christmas shutdown spanning year boundary, seasonal factors.
- **Traces:** LP §2 steps 1–4, §3.3 · **Effort:** L · **Depends:** M3 merged (dim_calendar), SG-04 ADR
- **Validation:** unit tests per rule: Dec 25 vs Dec 26 equality; maintenance factor applied on top of weekday shape; holiday Monday gets weekend shape; Aug-1-is-Monday edge year (2022) maintenance = Aug 1–7.
- **AC:** all rule tests green; zero YAML numerics duplicated in code (grep for `0.18|0.60|1.06` in `src/` finds nothing).

#### T4.02 — Normalization incl. partial years `[CP]`
- **Objective:** per-local-year normalization to exactly `annual_consumption_mwh` (±0.01); LP-034 hypothetical-full-year rule for the forward partial year.
- **Traces:** LP-004, LP-034 · **Effort:** M · **Depends:** T4.01
- **Validation:** 6-month-window fixture reproduces the same monthly volumes as the full-year run (LP-034 test); each full local year sums to 50,000.00 ± 0.01.
- **AC:** both tests green; DST years included in the tested set.

#### T4.03 — Outputs: hourly parquet, monthly volumes, peak share `[CP]`
- **Objective:** persist `consumer_load_hourly.parquet` + `consumer_load_monthly.parquet`; compute `consumer_peak_share` per SG-03 ADR (reference-year value published, per-year variation test <1 pp); write SSOT-inputs parquet consumed later by `generate_ssot.py`.
- **Traces:** LP-003, LP-020, LP-021 · **Effort:** M · **Depends:** T4.02
- **AC:** peak share ∈ [0.42, 0.48] (LP-020 plausibility); files land in `data/processed/`; dbt `fct_consumer_load_hourly` now reads real output.

#### T4.04 — flat_baseload variant + golden/property/meta tests `[CP]`
- **Objective:** LP-030 second profile via config switch; LP-040 golden (ratios, Aug<Jul, Dec25==Dec26, sha256 of 2023 slice persisted to `tests/golden/`), LP-041 property tests, LP-042 checksum-sensitivity meta-test.
- **Traces:** LP-030, LP-040..042, EN-072 · **Effort:** L · **Depends:** T4.03
- **AC:** golden checksum stable across two clean rebuilds (run twice in CI locally); meta-test proves sensitivity.

#### T4.05 — `make profile` wiring + M4 PR `[CP]` — CLI entry, Makefile target un-stubbed, stub-test rows for M4 deleted, BUILD_LOG, PR per template.
- **AC:** `make profile` idempotent (second run byte-identical except `ingested_at_utc`-class metadata); [06_CHECKLISTS.md](06_CHECKLISTS.md) §M4 ticked.

---

## M5 — Analytics (SPEC-04) — order A1→A2→A4→A3

#### T5.01 — Analytics shared kit `[CP]`
- **Objective:** mart-reader helpers (`db.connect` read-only + SQL in one place), artifact writers (md table + prose section, PNG saver applying RP-701/702 style incl. source note + epistemic tag stamp), SSOT-inputs emitter (appends typed rows: key, value, unit, tag, produced_by).
- **Traces:** AN preamble ("read from marts only"), RP-701..703, AN-703 · **Effort:** M · **Depends:** M4 merged
- **AC:** chart helper output PNG passes a pixel-independent test (figsize/dpi/text elements present via matplotlib object inspection, not image diff).

#### T5.02 — A1 descriptive `[PAR]`
- **Objective:** AN-101 annual table (md+CSV), AN-102 heatmap (5 panels, shared scale), AN-103 duration curves, AN-104 negative-price analysis + SSOT rows, AN-105 prose paragraph (≥400 chars, mentions solar midday depression, 2022 level, negative-hour meaning for flexible consumers).
- **Traces:** AN-101..105 · **Effort:** L · **Depends:** T5.01
- **AC:** all four A1 artifacts exist post-`make analyze`; AN-704 prose test green; SSOT input rows tagged VERIFIED only.

#### T5.03 — A2 spread `[PAR]` — AN-201..203 artifacts + SSOT `spread_mean_<year>`; interpretation paragraph. **Effort:** M · **Depends:** T5.01 · **AC:** zero-line present in chart; stats table matches a hand-checked month.

#### T5.04 — A4 weather `[PAR]` — AN-401..402: scatter+OLS (HC1, month FE) to md+PNG; weather-invariance sentence included. **Effort:** M · **Depends:** T5.01 · **AC:** OLS coefficient sign positive (load rises with HDD) asserted with tolerance; prose test green.

#### T5.05 — A3 regimes (HMM) `[CP]`
- **Objective:** AN-302 exactly: daily arithmetic diffs, z-scored, GaussianHMM(3, full, 500), restarts seeded 42..51, best LL wins; state labeling by ascending std; timeline chart + occupancy/stats table.
- **Traces:** AN-301 (realized vol chart), AN-302, T-3 · **Effort:** L · **Depends:** T5.01
- **Validation:** determinism test (two fits → identical state sequence); AN-304 sanity gate implemented as a hard test.
- **AC:** AN-304 passes on real data (≥70% crisis-window days in top-2 states; ≥60% of 2019 calm); if it fails → investigation protocol in the guide, NOT gate widening.

#### T5.06 — A3 GARCH complement `[PAR]`
- **Objective:** AN-303: GARCH(1,1) on d_t, documented rescale if optimizer warns, overlay chart vs 30-day realized vol, `garch_persistence` → SSOT (VERIFIED); α+β ≥ 1 reported as near-integrated, never "fixed".
- **Traces:** AN-303 · **Effort:** M · **Depends:** T5.05 (shares the d_t series builder)
- **AC:** persistence value reproducible to full float precision across two runs.

#### T5.07 — `make analyze` + AN-70x gates + M5 PR `[CP]`
- **Objective:** wire target; existence check for the 12-artifact list (AN-701); determinism ×2 (AN-705); delete M5 stub-test rows; BUILD_LOG; PR.
- **AC:** `make analyze` from clean `reports/analytics/` regenerates all 12 artifacts; second run → identical SSOT input values; [06_CHECKLISTS.md](06_CHECKLISTS.md) §M5 ticked.

---

## M6 — Strategies (SPEC-05) — the heart; sequence is mandatory

#### T6.01 — Strategy data access + volume alignment `[CP]`
- **Objective:** loaders joining `fct_price_hourly` × `fct_consumer_load_hourly` and monthly volumes × ÖSPI; implement the ST-101 NULL-price drop rule ONCE (drop hour from all strategies' volume; log dropped hours) so every engine consumes pre-aligned frames.
- **Traces:** ST-001, ST-101, ST-501 · **Effort:** M · **Depends:** M5 merged
- **AC:** unit test: synthetic month with 3 NULL hours → identical volume across strategies; dropped-hours log line emitted.

#### T6.02 — Calibration anchors `[CP]`
- **Objective:** ST-201..204 exactly; ST-202 docstring carries the spec sentence verbatim; anchors persisted for SSOT (CALIBRATED).
- **Traces:** ST-201..204, T-5 · **Effort:** M · **Depends:** T6.01
- **Validation:** synthetic-2019 unit test where anchors are hand-computable; plausibility assertion p_ref_base ∈ [30, 60] EUR/MWh on real data (2019 gate range echo).
- **AC:** anchors deterministic; unit test green; real-data values recorded in PR description.

#### T6.03 — Retrospective S1 `[CP]`
- **Objective:** hourly spot cost per month 2021–2025 (+2019 for calibration); monthly output schema `year_local, month_local, strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh`.
- **Traces:** ST-101, ST-301 partial · **Effort:** M · **Depends:** T6.02
- **AC:** hand-computed synthetic month matches to the cent; 2022 unit cost ≫ 2019 unit cost on real data (sanity echo).

#### T6.04 — Retrospective S2/S3/S4 + no-lookahead test `[CP]`
- **Objective:** ST-102..107; S3 lock-window mean via config months; S4 reuses S1 leg scaled; ST-503 test asserting p_S3(2022) consumes only 2021-07..12 ÖSPI rows (spy/fixture-based).
- **Traces:** ST-102..107, ST-503 · **Effort:** L · **Depends:** T6.03
- **AC:** ST-602(b) hybrid-between-legs relation holds on real data (±0.5%); no-lookahead test green; every output caption carries the ST-502 sentence (helper from T5.01 reused).

#### T6.05 — Annual summary, headline, charts `[CP]`
- **Objective:** ST-301 aggregate + rank/delta; ST-302 `wrong_strategy_cost_<year>` + 5-yr total; ST-304 charts via report kit.
- **Traces:** ST-301, ST-302, ST-304 · **Effort:** M · **Depends:** T6.04
- **AC:** ST-602(a) holds (2022: S1 > S3) — if not, STOP per phase rollback; matrix persisted to processed parquet feeding `fct_procurement_cost_monthly`.

#### T6.06 — Sensitivities `[PAR]`
- **Objective:** ST-303 exactly three: premium {0,5,10}, flat_baseload, full-prior-year lock; one compact md table `reports/strategies/sensitivity_matrix.md`. No further sensitivities (scope guard).
- **Traces:** ST-303, O-7 · **Effort:** M · **Depends:** T6.05
- **AC:** each sensitivity is a config-delta rerun through the same engine (no forked logic); table renders all three blocks.

#### T6.07 — Forward bootstrap (vectorized) `[CP]`
- **Objective:** ST-401 verbatim with the ST-406 cost-cell precompute (equivalence argument documented in the guide); single seeded RNG; month draws keep prices+ÖSPI together (T-6); SG-07 day-mapping rule; SG-08 quantile/CVaR method pins; outputs ST-403 table + fan + risk-return charts.
- **Traces:** ST-401..404, ST-406, T-6 · **Effort:** L · **Depends:** T6.05 (cells), T5.05 (regime labels for step 4)
- **Validation:** N=50 smoke distribution sanity (P95 ≥ P50 ≥ P5 per strategy); determinism ×2 exact; runtime N=2000 < 10 min.
- **AC:** ST-602(c) P95(S1) ≥ P95(S3) on real data; no-crisis variant produced (restricted pool per ST-401 step 4) and labeled.

#### T6.08 — SSOT generator `[CP]`
- **Objective:** `scripts/generate_ssot.py` per GV-301/302: reads persisted outputs (never recomputes), emits the full GV-302 key set + analytic/profile inputs, columns `key|value|unit|tag|produced_by|updated_at`; E-2 dependency rule enforced structurally (tag column sourced from producing module's declaration, not retyped).
- **Traces:** GV-301, GV-302, E-2, E-3 · **Effort:** M · **Depends:** T6.05, T6.07, T4.03, T5.07
- **AC:** every GV-302 key present exactly once; `make ssot` twice → identical file except nothing (fully deterministic incl. `updated_at` sourced from inputs' max mtime hash — SG-09 companion decision documented in ADR).

#### T6.09 — SSOT consistency checker + CI job 4 `[CP]`
- **Objective:** `scripts/check_ssot_consistency.py` per GV-303 + SG-09 rounding rule; `scripts/ssot_whitelist.txt` with per-line comments; freshness check; CI job `ssot-check` added + required.
- **Traces:** GV-303, EN-080 job 4 · **Effort:** L · **Depends:** T6.08
- **AC:** mutation test: change one README number by 1 unit → checker fails naming the key; whitelisted year "2022" does not false-positive.

#### T6.10 — Goldens + determinism + M6 PR `[CP]`
- **Objective:** `generate_golden_metrics.py` implemented; `tests/golden/strategy_annual_summary.json` written on first accepted results (human approves values, AGENTS §2.6); ST-601 golden test; ST-405 determinism test (`make simulate` ×2 → clean diff); delete M6 stub rows; BUILD_LOG; PR ticking ST-601..604.
- **Traces:** ST-601..604, EN-072 · **Effort:** M · **Depends:** T6.07–T6.09, `[HUMAN]` golden approval
- **AC:** [06_CHECKLISTS.md](06_CHECKLISTS.md) §M6 + scientific checklist fully ticked; all four CI jobs green.

---

## M7 — Reporting, dashboard, refresh, release (SPEC-06, SPEC-07 §8)

#### T7.01 — Export script + contract tests `[CP]`
- **Objective:** `scripts/export_marts.py` writing the six §7 CSVs (UTF-8, ISO dates, dot decimal); DM-070 contract tests (columns/dtypes per export).
- **Traces:** DM-070, SPEC-02 §7 · **Effort:** M · **Depends:** M6 merged
- **AC:** `make export` produces exactly six files; contract tests green; re-run idempotent.

#### T7.02 — Executive charts `[CP]`
- **Objective:** RP-201..204 via the report kit; RP-301 reproducibility pytest (recompute chart-1 bars from `strategy_annual_summary.csv`); captions/tags per RP-702 + LP-050 + ST-502.
- **Traces:** RP-201..204, RP-301 · **Effort:** L · **Depends:** T7.01
- **AC:** four PNGs in `reports/executive_charts/`; RP-301 test green; RP-204 overlays regime bands + indexed ÖSPI axis.

#### T7.03 — EXEC_SUMMARY `[HUMAN-co]` `[CP]`
- **Objective:** ≤2 pages per SPEC-06 §5 structure; §5 recommendation co-written with human; every number copy-pasted from SSOT; "no hedging language without a number".
- **Traces:** RP §5, DL-5, A-6 · **Effort:** M · **Depends:** T6.08
- **AC:** GV-303 checker passes over EXEC_SUMMARY; §§1–6 all present; page count ≤ 2 (rendered estimate documented).

#### T7.04 — Final README + LIMITATIONS `[CP]`
- **Objective:** README per §6 order (answer first, stack last, RP-601); LIMITATIONS sections 1–7 finalized with computed sensitivity numbers.
- **Traces:** RP-601, SPEC-08 §6, DL-9, DL-10 · **Effort:** M · **Depends:** T7.02, T7.03
- **AC:** GV-303 green over README; every §6 element present in order; RP-201 chart embedded and rendering on GitHub.

#### T7.05 — refresh.yml `[CP]`
- **Objective:** EN-081..083: monthly cron + dispatch; `make refresh`; artifact upload; automated PR with only committed report changes (skip PR when diff empty — SG-18); ÖSPI-coverage check suppressing uncovered-month strategy outputs (ING-104/EN-083).
- **Traces:** EN-081..083 · **Effort:** L · **Depends:** TP.02, T7.01
- **AC:** `workflow_dispatch` dry-run on GitHub succeeds end-to-end (with token secret) and opens/skips PR correctly.

#### T7.06 — Power BI handoff + human build `[HUMAN]`
- **Objective:** complete `dashboards/README.md` build instructions (relative-path relink, relationships, 4 pages per RP-401..405); human builds `.pbix`, screenshots to `docs/assets/dashboard_p1..4.png`; embed in README.
- **Traces:** RP-401..406, DL-6 · **Effort:** M (human) · **Depends:** T7.01
- **AC:** `.pbix` committed; four screenshots present + embedded; German subtitle on each page visible in screenshots.

#### T7.07 — Release: DL-1..10 walk + M7 PR `[CP]`
- **Objective:** execute [11_ACCEPTANCE_CRITERIA.md](11_ACCEPTANCE_CRITERIA.md) §M7 verbatim, incl. the fresh-clone DL-1 rehearsal; BUILD_LOG final entry; PR ticks DL-1..10 with evidence.
- **Traces:** Charter §6 · **Effort:** L · **Depends:** T7.01–T7.06
- **AC:** all ten DLs objectively verified; release checklist in [06_CHECKLISTS.md](06_CHECKLISTS.md) fully ticked.
