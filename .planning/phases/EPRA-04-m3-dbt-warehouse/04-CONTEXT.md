# Phase 4: M3 dbt Warehouse - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning
**Mode:** Interactive discuss — spec-supremacy project. `docs/SPEC-02_data_model.md` (DM-xxx) locks *what* to build (model names, grains, columns, units, DM-060..066 tests); WBS §M3 (T3.01–T3.07) locks the task shape. This discussion captures the **operational / HOW decisions the spec leaves open** — the fixture/CI story, the real-data close boundary, the future-mart stand-ins, and the contract/ADR governance.

<domain>
## Phase Boundary

Build the dbt + DuckDB transformation layer between `data/raw/` and all analytical consumption (REQ-DWH-01). One milestone, one PR.

- **Warehouse:** single DuckDB file `data/warehouse/epra.duckdb` (gitignored, DM-001); dbt-duckdb project at `dbt/` (skeleton already committed).
- **Models (16):** 8 staging views (`stg_*`, §3), 2 dimensions (`dim_calendar` hour-grain with weather join + `dim_strategy` seed, §4), 6 marts (`fct_*`, §5) — schemas `raw`/`staging`/`marts` per DM-003.
- **Tests:** DM-060..066 (unique/not_null, accepted ranges, per-year row counts ±24, 2022-08 reconciliation singular test, DST hour-count tests, refresh-only freshness) + a hand-authored schema contract that byte-matches SPEC-02 §5.
- **CI:** `scripts/bootstrap_fixture_warehouse.py` + a required `dbt-check` job so `dbt build` is green network-free without a full local backfill.

**Exit gate (SC):** (1) `dbt build` green on **real** data locally; (2) mart schemas byte-match the committed SPEC-02 §5 contract YAML; (3) CI fixture bootstrap makes `dbt build` green without a full backfill.

**Out of this phase:**
- **BI exports** — `scripts/export_marts.py` / `make export` / SPEC-02 §7 CSVs are **M7/Phase 8** per WBS (M3 tasks stop at CI bootstrap, T3.06). M3 does NOT write `exports/`.
- Consumer load-profile computation (M4/Phase 5) and strategy-cost computation (M6/Phase 7) — M3 only *re-exposes* their eventual parquet outputs as marts, fed by stand-ins until then.
- Anything upstream of `data/raw/` (ingestion is M1+M2, complete).

</domain>

<decisions>
## Implementation Decisions

### Real-data close boundary (Area A — reprises D-06/D-07 from M1/M2)
- **D-01:** **Split by environment.** The **CI blocking gate** is `dbt build` green on the *synthesized fixture warehouse* (network-free, deterministic, <5 min, T3.06). The **real-data `dbt build`** is run in-phase locally (real data is already present in `data/raw/` 2019→2024 + calendar parquet + reconciled `oespi_monthly.csv`). The phase **closes only when BOTH are green** — satisfies SC#1 (real) and SC#3 (CI fixtures) while keeping CI deterministic.
- **D-02:** The real-data checkpoint commits a **human-readable build report** at `reports/warehouse/dbt_build_<date>.md` (models built; test pass/fail counts; key sanity numbers — per-year hourly row counts, month coverage, 2022-08 reconciliation delta). Mirrors the `reports/ingestion/validation_*.md` precedent. The `data/warehouse/epra.duckdb` file itself stays **gitignored** (DM-001); `git status` must stay clean of `data/`.

### CI fixture bootstrap (Area B — SG-06, T3.06)
- **D-03:** The fixture warehouse spans a **contiguous window that includes every spec-hardcoded test date** — at minimum **2022-01-01 → 2024-12-31** — so DM-062 (full local years, 8760/8784 ±24), DM-064 (2022-08 reconciliation), DM-065 (2024-03-31 = 23 h, 2024-10-27 = 25 h), and DM-050 (no-gap month spine) all run **UNMODIFIED with their spec-literal dates**. The window span is the deliberate price of keeping CI tests byte-identical to the real-data build (no test-date parametrization, no ADR for the tests themselves).
- **D-04:** `scripts/bootstrap_fixture_warehouse.py` **synthesizes the rows programmatically at CI time** (seeded/deterministic) and writes the `data/raw/**` + `data/processed/**` parquet — it does **not** copy committed multi-MB parquet. Repo stays lean (M1's ≤200-row lean-excerpt spirit preserved for hand-authored fixtures; the full-window warehouse is generated, never committed). Synthetic values are crafted to pass DM-061 accepted ranges and the DM-064 reconciliation (monthly base = mean of hourly). This **deviates from WBS T3.06's "from `tests/fixtures/` parquet" wording** → recorded in **ADR-010** (SG-06 adoption).

### Future-mart stand-ins (Area C — SG-06, SG-05, DM-050/DM-063)
- **D-05:** `fct_consumer_load_hourly` (M4 input `data/processed/consumer_load_hourly.parquet`) and `fct_procurement_cost_monthly` (M6 SPEC-05 output) are **never disabled** (SG-06). They build off **full-window, valid, environment-aligned stand-in parquet**: consumer load = hourly valid MWh over the window; procurement cost = **every month × all 6 strategy_ids** (S1, S2, S3, S4_30, S4_50, S4_70) with valid costs. This makes **DM-050 (no-gap), DM-063 (strategy FK → dim_strategy), and DM-060 (keys)** pass **unmodified** on both marts.
- **D-06:** The stand-in window **matches the surrounding data window per environment** — real **2019→latest** in the local build, synthetic **2022–2024** in CI — so the DM-050 generated month-spine aligns with the other monthly marts in that environment. `data/processed/` is empty even locally, so the **same stand-in mechanism feeds the local real-data build** (D-01's gate), not just CI, until M4/M6 produce real files. The build report (D-02) flags these two marts as "stand-in (M4/M6 pending)."

### Contract & ADR governance (Area D — SG-05, T3.05)
- **D-07:** `dbt/contracts/marts_contract.yml` is **hand-authored from SPEC-02 §5 + the SG-05 enumeration**, covering **all 6 marts** (including the two stand-in-fed ones). SG-05's frozen enumeration for `fct_price_hourly` = the ING-110 calendar list (`date_local, year_local, month_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour`) + `season, hdd_18, cdd_22`. The T3.05 schema-contract test diff-checks `information_schema.columns` against this human-reviewed, spec-derived YAML; editing any mart column name/type breaks it (verify once, revert). SG-05 needs **no ADR** — the committed contract YAML *is* its adoption.
- **D-08:** Three **single-topic ADRs** (matching the ADR-001..008 one-decision-per-ADR precedent and the WBS T3.01/T3.04/T3.06 triggers). **Confirm next-free numbers against `docs/ADR/` at planning time** (currently ADR-009/010/011 are free):
  - **ADR-009** — SG-13 `generate_schema_name` override macro so schemas are literally `staging`/`marts` (not `main_staging`).
  - **ADR-010** — SG-06 CI-fixture synthesis + environment-aligned stand-in policy (includes the D-04 generated-at-CI deviation from WBS wording and the D-05/D-06 stand-in-feeds-local-build decision).
  - **ADR-011** — SG-14 holiday-aware peak (`is_peak_hour`, ING-110) used everywhere for `price_peak_eur_mwh` + anchors, plus the note that ÖSPI's own peak convention may treat holidays differently (anchor ratios absorb the level offset) → **also add a LIMITATIONS.md §2 entry**.

### Claude's Discretion
- **Operator interface:** the real-data build wrapper (e.g., `make warehouse` / `make dbt-check`) naming and Makefile wiring — "Makefile as canonical operator interface" is already a locked PROJECT.md key decision; the exact target names are the implementer's choice.
- **Month-spine test mechanism** (DM-050): custom SQL spine macro vs a `dbt_utils` dependency — planner/researcher decides; if a package dep is added, note it (minimal footprint preferred, consistent with the lean-repo posture).
- **Model/macro decomposition, SQL style, staging CTE structure, synthetic-generator internals, seed/relationship-test scaffolding layout** — implementer's choice within the SPEC-02 contracts and DM-xxx model-YAML citations (W-2), consistent with M1/M2.
- **Fixture-generator determinism knobs** (seed value, exact synthetic curve shape) — free, provided all DM-060..066 pass.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Binding spec (authority)
- `docs/SPEC-02_data_model.md` — the whole file governs this phase. §1 stack/layout (DM-001..005), §2 timezone doctrine (DM-010..012, `ts_utc` join key, `dim_calendar` is the ONLY source of local attributes), §3 the 8 staging contracts + DM-020 dedup, §4 dimensions (`dim_calendar` weather join / season rule / hdd_18 / cdd_22; `dim_strategy` seed), §5 the 6 mart contracts (the exit-gate diff target), §6 tests DM-060..066, §7 exports (**M7, not this phase**).
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M3 — tasks T3.01 (sources + `generate_schema_name` macro + smoke), T3.02 (8 staging), T3.03 (`dim_calendar`/`dim_strategy`), T3.04 (marts), T3.05 (DM-060..066 + schema contract test), T3.06 (CI fixture bootstrap + job 3), T3.07 (M3 PR assembly).
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` — module contracts (esp. any `validate`/report-writer analog; reuse the `GateResult`/`ValidationReport` style for the build report if useful).

### Spec-gap resolutions adopted here (ADRs at T3.01/T3.04/T3.06)
- `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` — **SG-05** (`fct_price_hourly` enumeration = frozen contract YAML; no ADR), **SG-06** (fixture bootstrap + stand-in policy → ADR-010), **SG-13** (`generate_schema_name` macro → ADR-009), **SG-14** (holiday-aware peak + ÖSPI note → ADR-011 + LIMITATIONS §2). Also relevant/resolved: SG-16 (staging dedup is defense-in-depth), SG-17 (persist both gen kinds; staging filters `aggregated`).

### Precedent / patterns to reuse
- `docs/ADR/ADR-006_validation-gate-scope-local-year.md` — gates scoped to complete Vienna-local years; the D-01 split-by-environment close boundary reprises this + the EN-070 live-vs-CI split.
- `docs/ADR/ADR-005_latest-complete-month-sg02.md` — `latest_complete_month()`; drives the local real-data window end (2019→latest) that the stand-in generator (D-06) must align to.
- `.planning/phases/EPRA-03-m2-auxiliary-data/03-CONTEXT.md` — M2 decisions carried forward: D-06/D-07 real-data-boundary pattern (fixtures/synthetic green in CI; real data as committed checkpoint), functional-core discipline, spec-ID-in-docstring/model-YAML.
- `.planning/phases/EPRA-02-m1-entso-e-ingestion/02-CONTEXT.md` — M1 fixture/live-vs-fixture pattern; the ≤200-row lean-excerpt convention that D-04 preserves for hand-authored fixtures.

### Downstream consumers (context, not modified here)
- `docs/SPEC-03_consumer_load_profile.md` — produces `data/processed/consumer_load_hourly.parquet` that replaces the D-05 consumer stand-in at M4.
- `docs/SPEC-05_strategy_simulator.md` — produces the procurement-cost parquet that replaces the D-05 procurement stand-in at M6; `dim_strategy` seed and `fct_procurement_cost_monthly` re-expose it for BI.

### Governance
- `docs/PROJECT_CHARTER.md` + `docs/ADR/ADR-001_light-governance-no-external-kit.md` — append-only ADRs (GV-201..203) and single-topic precedent that D-08 follows.
- `LIMITATIONS.md` §2 — receives the SG-14 ÖSPI-peak-convention note (ADR-011).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dbt/` skeleton is **already committed and correct**: `dbt_project.yml` fixes `staging`→view/`marts`→table materializations and schema names; `profiles.yml` points `duckdb` at `../data/warehouse/epra.duckdb` (relative, no creds, DM-002); `dbt/seeds/dim_strategy.csv` holds all 6 strategies. `models/staging/`, `models/marts/`, `macros/`, `tests/` exist as `.gitkeep` stubs awaiting models.
- Real `data/raw/` is **fully populated locally** (entsoe prices AT/DE-LU, load AT, gen AT 2018→2024; `calendar/calendar.parquet`; `geosphere_graz_daily/`) and `data/manual/oespi_monthly.csv` is reconciled (92 months) — so the D-01 local real-data `dbt build` is runnable now.
- `tests/fixtures/entsoe/*_2024-01.parquet` and `tests/fixtures/geosphere/geosphere_graz_daily_2024-01.parquet` are **real single-month excerpts** — reusable as edge-case seeds if the synthetic generator (D-04) wants realistic shapes, but the full contiguous window is generated, not committed.
- `src/epra/common/timeutil.py` (`is_peak_hour`, `to_utc/to_local`) — the ONLY sanctioned TZ layer (T-1). Per DM-011 **no dbt model calls TZ functions**; local attributes come only from `dim_calendar` (built from the calendar parquet that already used timeutil).
- `scripts/export_marts.py` exists as a stub — **leave it for M7** (out of this phase's scope).

### Established Patterns
- Spec-ID citations in artifacts (M1/M2 used `Implements: ING-xxx` docstrings) → here cite `DM-xxx` in model YAML / macro comments (W-2).
- Live/real work isolated from deterministic CI (EN-070; M1 `@pytest.mark.live`, CI `-m "not live"`) → D-01's split-by-environment close is the dbt analog: CI runs the synthesized fixture warehouse; real build is local.
- Committed validation/build reports under `reports/` (M1/M2 `reports/ingestion/validation_*.md`) → D-02 adds `reports/warehouse/dbt_build_<date>.md`.
- Contract tests that fail on drift (M1 `tests/test_raw_contracts.py` per SPEC-01 §7) → D-07 schema-contract test is the SPEC-02 §5 analog.

### Integration Points
- New: `dbt/models/sources.yml` (+ `generate_schema_name` macro, ADR-009), `dbt/models/staging/stg_*.sql`, `dbt/models/marts/{dim_calendar,fct_*}.sql`, `dbt/models/**/schema.yml` (DM tests), `dbt/contracts/marts_contract.yml` (hand-authored), `dbt/tests/` singular tests (DM-064 reconciliation, DM-062 row counts, DM-065 DST, DM-050 spine).
- New: `scripts/bootstrap_fixture_warehouse.py` (D-04 synthesizer) + `.github/workflows/ci.yml` `dbt-check` job (required, TP.02).
- New: `docs/ADR/ADR-009..011` (confirm numbers) + `LIMITATIONS.md` §2 entry.
- `data/raw/**/*.parquet` glob is read **exactly once per source** in `sources.yml` via `read_parquet` (DM-004) — no other model touches files directly.

</code_context>

<specifics>
## Specific Ideas

- **Fixture window 2022-01-01 → 2024-12-31** is the concrete minimum: 2022 gives the DM-064 crisis month (2022-08) and a full year; 2024 gives the DM-065 DST days (2024-03-31, 2024-10-27); three contiguous full local years satisfy DM-062 + DM-050. Extend earlier only if a test needs it.
- **Strategy IDs** the procurement stand-in must emit (DM-063): `S1, S2, S3, S4_30, S4_50, S4_70` — exactly the `dbt/seeds/dim_strategy.csv` rows.
- **Season rule** (DM-`dim_calendar`): `winter` if `month_local in (11,12,1,2,3)` else `summer` (Austrian energy convention) — document in model YAML.
- **`price_peak_eur_mwh` is NULL on days with no peak hours** (holiday fixture verifies) — the holiday-aware `is_peak_hour` (ADR-011/SG-14) drives this.

</specifics>

<deferred>
## Deferred Ideas

- **BI exports** — `scripts/export_marts.py`, `make export`, SPEC-02 §7 CSVs (`exports/price_daily.csv` etc.) and their ING-070-style contract tests (DM-070) → **M7/Phase 8** (WBS defers them; M3 stops at CI bootstrap). Power BI reads only from `exports/`, never DuckDB.
- **Real consumer-load parquet** replaces the D-05 consumer stand-in → **M4/Phase 5** (SPEC-03).
- **Real procurement-cost parquet** replaces the D-05 procurement stand-in → **M6/Phase 7** (SPEC-05).
- **DM-066 freshness gate** is refresh-only (`make refresh`, scheduled runs) → wired now but exercised at **M7** monthly refresh, not in normal `dbt build`.

None outside these — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-M3 dbt Warehouse*
*Context gathered: 2026-07-23*
