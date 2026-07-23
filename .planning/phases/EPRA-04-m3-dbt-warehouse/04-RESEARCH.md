# Phase 4: M3 dbt Warehouse - Research

**Researched:** 2026-07-23
**Domain:** dbt-duckdb transformation layer (external parquet sources → staging views → mart tables), dbt testing mechanics, DuckDB timestamp/timezone semantics
**Confidence:** HIGH for project facts and package versions (read directly from committed files / `pip index versions`, per `classify-confidence`). MEDIUM-to-LOW for the dbt-duckdb mechanical patterns: no `context7`/`ref`/`jina`/`firecrawl` MCP tool was available in this session's toolset, so all external-doc research used `WebSearch`/`WebFetch`, which `gsd-tools query classify-confidence` rates **LOW** regardless of source authority (only `context7`/`ref`/`jina`/`firecrawl` are rated MEDIUM by the seam). The `[CITED: url]` tags below are truthful about *provenance* (these are excerpts from official dbt/DuckDB documentation pages, not training-data guesses) but per the seam's tier, treat every pattern/code shape in this document as **not yet mechanically verified** — the planner's tasks must include running `dbt build` against real data as the actual verification step, not just trusting this document.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Real-data close boundary (Area A):**
- **D-01:** Split by environment. CI blocking gate = `dbt build` green on the synthesized fixture warehouse (network-free, deterministic, <5 min, T3.06). Real-data `dbt build` is run in-phase locally (real data already present 2019→2024). Phase closes only when BOTH are green (SC#1 real + SC#3 CI fixtures).
- **D-02:** Real-data checkpoint commits a human-readable build report at `reports/warehouse/dbt_build_<date>.md` (models built; test pass/fail counts; key sanity numbers — per-year hourly row counts, month coverage, 2022-08 reconciliation delta). Mirrors `reports/ingestion/validation_*.md`. `data/warehouse/epra.duckdb` stays gitignored (DM-001); `git status` must stay clean of `data/`.

**CI fixture bootstrap (Area B — SG-06, T3.06):**
- **D-03:** Fixture warehouse spans a contiguous window including every spec-hardcoded test date — minimum **2022-01-01 → 2024-12-31** — so DM-062, DM-064, DM-065, DM-050 all run UNMODIFIED with spec-literal dates.
- **D-04:** `scripts/bootstrap_fixture_warehouse.py` synthesizes rows programmatically at CI time (seeded/deterministic) and writes `data/raw/**` + `data/processed/**` parquet — does NOT copy committed multi-MB parquet. Synthetic values crafted to pass DM-061 accepted ranges and the DM-064 reconciliation. Deviates from WBS T3.06's "from `tests/fixtures/` parquet" wording → recorded in ADR-010 (SG-06 adoption).

**Future-mart stand-ins (Area C — SG-06, SG-05, DM-050/DM-063):**
- **D-05:** `fct_consumer_load_hourly` and `fct_procurement_cost_monthly` are never disabled (SG-06). They build off full-window, valid, environment-aligned stand-in parquet: consumer load = hourly valid MWh over the window; procurement cost = every month × all 6 strategy_ids (S1, S2, S3, S4_30, S4_50, S4_70) with valid costs. Makes DM-050, DM-063, DM-060 pass unmodified on both marts.
- **D-06:** Stand-in window matches the surrounding data window per environment — real 2019→latest locally, synthetic 2022–2024 in CI — so the DM-050 generated month-spine aligns with other monthly marts. `data/processed/` is empty even locally, so the same stand-in mechanism feeds the local real-data build too, not just CI, until M4/M6 produce real files. Build report (D-02) flags these two marts as "stand-in (M4/M6 pending)."

**Contract & ADR governance (Area D — SG-05, T3.05):**
- **D-07:** `dbt/contracts/marts_contract.yml` is hand-authored from SPEC-02 §5 + the SG-05 enumeration, covering all 6 marts. SG-05's frozen enumeration for `fct_price_hourly` = the ING-110 calendar list (`date_local, year_local, month_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour`) + `season, hdd_18, cdd_22`. The T3.05 schema-contract test diff-checks `information_schema.columns` against this human-reviewed, spec-derived YAML. SG-05 needs no ADR — the committed contract YAML IS its adoption.
- **D-08:** Three single-topic ADRs (confirm next-free numbers against `docs/ADR/` at planning time — verified this session: **ADR-009/010/011 are free**):
  - **ADR-009** — SG-13 `generate_schema_name` override macro so schemas are literally `staging`/`marts`.
  - **ADR-010** — SG-06 CI-fixture synthesis + environment-aligned stand-in policy (includes D-04's generated-at-CI deviation and D-05/D-06's stand-in-feeds-local-build decision).
  - **ADR-011** — SG-14 holiday-aware peak (`is_peak_hour`, ING-110) used everywhere for `price_peak_eur_mwh` + anchors, plus a note that ÖSPI's own peak convention may treat holidays differently → also add a LIMITATIONS.md §2 entry.

### Claude's Discretion
- **Operator interface:** naming/Makefile wiring for the real-data build wrapper — "Makefile as canonical operator interface" is locked PROJECT.md policy; exact target names are the implementer's choice. **Research finding: the Makefile already has a stubbed `transform:` target wired into `all:`/`refresh:` — use it, don't invent a new name** (see Summary).
- **Month-spine test mechanism** (DM-050): custom SQL spine macro vs a `dbt_utils` dependency — planner/researcher decides; if a package dep is added, note it (minimal footprint preferred). **Research recommendation: skip dbt_utils, hand-roll the spine macro** (see Standard Stack → Alternatives Considered).
- Model/macro decomposition, SQL style, staging CTE structure, synthetic-generator internals, seed/relationship-test scaffolding layout — implementer's choice within the SPEC-02 contracts and DM-xxx model-YAML citations (W-2), consistent with M1/M2.
- Fixture-generator determinism knobs (seed value, exact synthetic curve shape) — free, provided all DM-060..066 pass.

### Deferred Ideas (OUT OF SCOPE)
- BI exports — `scripts/export_marts.py`, `make export`, SPEC-02 §7 CSVs and their DM-070 contract tests → M7/Phase 8. Power BI reads only from `exports/`, never DuckDB.
- Real consumer-load parquet replacing the D-05 consumer stand-in → M4/Phase 5 (SPEC-03).
- Real procurement-cost parquet replacing the D-05 procurement stand-in → M6/Phase 7 (SPEC-05).
- DM-066 freshness gate is refresh-only (`make refresh`, scheduled runs) → wired now but exercised at M7 monthly refresh, not in normal `dbt build`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| REQ-DWH-01 | `dbt build` green on real data and CI fixtures; mart schemas byte-match SPEC-02 §5 contract YAML (M3) | Standard Stack (verified dbt-core/dbt-duckdb/duckdb versions), Architecture Patterns 1–7 (sources.yml external parquet, schema-name macro, month-spine/accepted-range macros, DM-06x singular test SQL shapes, D-07 pytest contract diff, D-04 CI bootstrap), Validation Architecture (full DM-060..066 → test map), Common Pitfalls 1–6 (relative paths, schema-macro tradeoff, contract-file discoverability, sub-hourly aggregation, TIMESTAMPTZ consistency, union_by_name) |
</phase_requirements>

## Summary

This is a **spec-supremacy** phase: SPEC-02 (DM-001..070) already locks every model name, grain, column, and test; WBS §M3 already locks the task shape (T3.01–T3.07); CONTEXT.md's D-01..D-08 already lock the fixture/CI/stand-in/ADR strategy. Nothing here re-derives those. What genuinely needed research is the **dbt-duckdb mechanical HOW**: how external parquet sources are wired without copying files, how to defeat dbt's default schema-prefixing behavior, how to shape the DM-060..066 tests as runnable SQL, and how to keep the CI fixture job genuinely network-free.

The codebase check that mattered most: `dbt/dbt_project.yml`, `profiles.yml`, and `seeds/dim_strategy.csv` are **already committed and correct** — dbt runs from `dbt/` (profiles.yml uses `../data/warehouse/epra.duckdb`, so parquet globs in `sources.yml` need the same `../data/raw/...` relative prefix). The Makefile **already has a stubbed `transform` target** wired into `all:` and `refresh:` — the planner should un-stub it, not invent a new operator-interface name (CONTEXT.md's "Claude's Discretion" framing of this as fully open is slightly stale; the skeleton already answered it).

The three genuinely non-obvious mechanics are: (1) `generate_schema_name` must be overridden to **omit** `default_schema` — which is the exact opposite of dbt's own documented "correct" pattern (dbt's docs warn against this for multi-dev environments, but SG-13/DM-003 deliberately wants it because this is a single-target, single-developer local warehouse); (2) `dbt/contracts/marts_contract.yml` sits **outside** `model-paths` (`dbt_project.yml` only globs `models/`), which means it cannot be a native dbt `contract: {enforced: true}` block — it is necessarily consumed by a **Python-side (pytest) diff test** against `information_schema.columns`, not a dbt-native mechanism; (3) `read_parquet` is core-bundled DuckDB (no extension autoinstall/network needed), and since DM-011 forbids any dbt model from calling TZ conversion functions, the ICU extension is never needed either — the CI fixture job can be genuinely network-free with zero extension-loading risk.

**Primary recommendation:** Skip `dbt_utils` entirely (zero dbt package dependencies, consistent with the project's lean-repo/no-external-kit posture, ADR-001). Hand-roll a ~10-line `month_spine` macro using DuckDB's native `generate_series`, and hand-roll a `test_accepted_range` generic test macro. Implement DM-060..066 as a mix of dbt generic tests (schema.yml `unique`/`not_null`/`accepted_range`/`relationships`) and 4 singular `.sql` tests in `dbt/tests/` (row-count, reconciliation, DST, no-gap spine). Implement the D-07 schema-contract check as a pytest test reading `information_schema.columns` via `epra.common.db.connect(read_only=True)`, diffed against a PyYAML-parsed `dbt/contracts/marts_contract.yml`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Raw parquet exposure (DM-004) | Database / Storage (DuckDB `sources.yml`, `read_parquet`) | — | dbt-duckdb reads files directly as external relations; no separate ingestion step |
| Hourly/dedup aggregation (staging) | Database / Storage (dbt SQL views) | — | Pure SQL transforms over the raw layer; no Python involved |
| Local-calendar attribute join (`dim_calendar`) | Database / Storage (dbt) | Backend/Python (upstream: `calendar.py` already computed the values) | DM-011 forbids dbt from computing TZ attributes itself — it only joins pre-computed values |
| Mart materialization (`fct_*`, `dim_*`) | Database / Storage (dbt tables) | — | Analytics/strategies modules (M5/M6, future phases) read these as the sole warehouse interface |
| DM-060..066 test execution | Database / Storage (dbt `test`/`build`) | — | Runs inside `dbt build`'s DAG-ordered execution |
| Schema-contract diff (D-07) | Backend/Python (pytest) | Database / Storage (queries `information_schema`) | `dbt/contracts/marts_contract.yml` lives outside `model-paths`; only a Python-side reader can consume it |
| CI fixture synthesis (D-04) | Backend/Python (`scripts/bootstrap_fixture_warehouse.py`) | Database / Storage (writes parquet dbt then reads) | Determinism/seeding logic is Python; dbt only ever reads the resulting files |
| Build report (D-02) | Backend/Python (new script, `db.connect(read_only=True)`) | Database / Storage (source of the sanity numbers) | Mirrors the `GateResult`/`ValidationReport` pattern from M1/M2's `validate.py` |
| Operator entrypoint | Backend/Python (Makefile `transform:` target, already stubbed) | — | Already wired into `all:`/`refresh:`; just needs its body filled in |

## Standard Stack

### Core
| Library | Version (pinned/resolved) | Purpose | Why Standard |
|---------|------|---------|--------------|
| `dbt-core` | `>=1.8,<2` in `pyproject.toml`; **resolved 1.12.0** in `uv.lock` [VERIFIED: uv.lock] | Transformation orchestration, DAG execution, testing framework | Industry-standard SQL transformation tool; already the project's chosen stack (SPEC-02 DM-002) |
| `dbt-duckdb` | `>=1.8,<2` in `pyproject.toml`; **resolved 1.10.1** in `uv.lock` [VERIFIED: uv.lock] | dbt adapter targeting DuckDB, incl. external-file source support | Only maintained dbt adapter for DuckDB; maintained under the `duckdb` GitHub org (was `jwills/dbt-duckdb`, now transferred) |
| `duckdb` | `>=1.0` in `pyproject.toml`; **resolved 1.5.4** in `uv.lock` [VERIFIED: uv.lock] | Embedded OLAP engine, the warehouse file itself | Already the project's DB (DM-001); `epra.common.db.connect()` already uses it |

**All three are already locked in the committed `uv.lock`** — this phase does not add a new dependency, it activates one already resolved since project bootstrap. `pip index versions` confirms current PyPI latest: `dbt-core` 1.12.0, `dbt-duckdb` 1.10.1, `duckdb` (Python package) 1.5.5 — the pinned/resolved versions are current, not stale. [VERIFIED: pip index versions, run 2026-07-23]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyyaml` | already a transitive dep via dbt-core | Parse `dbt/contracts/marts_contract.yml` in the pytest schema-contract test | Only needed if not already importable — dbt-core vendors/depends on a YAML library; confirm importability at T3.05, don't add a new pin if avoidable |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `month_spine` macro | `dbt_utils.date_spine` | `dbt_utils` requires a `packages.yml` + `dbt deps` step (extra CI step, extra network call during `dbt deps`, extra footprint) for one ~10-line capability DuckDB's native `generate_series` already provides. **Recommendation: skip dbt_utils.** [ASSUMED — recommendation, not spec-mandated; CONTEXT.md leaves this to planner/researcher discretion] |
| Hand-rolled `test_accepted_range` generic test | `dbt_utils.accepted_range` | Same package-footprint tradeoff; the macro is ~15 lines and DM-061's four range checks are simple enough not to justify a dependency |
| pytest-based `information_schema` diff test (D-07) | dbt native `contract: {enforced: true}` | Native contracts require declaring `data_type` for every column inside the model's own `schema.yml`, duplicating what `dbt/contracts/marts_contract.yml` already declares, AND the contract file lives outside `model-paths` so dbt would never discover it there anyway. Native contracts also only catch drift at `dbt run` compile time for the contracted model, not as a standalone diff-checkable artifact reviewers can eyeball. **Recommendation: pytest diff test, per D-07's implied design.** |

**Installation:** none required — `uv sync` already resolves all three core packages from the existing `pyproject.toml` pins. No `pip install`/`uv add` step needed in this phase's tasks.

**Version verification:** confirmed via `pip index versions dbt-core|dbt-duckdb|duckdb` (2026-07-23) and cross-checked against `uv.lock`'s resolved versions — all match and are current, not stale relative to PyPI.

## Package Legitimacy Audit

| Package | Registry | Age (per tool) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `dbt-core` | pypi | latest release 2026-07-16 | unknown (API returned null) | `github.com/dbt-labs/dbt-core` | SUS (`too-new`, `unknown-downloads`) | **Approved** — false positive, see note |
| `dbt-duckdb` | pypi | latest release 2026-02-17 | unknown (API returned null) | `github.com/jwills/dbt-duckdb` (canonical repo now `github.com/duckdb/dbt-duckdb`) | SUS (`unknown-downloads`) | **Approved** — false positive, see note |
| `duckdb` | pypi | latest release 2026-07-22 | unknown (API returned null) | `github.com/duckdb/duckdb-python` | SUS (`too-new`, `unknown-downloads`) | **Approved** — false positive, see note |

**Note on the SUS verdicts:** `gsd-tools query package-legitimacy check` flags `publishedAt` = the *latest version's* release date, not the package's original creation date, and its downloads API returned `null` for all three (no data, not zero). All three are foundational, canonical-maintainer packages (dbt Labs' own core product; DuckDB Labs' own official Python bindings; DuckDB org's own official dbt adapter) that were **already declared in `pyproject.toml` and already resolved in the committed `uv.lock` since project bootstrap (M0)** — this phase is the first to *invoke* them, not the first to *install* them. No `postinstall` script flagged on any of the three. Given canonical maintainer + existing lockfile resolution + no postinstall risk, these are treated as approved without a `checkpoint:human-verify` gate. The planner may add one if the operator wants extra caution before running `dbt build` for the first time, but it is not required by this research.

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `dbt-core`, `dbt-duckdb`, `duckdb` — all dispositioned "Approved" per the note above (pre-existing pinned/locked dependencies, canonical maintainers, no postinstall risk).

*`dbt_utils` was investigated as a candidate dependency (see Alternatives Considered) but is **not recommended for adoption** — no legitimacy check was run because the recommendation is not to add it.*

## Architecture Patterns

### System Architecture Diagram

```
data/raw/**/*.parquet  ─────┐
data/manual/oespi_monthly.csv ┤
data/raw/calendar/calendar.parquet ┤
data/processed/**/*.parquet (M4/M6 stand-ins, D-05/D-06) ┘
        │  read_parquet() / read_csv(), ONE glob per source (DM-004)
        ▼
┌─────────────────────────────┐
│ dbt/models/sources.yml       │  schema: raw (external view over files)
└──────────────┬───────────────┘
               │ ref()/source()
               ▼
┌─────────────────────────────┐
│ dbt/models/staging/stg_*.sql │  schema: staging, materialized: view
│  - dedup (qualify row_number)│
│  - 15-min → hourly MEAN      │
│  - rename/passthrough        │
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────────┐
│ dim_calendar, dim_strategy   │  schema: marts, materialized: table
│  (join weather, season rule) │  (dim_strategy = dbt seed)
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────────┐
│ dbt/models/marts/fct_*.sql   │  schema: marts, materialized: table
│  fct_price_hourly/daily/     │
│  monthly, fct_generation_    │
│  monthly, fct_consumer_load_ │
│  hourly, fct_procurement_    │
│  cost_monthly                │
└──────────────┬───────────────┘
               │  dbt build runs generic + singular tests
               │  in DAG order after each layer materializes
               ▼
┌─────────────────────────────┐      ┌──────────────────────────────┐
│ data/warehouse/epra.duckdb   │─────▶│ epra.common.db.connect(      │
│ (gitignored, DM-001)         │      │   read_only=True)            │
└───────────────────────────────┘      │  → pytest schema-contract    │
                                        │    test (info_schema diff)   │
                                        │  → M5/M6 analytics (future)  │
                                        └──────────────────────────────┘
```

### Recommended Project Structure
```
dbt/
├── dbt_project.yml          # already committed — do not touch materialization/schema config
├── profiles.yml             # already committed — relative path from dbt/
├── seeds/
│   └── dim_strategy.csv     # already committed
├── models/
│   ├── sources.yml          # NEW — T3.01: one entry per raw dataset, read_parquet globs
│   ├── staging/
│   │   ├── stg_prices_at_native.sql
│   │   ├── stg_prices_delu_native.sql
│   │   ├── stg_prices_at_hourly.sql
│   │   ├── stg_prices_delu_hourly.sql
│   │   ├── stg_load_at_hourly.sql
│   │   ├── stg_gen_at_hourly.sql
│   │   ├── stg_weather_graz_daily.sql
│   │   ├── stg_oespi_monthly.sql
│   │   └── staging.yml       # generic tests (unique/not_null/accepted_range) for staging grain keys
│   └── marts/
│       ├── dim_calendar.sql
│       ├── fct_price_hourly.sql
│       ├── fct_price_daily.sql
│       ├── fct_price_monthly.sql
│       ├── fct_generation_monthly.sql
│       ├── fct_consumer_load_hourly.sql
│       ├── fct_procurement_cost_monthly.sql
│       └── marts.yml         # generic tests (unique/not_null/accepted_range/relationships) for mart grain keys
├── macros/
│   ├── generate_schema_name.sql   # NEW — T3.01, SG-13/ADR-009
│   ├── month_spine.sql            # NEW — T3.04/T3.05, DM-050 helper
│   └── test_accepted_range.sql    # NEW — T3.05, DM-061 generic test (hand-rolled, no dbt_utils)
├── tests/
│   ├── fct_price_hourly_row_count_per_year.sql   # DM-062
│   ├── reconcile_price_monthly_2022_08.sql       # DM-064
│   ├── dst_hour_counts_fct_price_hourly.sql      # DM-065
│   └── no_gap_fct_price_monthly.sql              # DM-050 (also applies to fct_generation_monthly, fct_procurement_cost_monthly)
└── contracts/
    └── marts_contract.yml    # NEW — T3.05, D-07: hand-authored, lives OUTSIDE model-paths on purpose

scripts/
└── bootstrap_fixture_warehouse.py   # NEW — T3.06, D-04

reports/warehouse/
└── dbt_build_<date>.md              # NEW — T3.05/T3.07 build-report script output, D-02

tests/unit/
└── test_marts_contract.py           # NEW — T3.05: pytest diff test consuming dbt/contracts/marts_contract.yml
```

### Pattern 1: External source via `read_parquet` glob (DM-004)
**What:** Every raw dataset is exposed exactly once in `sources.yml` via `meta.external_location` (or per-table `config.external_location`) pointing at a `read_parquet('...')` glob. No other model touches `data/raw/**` directly.
**When to use:** For every one of the M1/M2 raw datasets (`entsoe_prices_at`, `entsoe_prices_delu`, `entsoe_load_at`, `entsoe_gen_at`, `geosphere_graz_daily`, `calendar`) plus the M4/M6 stand-in parquet in `data/processed/` and the manual `oespi_monthly.csv`.
**Example:**
```yaml
# dbt/models/sources.yml
# Source: https://github.com/duckdb/dbt-duckdb README (external source config: meta.external_location)
version: 2

sources:
  - name: raw
    meta:
      external_location: "read_parquet('../data/raw/{name}/**/*.parquet', union_by_name=true)"
    tables:
      - name: entsoe_prices_at
      - name: entsoe_prices_delu
      - name: entsoe_load_at
      - name: entsoe_gen_at
      - name: geosphere_graz_daily

  - name: raw_calendar
    tables:
      - name: calendar
        meta:
          external_location: "read_parquet('../data/raw/calendar/calendar.parquet')"

  - name: raw_manual
    tables:
      - name: oespi_monthly
        meta:
          external_location: "read_csv('../data/manual/oespi_monthly.csv', header=true)"

  - name: raw_processed
    meta:
      external_location: "read_parquet('../data/processed/{name}/**/*.parquet', union_by_name=true)"
    tables:
      - name: consumer_load_hourly
      - name: procurement_cost_monthly
```
Two landmines to flag in the model itself:
1. **`../` prefix is mandatory** — dbt runs from `dbt/` (per `profiles.yml`'s own comment), so a bare `data/raw/...` glob resolves relative to the `dbt/` directory and silently returns zero rows, not an error, if the path doesn't exist ambiguously (DuckDB's `read_parquet` on a genuinely empty glob raises; a *wrong but non-empty* relative path is the dangerous case — verify with a `dbt build --select sources.raw.entsoe_prices_at` smoke check before building further).
2. **`union_by_name=true`** is not spec-mandated but is a defensive default: monthly parquet files across years/months are all written by the same `_io.write_month` path so schemas should already be identical (ING-070 contract-tested at ingest time) — but it costs nothing to add and protects against any future column-order drift. [ASSUMED — reasonable engineering default, not verified against a real schema-drift scenario in this session]

`[CITED: github.com/duckdb/dbt-duckdb README — external source meta.external_location / read_parquet syntax]`

### Pattern 2: `generate_schema_name` override — literal schema names (SG-13 / ADR-009)
**What:** dbt's default `generate_schema_name` macro concatenates `<target_schema>_<custom_schema>` (e.g. `main_staging`) to avoid dev/CI schema collisions across developers sharing one warehouse. DM-003 wants schemas literally named `staging`/`marts`. Overriding requires **omitting** `default_schema` from the returned value — which dbt's own docs explicitly warn against for shared environments, but which is safe here because `profiles.yml` defines exactly one `dev` target against one local file, with no shared/concurrent-developer warehouse.
**When to use:** Once, project-wide, in `dbt/macros/generate_schema_name.sql`.
**Example:**
```sql
-- dbt/macros/generate_schema_name.sql
-- Source: https://docs.getdbt.com/docs/build/custom-schemas (the pattern the docs
-- label "incorrect" for shared dev/CI — deliberately adopted here per SG-13/ADR-009
-- because this project has exactly one local target, no shared warehouse).
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```
With `dbt_project.yml`'s existing `+schema: staging` / `+schema: marts` configs, this yields DuckDB schemas literally named `staging` and `marts` — verify via `select schema_name from information_schema.schemata;` (T3.01 AC).
`[CITED: docs.getdbt.com/docs/build/custom-schemas]`

### Pattern 3: Hand-rolled month spine (DM-050) — no `dbt_utils`
**What:** A macro generating one row per local calendar month between the min and max month present in a mart, using DuckDB's native `generate_series` over `date_trunc('month', ...)`. Anti-joined against the mart's distinct months to find gaps.
**When to use:** `fct_price_monthly`, `fct_generation_monthly`, and `fct_procurement_cost_monthly` (D-05/D-06 mandate these are gap-free across the stand-in window too).
**Example:**
```sql
-- dbt/macros/month_spine.sql
-- Source: DuckDB docs — generate_series(TIMESTAMP, TIMESTAMP, INTERVAL);
-- pattern adapted from community DuckDB date-range idioms (no dbt_utils dependency).
{% macro month_spine(min_month_expr, max_month_expr) %}
    select unnest(
        generate_series(
            date_trunc('month', {{ min_month_expr }}),
            date_trunc('month', {{ max_month_expr }}),
            interval '1 month'
        )
    )::date as month_local
{% endmacro %}
```
```sql
-- dbt/tests/no_gap_fct_price_monthly.sql
-- DM-050: monthly marts cover every month in the analysis window, no gaps.
with actual as (
    select make_date(year_local, month_local, 1) as month_local
    from {{ ref('fct_price_monthly') }}
),
spine as (
    {{ month_spine("(select min(month_local) from actual)", "(select max(month_local) from actual)") }}
)
select spine.month_local
from spine
left join actual using (month_local)
where actual.month_local is null
```
`[CITED: duckdb.org/docs — generate_series/date_trunc]` `[ASSUMED — macro composition style, not copy-pasted from an official source]`

### Pattern 4: Hand-rolled `accepted_range` generic test (DM-061) — no `dbt_utils`
**What:** A generic test macro following dbt's `test_<name>(model, column_name, ...)` signature convention, returning failing rows outside `[min_value, max_value]`.
**Example:**
```sql
-- dbt/macros/test_accepted_range.sql
-- Source: pattern per docs.getdbt.com/best-practices/writing-custom-generic-tests
{% test accepted_range(model, column_name, min_value=none, max_value=none) %}
select *
from {{ model }}
where
    {% if min_value is not none %} {{ column_name }} < {{ min_value }} {% endif %}
    {% if min_value is not none and max_value is not none %} or {% endif %}
    {% if max_value is not none %} {{ column_name }} > {{ max_value }} {% endif %}
{% endtest %}
```
```yaml
# dbt/models/marts/marts.yml (excerpt)
models:
  - name: fct_price_hourly
    columns:
      - name: price_at_eur_mwh
        tests:
          - accepted_range: {min_value: -500, max_value: 5000}
```
`[CITED: docs.getdbt.com/best-practices/writing-custom-generic-tests]`

### Pattern 5: Singular tests for DM-062/064/065 (spec-literal SQL shapes)
```sql
-- dbt/tests/fct_price_hourly_row_count_per_year.sql — DM-062
with counts as (
    select
        year_local,
        count(*) as n_hours,
        case
            when year_local % 4 = 0 and (year_local % 100 != 0 or year_local % 400 = 0)
            then 8784 else 8760
        end as expected_hours
    from {{ ref('fct_price_hourly') }}
    group by year_local
)
select *
from counts
where abs(n_hours - expected_hours) > 24
```
```sql
-- dbt/tests/reconcile_price_monthly_2022_08.sql — DM-064 (hardcoded per SPEC-02 §6, deliberately not parametrized)
with hourly_mean as (
    select avg(price_at_eur_mwh) as mean_price
    from {{ ref('fct_price_hourly') }}
    where year_local = 2022 and month_local = 8
),
monthly as (
    select price_base_eur_mwh
    from {{ ref('fct_price_monthly') }}
    where year_local = 2022 and month_local = 8
)
select monthly.price_base_eur_mwh, hourly_mean.mean_price
from monthly, hourly_mean
where abs(monthly.price_base_eur_mwh - hourly_mean.mean_price) > 0.01
```
```sql
-- dbt/tests/dst_hour_counts_fct_price_hourly.sql — DM-065 (hardcoded per SPEC-02 §6)
with expected(date_local, expected_hours) as (
    values (date '2024-03-31', 23), (date '2024-10-27', 25)
),
actual as (
    select date_local, count(*) as n_hours
    from {{ ref('fct_price_hourly') }}
    where date_local in (date '2024-03-31', date '2024-10-27')
    group by date_local
)
select expected.date_local, expected.expected_hours, actual.n_hours
from expected
join actual using (date_local)
where actual.n_hours != expected.expected_hours
```
All three are `[ASSUMED — SQL shape derived directly from the DM-06x spec text, not copy-pasted from any external source]` but mechanically follow the verified `[CITED]` singular-test convention (a `.sql` file in `test-paths` returning failing rows = a data test).

### Pattern 6: Schema-contract diff test (D-07) — pytest, not dbt-native
**What:** `dbt/contracts/marts_contract.yml` is deliberately placed **outside** `model-paths: ["models"]` (per the committed `dbt_project.yml`), so dbt itself never discovers or validates it — confirming this is meant to be read by an external tool, not dbt's own `contract: {enforced: true}` mechanism (which would require the same enumeration duplicated inside each model's own `schema.yml`).
**Example:**
```python
# tests/unit/test_marts_contract.py (illustrative shape)
import duckdb
import yaml

from epra.common.config import load_settings
from epra.common.db import connect

def test_marts_schema_matches_contract():
    settings = load_settings()
    contract = yaml.safe_load(
        (REPO_ROOT / "dbt" / "contracts" / "marts_contract.yml").read_text()
    )
    with connect(settings, read_only=True) as con:
        actual = con.execute(
            "select table_name, column_name, data_type "
            "from information_schema.columns "
            "where table_schema = 'marts' "
            "order by table_name, ordinal_position"
        ).fetchall()
    # diff `actual` against `contract`'s per-model column/type enumeration;
    # fail with a readable diff naming the model + offending column.
```
`[ASSUMED — test shape inferred from D-07's wording + the model-paths placement fact, not an official documented pattern]`

### Pattern 7: Freshness (DM-066) — refresh-only, gated by a dbt var
**What:** dbt's native `dbt source freshness` command only operates on `sources:` blocks with `loaded_at_field`/`freshness:` config and is a **separate command** from `dbt build` — it does not fit DM-066's requirement to check freshness on `stg_prices_at_hourly` (a staging **model**, not a raw source). WBS T3.05 hints at this too ("freshness ... via `dbt build --select ... --vars`"). The idiomatic fit is a singular test **disabled by default**, enabled only when a dbt var is set — so `make transform` (normal `dbt build`) never runs it, but `make refresh` can pass the var.
**Example:**
```sql
-- dbt/tests/freshness_stg_prices_at_hourly.sql — DM-066, wired now, exercised at M7
{{ config(enabled=var('check_freshness', false)) }}

select max(ts_utc) as newest_ts_utc
from {{ ref('stg_prices_at_hourly') }}
having max(ts_utc) < current_timestamp - interval '40 days'
```
Invoked at refresh time as `dbt build --vars '{check_freshness: true}'`. `[ASSUMED — inferred from WBS T3.05's own wording; not verified against an official "conditional singular test" recipe]`

### Anti-Patterns to Avoid
- **Copying raw parquet into `dbt/seeds/` or hand-writing INSERT statements for fixtures:** D-04 explicitly requires `bootstrap_fixture_warehouse.py` to *synthesize* rows programmatically at CI time, not commit multi-MB parquet — keeps the repo lean (D-04).
- **Any dbt model calling `AT TIME ZONE`, `EXTRACT` on a TZ-aware column independently, or otherwise deriving local calendar attributes itself:** DM-011 is explicit — ALL local attributes come from `dim_calendar` only. This also means the project never needs to load DuckDB's ICU extension, keeping the CI fixture job's "no network" guarantee simple to keep (parquet reading is core-bundled; no extension autoinstall required).
- **Running `bootstrap_fixture_warehouse.py` against a populated `data/` without a `--force`/guard flag:** per `03_MODULES.md`'s own module contract for this script — it must refuse to clobber real ingested data by default.
- **Adding `dbt_utils` "just in case":** every DM-06x test this phase needs has a ≤15-line hand-rolled equivalent; the package adds a `packages.yml` + `dbt deps` step and a network dependency during that step, which cuts against the CI job's network-free goal and the project's lean-repo posture.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| DAG-ordered build+test+seed execution | A custom Python orchestrator calling `dbt run` then `dbt test` then `dbt seed` in the right order | `dbt build` (single command) | `dbt build` already runs seeds, models, snapshots, and tests together in dependency order, failing fast and skipping downstream nodes when an upstream test fails — reimplementing this ordering logic is pure risk for zero benefit `[CITED: docs.getdbt.com/reference/commands/build]` |
| External-file access from Python-side glue | A pandas/pyarrow script that pre-reads `data/raw/**` and writes intermediate CSVs for dbt to ingest | `read_parquet()` directly in `sources.yml` | DuckDB reads Parquet natively and efficiently; adding a Python pre-processing step duplicates DM-004's single-glob-per-source contract and creates a second place duplicates/dtype drift can creep in |
| Schema drift detection | A bespoke ORM/schema-comparison library | `information_schema.columns` (already a first-class DuckDB catalog view) + a small pytest diff | DuckDB's `information_schema` is standard SQL; no library needed to query it |

**Key insight:** dbt-duckdb's whole value proposition here is that it eliminates a "load parquet into the warehouse" step entirely — sources are *views over files*, not copies. Any pattern that reintroduces a materialize-then-transform two-step for the raw layer defeats DM-004's explicit "no other model touches files directly" contract.

## Common Pitfalls

### Pitfall 1: Relative-path mismatch between `dbt/` cwd and `data/`
**What goes wrong:** `sources.yml` globs written as `data/raw/...` (repo-root-relative) instead of `../data/raw/...` silently resolve against `dbt/` as cwd and either error (`read_parquet` on a truly nonexistent path raises) or, worse, ambiguously match nothing while a model built on top of it materializes to zero rows without an obvious build failure.
**Why it happens:** `profiles.yml`'s own comment says "Run dbt from the `dbt/` directory" — but it's easy to write source paths assuming repo-root as cwd (as ingestion Python code does via `_dataset_root`).
**How to avoid:** Every `external_location` in `sources.yml` must be prefixed `../data/...`, matching `profiles.yml`'s own `path: ../data/warehouse/epra.duckdb`. Verify with a `dbt build --select sources.raw.<name>` smoke check (T3.01's stated AC) before layering staging models on top.
**Warning signs:** A staging/mart model builds "successfully" but returns 0 rows.

### Pitfall 2: Native `generate_schema_name` override breaks CI/dev isolation if ever multi-environment
**What goes wrong:** The SG-13 override (Pattern 2) returns `custom_schema_name` literally, discarding `target.schema`. dbt's own docs call this out as dangerous for shared dev/CI databases — a second developer or a second CI run targeting the *same* DuckDB file would silently overwrite the first's `staging`/`marts` schemas.
**Why it happens:** This tradeoff is being deliberately accepted (ADR-009) because the project has exactly one local DuckDB file, one operator, and the CI fixture job builds a *fresh, ephemeral* file each run (never a shared persistent warehouse).
**How to avoid:** Do not generalize this macro's pattern to any future multi-target/multi-developer dbt project without revisiting the tradeoff. Document the acceptance explicitly in ADR-009 (already planned per D-08).
**Warning signs:** N/A for this project as scoped — becomes a real risk only if a shared/remote warehouse target is ever added.

### Pitfall 3: `dbt/contracts/marts_contract.yml` silently ignored by dbt
**What goes wrong:** Because it's placed outside `model-paths`, any attempt to make dbt "enforce" it directly (e.g., expecting `dbt build` to fail on a mismatched column without an explicit pytest step) will silently do nothing — dbt never reads that directory.
**Why it happens:** The file's location is a deliberate design choice (per D-07's phrasing: "the T3.05 schema-contract test diff-checks `information_schema.columns` against this ... YAML") but it's easy to *assume* dbt auto-validates any YAML under `dbt/`.
**How to avoid:** The schema-contract check MUST be a separate executable step (pytest test, per Pattern 6) that runs *after* `dbt build` populates the warehouse — wire it into the same Makefile/CI step sequence, not as a dbt config.
**Warning signs:** A renamed mart column doesn't fail anything until an analytics module downstream (M5/M6, future phases) breaks at read time.

### Pitfall 4: 15-minute vs 60-minute resolution mixed-month aggregation off-by-one
**What goes wrong:** SPEC-02 §3 already specifies "mixed months handled per-row by truncating ts to hour and averaging" for `stg_prices_at_hourly`/`stg_prices_delu_hourly` — a naive `GROUP BY date_trunc('hour', ts_utc)` without also tracking `n_subhours` correctly (1 for PT60M source rows, 4 for PT15M) will silently compute a correct *average* but lose the diagnostic `n_subhours` column the contract requires, which downstream tests (or a future analyst) may rely on to detect partial-hour aggregation.
**Why it happens:** The temptation is to write the simplest possible `avg(price_eur_mwh)` query and forget the accompanying `count(*) as n_subhours`.
**How to avoid:** Always select `count(*) as n_subhours` alongside the mean in the same `GROUP BY` — it's already in the exact §3 column contract, easy to check against the (planned, T3.05) staging schema test.
**Warning signs:** `n_subhours` missing from `stg_prices_at_hourly`/`stg_prices_delu_hourly` output — would be caught by T3.02's own AC ("column names/units match §3 exactly").

### Pitfall 5: TIMESTAMPTZ vs plain TIMESTAMP dtype mismatch across sources
**What goes wrong:** DuckDB's parquet reader promotes any tz-aware pandas `datetime64[ns, UTC]` column (written via pyarrow with `isAdjustedToUTC=true`) to `TIMESTAMP WITH TIME ZONE`. If any future dataset were ever written with a **naive** `ts_utc` column, joining it against the tz-aware `ts_utc` from other sources would either error on type mismatch or (worse) silently coerce, depending on DuckDB version.
**Why it happens:** Not a live bug today — `epra.ingest._io._validate_ts_utc_key` already rejects naive `ts_utc` at write time (ING-005), and `calendar.py` builds `ts_utc` tz-aware too — so all current raw parquet already has consistent `TIMESTAMP WITH TIME ZONE` semantics on read. This is a **confirmed non-issue for existing sources**, flagged here only as a regression risk if a new raw dataset is ever added without going through `_io.write_month`.
**How to avoid:** Any new raw dataset must continue to go through the existing `write_month`/`_validate_ts_utc_key` path (already enforced at ingest time, not a dbt concern).
**Warning signs:** A `JOIN ... USING (ts_utc)` between two sources returns zero rows despite both having data in the same window — check `information_schema.columns.data_type` for a `TIMESTAMP` vs `TIMESTAMP WITH TIME ZONE` mismatch.
`[CITED: github.com/duckdb/duckdb issues on isAdjustedToUTC/TIMESTAMPTZ parquet roundtrip behavior]`

### Pitfall 6: `union_by_name` needed if any monthly parquet ever has reordered columns
**What goes wrong:** DuckDB's `read_parquet` on a glob defaults to positional column matching across files; if any single month's file (e.g., an old fixture) has a different column order than the rest, rows silently get misaligned data instead of erroring.
**Why it happens:** All current files are written by the same `_io.write_month` code path so this is currently a non-issue, but globs are inherently fragile to any future manual file drop.
**How to avoid:** Always pass `union_by_name=true` in every `read_parquet(...)` glob in `sources.yml` (Pattern 1) — it's a no-cost defensive default.
**Warning signs:** A staging model's row count matches expectations but specific column values look implausible for certain months.

## Code Examples

Verified/derived patterns — see Patterns 1–7 above for the full, in-context code (kept together with their rationale rather than duplicated here).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| dbt `run` + `test` + `seed` as separate commands | `dbt build` (single command, DAG-ordered) | Introduced dbt-core 1.0 (2021), now the standard recommendation | This project should use `dbt build` exclusively (also SPEC-02 phrasing already implies this: "all must pass in `dbt build`") |
| dbt-duckdb targeting DuckDB <1.0 | dbt-duckdb 1.8+ targets DuckDB 1.x line | DuckDB 1.0 GA (2024) | Already reflected in this project's `>=1.0` pin; resolved 1.5.4 is well within the supported range |

**Deprecated/outdated:** none directly relevant surfaced in this session's search — dbt-duckdb's external-source `meta.external_location` mechanism used here has been stable across the 1.x line per the README fetched in this session.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `union_by_name=true` is a safe, cost-free default to add to every `read_parquet` glob | Pattern 1, Pitfall 6 | Low — if wrong, worst case is a slightly slower query; correctness only improves |
| A2 | The hand-rolled `month_spine`/`test_accepted_range` macro *syntax* (exact Jinja shape) is idiomatic but not copy-pasted from an official recipe | Patterns 3, 4 | Low-Medium — macros are simple enough to unit-verify at T3.04/T3.05 by running `dbt build` against real data; any syntax error surfaces immediately as a compile failure |
| A3 | DM-066 freshness is best implemented as a `var`-gated singular test rather than dbt's native `source freshness` command | Pattern 7 | Medium — if the planner disagrees, dbt's native `dbt source freshness` command could instead be pointed at the *source* (not the staging model), which would technically satisfy "freshness" but check a slightly different column set than DM-066's literal wording ("newest `ts_utc` in `stg_prices_at_hourly`"); worth a quick confirm at T3.05 planning |
| A4 | The schema-contract check (D-07) should be a pytest test, not a dbt-native contract | Pattern 6 | Low — grounded in a verifiable fact (`marts_contract.yml` sits outside `model-paths`), not speculation, but the *exact* pytest test shape is illustrative only |
| A5 | `dbt-core`/`dbt-duckdb`/`duckdb`'s SUS package-legitimacy flags are false positives (tool metadata quirk, not real risk) | Package Legitimacy Audit | Low — these are extremely well-known, canonical-maintainer packages already resolved in the committed `uv.lock`; independently corroborated via `pip index versions` and GitHub org ownership |

## Open Questions

1. **Does DM-066's freshness check need to run inside `dbt build --select ...` or as a fully separate `make refresh`-only step?**
   - What we know: WBS T3.05 says "freshness (refresh-only, DM-066 via `dbt build --select ... --vars`)" — implying it's still a `dbt build` invocation, just parametrized differently for the refresh Makefile target vs the normal `transform` target.
   - What's unclear: whether "wired now but exercised at M7" (CONTEXT.md Deferred Ideas) means T3.05 should write the test but leave it permanently `enabled=false` until M7 flips a var, or whether the `make refresh` target itself (not yet built — M7 territory per WBS) is what sets the var.
   - Recommendation: Write the singular test with `config(enabled=var('check_freshness', false))` now (default off, so normal `dbt build`/`make transform` never runs it); leave wiring `make refresh` to actually pass `--vars '{check_freshness: true}'` for M7, consistent with CONTEXT.md's explicit deferral.

2. **Exact YAML shape of `dbt/contracts/marts_contract.yml`**
   - What we know: SG-05 gives the frozen `fct_price_hourly` enumeration; SPEC-02 §5 gives the other five marts' column lists verbatim.
   - What's unclear: whether the pytest diff test should compare column **names only** or names **and** DuckDB `data_type` strings (e.g., `DOUBLE` vs `VARCHAR`) — the CONTEXT.md D-07 wording ("editing any mart column name/type breaks it") suggests type-inclusive.
   - Recommendation: Include both name and a normalized type in the contract YAML and the diff; DuckDB's `information_schema.columns.data_type` gives canonical type strings (`BIGINT`, `DOUBLE`, `VARCHAR`, `DATE`, `TIMESTAMP WITH TIME ZONE`, `BOOLEAN`) to standardize against.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `dbt-core` | All of M3 | ✓ | 1.12.0 (resolved, uv.lock) | — |
| `dbt-duckdb` | All of M3 | ✓ | 1.10.1 (resolved, uv.lock) | — |
| `duckdb` (Python) | `epra.common.db`, warehouse file | ✓ | 1.5.4 (resolved, uv.lock) | — |
| Network access | None required for `dbt build` (parquet reading is core-bundled DuckDB, no extension autoinstall) | ✓ (not needed) | — | — |
| `data/raw/**` real parquet | Local real-data `dbt build` (D-01) | ✓ | populated 2019→2024 per `.planning` state | — |
| `data/manual/oespi_monthly.csv` | `stg_oespi_monthly` | ✓ | reconciled, 92 months | — |
| `data/processed/**` (M4/M6 real outputs) | `fct_consumer_load_hourly`, `fct_procurement_cost_monthly` | ✗ (empty — M4/M6 not yet built) | — | D-05/D-06 stand-in parquet generator (same script feeds both local and CI) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `data/processed/**` real files — fallback is the D-05/D-06 stand-in generator, already locked as this phase's own deliverable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (Python glue) | pytest (existing project framework; `tests/unit/`) |
| Framework (warehouse) | dbt's own `build`/`test` framework (generic + singular tests) — not pytest |
| Config file | `dbt/dbt_project.yml` (already committed); no new pytest config needed |
| Quick run command (dbt) | `cd dbt && dbt build --select staging` (staging layer only, fast iteration) |
| Full suite command (dbt) | `cd dbt && dbt build` (full DAG: seeds → staging → marts → all tests) |
| Quick run command (pytest) | `uv run pytest tests/unit/test_marts_contract.py -x` |
| Full suite command (pytest) | `uv run pytest -m "not live"` (existing project-wide command, unchanged) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| REQ-DWH-01 (DM-004) | Raw parquet exposed once per source, no other model touches files | dbt build (source smoke) | `cd dbt && dbt build --select source:raw+` | ❌ Wave 0 (`sources.yml`) |
| REQ-DWH-01 (DM-003/SG-13) | Schemas literally `staging`/`marts` | manual query + dbt build | `cd dbt && dbt build && duckdb data/warehouse/epra.duckdb -c "select schema_name from information_schema.schemata"` | ❌ Wave 0 (`macros/generate_schema_name.sql`) |
| REQ-DWH-01 (DM-005/§3) | 8 staging models, exact columns | dbt generic tests (unique/not_null) + AC eyeball | `cd dbt && dbt build --select staging` | ❌ Wave 0 (`models/staging/*.sql`) |
| REQ-DWH-01 (DM-011/§4) | `dim_calendar` has no independent TZ calls; season/hdd/cdd correct | dbt build + singular spot-check | `cd dbt && dbt build --select dim_calendar` | ❌ Wave 0 (`models/marts/dim_calendar.sql`) |
| REQ-DWH-01 (DM-050/§5) | Marts no-gap, `price_peak_eur_mwh` NULL on no-peak days | dbt singular test | `cd dbt && dbt build --select marts` | ❌ Wave 0 (`tests/no_gap_*.sql`) |
| REQ-DWH-01 (DM-060) | unique/not_null on grain keys | dbt generic test | `cd dbt && dbt test --select tag:dm060` (or just `dbt build`) | ❌ Wave 0 (`models/*/*.yml`) |
| REQ-DWH-01 (DM-061) | Accepted ranges | dbt generic test (hand-rolled) | `cd dbt && dbt build` | ❌ Wave 0 (`macros/test_accepted_range.sql`) |
| REQ-DWH-01 (DM-062) | Row counts 8760/8784 ±24 | dbt singular test | `cd dbt && dbt build` | ❌ Wave 0 (`tests/fct_price_hourly_row_count_per_year.sql`) |
| REQ-DWH-01 (DM-063) | strategy_id FK → dim_strategy | dbt generic test (`relationships`, native) | `cd dbt && dbt build` | ❌ Wave 0 (`models/marts/marts.yml`) |
| REQ-DWH-01 (DM-064) | 2022-08 reconciliation | dbt singular test | `cd dbt && dbt build` | ❌ Wave 0 (`tests/reconcile_price_monthly_2022_08.sql`) |
| REQ-DWH-01 (DM-065) | DST hour counts | dbt singular test | `cd dbt && dbt build` | ❌ Wave 0 (`tests/dst_hour_counts_fct_price_hourly.sql`) |
| REQ-DWH-01 (DM-066) | Freshness, refresh-only | dbt singular test (var-gated, wired-only this phase) | `cd dbt && dbt build --vars '{check_freshness: true}'` (not exercised in normal build) | ❌ Wave 0 (`tests/freshness_stg_prices_at_hourly.sql`) |
| REQ-DWH-01 (D-07 contract) | Mart schemas byte-match SPEC-02 §5 | pytest | `uv run pytest tests/unit/test_marts_contract.py` | ❌ Wave 0 (`tests/unit/test_marts_contract.py`, `dbt/contracts/marts_contract.yml`) |
| REQ-DWH-01 (D-04 CI bootstrap) | `bootstrap_fixture_warehouse.py` synthesizes deterministic 2022-2024 window | pytest (script's own unit test, per module-contract split) | `uv run pytest tests/unit/test_bootstrap_fixture_warehouse.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd dbt && dbt build --select <changed_layer>` (e.g., `--select staging` while iterating staging models)
- **Per wave merge:** `cd dbt && dbt build` (full DAG) + `uv run pytest tests/unit/test_marts_contract.py tests/unit/test_bootstrap_fixture_warehouse.py`
- **Phase gate:** Both the local real-data `dbt build` (D-01) AND the CI fixture `dbt build` must be green (SC#1 + SC#3); schema-contract pytest green (SC#2)

### Wave 0 Gaps
- [ ] `dbt/models/sources.yml` — DM-004 external sources
- [ ] `dbt/macros/generate_schema_name.sql` — SG-13
- [ ] `dbt/macros/month_spine.sql`, `dbt/macros/test_accepted_range.sql` — DM-050/DM-061 helpers
- [ ] `dbt/models/staging/*.sql` (8) + `staging.yml` — §3
- [ ] `dbt/models/marts/dim_calendar.sql`, `dbt/models/marts/fct_*.sql` (6) + `marts.yml` — §4/§5
- [ ] `dbt/tests/*.sql` (4 singular tests) — DM-050/062/064/065/066
- [ ] `dbt/contracts/marts_contract.yml` — D-07
- [ ] `tests/unit/test_marts_contract.py` — D-07 pytest diff
- [ ] `scripts/bootstrap_fixture_warehouse.py` + its own unit test — D-04
- [ ] Build-report script (D-02) writing `reports/warehouse/dbt_build_<date>.md`
- [ ] `Makefile`'s `transform:` target body (currently a stub erroring out) — un-stub to `cd dbt && dbt build`
- [ ] `.github/workflows/ci.yml` `dbt-check` job (currently commented out at line 36) — add, wire as required

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surface — local single-operator CLI/warehouse, no network service |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Marginal — yes | `read_parquet`/`read_csv` glob paths are hardcoded in `sources.yml`, not derived from any external/user input; no injection surface. The one quasi-external input is `dbt/contracts/marts_contract.yml`, parsed with `yaml.safe_load` (never `yaml.load`) in the pytest test to avoid arbitrary object deserialization |
| V6 Cryptography | No | No secrets/credentials in this layer — `profiles.yml` already documented as credential-free (DM-002) |

### Known Threat Patterns for dbt-duckdb / local warehouse

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unsafe YAML deserialization of `marts_contract.yml` | Tampering (if the repo were ever compromised) | Always `yaml.safe_load`, never `yaml.load` with default `Loader` |
| `bootstrap_fixture_warehouse.py` accidentally overwriting real `data/raw/` | Repudiation / data loss (self-inflicted, not adversarial) | Module contract already mandates a guard/`--force` flag (`03_MODULES.md` line 262) — must be implemented, not skipped |
| `data/warehouse/epra.duckdb` accidentally committed to git | Information disclosure (low severity — no PII, but bloats repo) | Already gitignored per DM-001; verify `.gitignore` entry exists and `git status` stays clean per D-02 |

## Sources

### Primary (HIGH confidence)
- Project files (read directly this session): `docs/SPEC-02_data_model.md`, `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M3, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md`, `docs/EXECUTION_BLUEPRINT/03_MODULES.md`, `.planning/phases/EPRA-04-m3-dbt-warehouse/04-CONTEXT.md`, `dbt/dbt_project.yml`, `dbt/profiles.yml`, `dbt/seeds/dim_strategy.csv`, `dbt/README.md`, `src/epra/common/timeutil.py`, `src/epra/ingest/calendar.py`, `src/epra/ingest/_io.py`, `src/epra/common/db.py`, `Makefile`, `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`, `config/settings.yaml`
- `uv.lock` (resolved versions: dbt-core 1.12.0, dbt-duckdb 1.10.1, duckdb 1.5.4) — read directly
- `pip index versions dbt-core|dbt-duckdb|duckdb` — run this session, 2026-07-23

### Secondary (MEDIUM confidence)
- None. `gsd-tools query classify-confidence` rates only `context7`/`ref`/`jina`/`firecrawl` as MEDIUM; none of those MCP tools were present in this session's toolset (only `WebSearch`/`WebFetch`, both rated LOW by the seam regardless of the URL's authority). Everything below that would conventionally be "official docs, MEDIUM confidence" is therefore listed under Tertiary per the seam's actual output — see the Confidence line at the top of this document for the reconciliation.

### Tertiary (LOW confidence — per `classify-confidence`; provenance is genuinely official docs, see caveat above)
- `github.com/duckdb/dbt-duckdb` README (fetched directly via WebFetch this session) — external source `meta.external_location`/`read_parquet` syntax, `profiles.yml` `extensions:` config shape
- `docs.getdbt.com/docs/build/custom-schemas` (fetched directly via WebFetch this session) — `generate_schema_name` override macro shape, including dbt's own warning against omitting `default_schema`
- `docs.getdbt.com/reference/commands/build` (via WebSearch) — `dbt build` DAG-ordered execution semantics
- `docs.getdbt.com/best-practices/writing-custom-generic-tests` (via WebSearch) — generic test macro signature convention
- `docs.getdbt.com/docs/build/data-tests` (via WebSearch) — singular test mechanics (`.sql` file in `test-paths`, no trailing semicolon)
- `duckdb.org/docs` (via WebSearch) — `generate_series`, `date_trunc` for date-range generation
- `github.com/duckdb/duckdb` issues (via WebSearch) — `isAdjustedToUTC`/`TIMESTAMP WITH TIME ZONE` parquet roundtrip behavior
- `dbt_utils` `date_spine`/`accepted_range` macro internals (via WebSearch summaries only, not fetched directly) — used only to inform the "skip this dependency" recommendation, not adopted into the plan
- Illustrative pytest/Python code shapes in Patterns 6 and the freshness singular test in Pattern 7 — derived from spec wording + the above sources, not copy-pasted from any external source; additionally flagged `[ASSUMED]` inline and listed in the Assumptions Log

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions directly confirmed via `uv.lock` (already resolved) and `pip index versions` (current PyPI state), not guessed from training data; `classify-confidence` has no direct provider tag for local-file/pip-registry facts, but these are tool-verified, not searched
- Architecture: HIGH for the parts grounded directly in SPEC-02/WBS/CONTEXT.md/committed project files (dbt_project.yml, profiles.yml — binding, read directly); LOW per `classify-confidence` for the dbt-duckdb mechanical patterns sourced via `WebSearch`/`WebFetch` (no `context7`/`ref`/`jina`/`firecrawl` MCP tool available this session) — genuinely official-docs provenance, but not tool-tier-verified; treat all SQL/macro shapes as needing the planner's own `dbt build` verification, not as pre-verified
- Pitfalls: mixed — Pitfalls 1, 3, 4 are HIGH (grounded directly in committed project files: profiles.yml comment, dbt_project.yml model-paths, SPEC-02 §3 text); Pitfalls 2, 5, 6 are LOW per the seam (grounded in WebSearch-sourced DuckDB/dbt official-doc excerpts, same caveat as Architecture above)
- Package legitimacy: all three core packages (`dbt-core`, `dbt-duckdb`, `duckdb`) came back `SUS` from `gsd-tools query package-legitimacy check` — dispositioned "Approved" on the strength of `uv.lock` resolution + canonical-maintainer GitHub orgs, not on the tool's own verdict (see Package Legitimacy Audit)

**Research date:** 2026-07-23
**Valid until:** 30 days (dbt-core/dbt-duckdb release cadence is roughly monthly minor patches; version pins in `pyproject.toml` are range-based so this doesn't block re-verification, but re-run `pip index versions` if this research is consumed after 2026-08-23)
