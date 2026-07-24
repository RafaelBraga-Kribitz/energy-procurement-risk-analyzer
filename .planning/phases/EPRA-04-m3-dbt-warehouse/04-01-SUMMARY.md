---
phase: EPRA-04-m3-dbt-warehouse
plan: 01
subsystem: database
tags: [dbt, dbt-duckdb, duckdb, sql]

# Dependency graph
requires:
  - phase: EPRA-02-m1-entsoe-ingestion
    provides: data/raw/entsoe_* monthly parquet (write_month contract, ING-004/005/070)
  - phase: EPRA-03-m2-auxiliary-data
    provides: data/raw/calendar/calendar.parquet, data/manual/oespi_monthly.csv, data/raw/geosphere_graz_daily
provides:
  - dbt/macros/generate_schema_name.sql — literal staging/marts schema override (SG-13, DM-003)
  - dbt/models/sources.yml — all 9 raw/manual/processed datasets exposed once via external read_parquet/read_csv globs (DM-004)
  - dbt/macros/month_spine.sql — DM-050 no-gap month spine helper (DuckDB generate_series)
  - dbt/macros/test_accepted_range.sql — DM-061 accepted-range generic test macro
  - docs/ADR/ADR-009_generate-schema-name-macro.md — governance record for the schema-macro tradeoff
affects: [EPRA-04-m3-dbt-warehouse plans 02-08 (staging models, marts, dbt test suite, CI fixture bootstrap)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dbt generate_schema_name override intentionally omits target.schema prefix for this single-operator local warehouse (ADR-009)"
    - "External sources via meta.external_location + read_parquet/read_csv, one glob per raw dataset, all paths prefixed ../data/ (dbt cwd is dbt/)"
    - "Hand-rolled dbt macros in place of dbt_utils to keep zero package dependencies (ADR-001 lean-repo)"

key-files:
  created:
    - dbt/macros/generate_schema_name.sql
    - dbt/models/sources.yml
    - dbt/macros/month_spine.sql
    - dbt/macros/test_accepted_range.sql
    - docs/ADR/ADR-009_generate-schema-name-macro.md
  modified:
    - .gitignore

key-decisions:
  - "ADR-009: generate_schema_name omits the default_schema prefix so DuckDB schemas are literally staging/marts, accepted because profiles.yml defines exactly one local single-operator target"
  - "sources.yml exposes 9 raw tables across 4 source groups (raw, raw_calendar, raw_manual, raw_processed), each read via a single ../data/-prefixed glob with union_by_name=true"
  - "month_spine and accepted_range macros hand-rolled on DuckDB native generate_series — no dbt_utils/packages.yml added"
  - "dbt/.user.yml (dbt-generated anonymous usage-tracking id, created on first dbt invocation) added to .gitignore alongside the existing dbt/target, dbt/logs, dbt/dbt_packages entries"

patterns-established:
  - "Pattern: every new dbt model/macro description cites its DM-xxx/SG-xx requirement ID, mirroring the project's Implements: XXX-nnn docstring convention"
  - "Pattern: dbt macro header comments avoid the literal string of a package name being deliberately avoided (write 'zero external dbt package dependency' rather than naming the alternative), so a grep for that package name across dbt/ reliably proves non-adoption"

requirements-completed: [REQ-DWH-01, DM-003, DM-004, SG-13]

coverage:
  - id: D1
    description: "generate_schema_name override yields literal staging/marts DuckDB schemas (not main_staging/main_marts)"
    requirement: "DM-003"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt seed --full-refresh && uv run python -c \"...information_schema.schemata... assert 'marts' in schemas and 'main_marts' not in schemas\""
        status: pass
    human_judgment: false
  - id: D2
    description: "sources.yml exposes all 9 raw/manual/processed datasets exactly once via ../data/-prefixed read_parquet/read_csv globs"
    requirement: "DM-004"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt parse (exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "month_spine + test_accepted_range macros compile with zero dbt_utils/packages.yml dependency"
    verification:
      - kind: other
        ref: "cd dbt && uv run dbt parse (exit 0); test ! -f packages.yml; grep -ri dbt_utils -r dbt/ (no matches)"
        status: pass
    human_judgment: false
  - id: D4
    description: "ADR-009 records the schema-macro single-operator tradeoff with Context/Decision/Consequences/Spec deviations sections"
    verification: []
    human_judgment: true
    rationale: "Governance-document quality (clarity, completeness of tradeoff framing) is a judgment call, not mechanically testable."

duration: 20min
completed: 2026-07-24
status: complete
---

# Phase EPRA-04 Plan 01: dbt Foundation — Schema Macro, Sources, Helper Macros Summary

**SG-13 `generate_schema_name` override (literal `staging`/`marts` schemas), DM-004 `sources.yml` exposing all 9 raw datasets via `../data/`-prefixed external globs, and hand-rolled `month_spine`/`accepted_range` macros with zero dbt package dependencies**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-24T08:29:59Z
- **Tasks:** 3/3
- **Files modified:** 6 (5 created + `.gitignore`)

## Accomplishments
- `generate_schema_name` override verified live: `dbt seed --full-refresh` builds `dim_strategy` into a schema literally named `marts` (not `main_marts`), proving SG-13/DM-003
- `sources.yml` created exposing every raw/manual/processed dataset exactly once (9 tables across 4 source groups), all globs prefixed `../data/` per Pitfall 1, `dbt parse` green
- `month_spine` and `test_accepted_range` macros hand-rolled on DuckDB's native `generate_series`/`{% test %}` convention — zero `dbt_utils`/`packages.yml` dependency, `dbt parse` green
- ADR-009 committed recording the schema-macro tradeoff and its single-operator justification

## Task Commits

Each task was committed atomically:

1. **Task 1: generate_schema_name override macro (SG-13) + ADR-009** - `b5c0cca` (feat)
2. **Task 2: sources.yml — every raw dataset exposed once via read_parquet/read_csv (DM-004)** - `32dfc9e` (feat)
3. **Task 3: hand-rolled month_spine + accepted_range helper macros (no dbt_utils)** - `cb8a956` (feat)

## Files Created/Modified
- `dbt/macros/generate_schema_name.sql` - overrides dbt's default schema-prefix behavior; returns trimmed `custom_schema_name` or `target.schema`
- `docs/ADR/ADR-009_generate-schema-name-macro.md` - governance record (Context/Decision/Consequences/Spec deviations)
- `dbt/models/sources.yml` - `raw` (5 parquet datasets), `raw_calendar.calendar`, `raw_manual.oespi_monthly` (CSV), `raw_processed` (2 M4/M6 stand-in tables)
- `dbt/macros/month_spine.sql` - DM-050 no-gap month-spine helper (`generate_series`/`date_trunc`)
- `dbt/macros/test_accepted_range.sql` - DM-061 generic test macro (`{% test accepted_range(model, column_name, min_value, max_value) %}`)
- `.gitignore` - added `dbt/.user.yml` (dbt-generated anonymous usage-tracking id, first appeared after the Task 1 `dbt seed` run)

## Decisions Made
- ADR-009: `generate_schema_name` omits the default-schema prefix so schemas are literally `staging`/`marts`, accepted because `profiles.yml` defines exactly one local single-operator target — this pattern must NOT be copied into any future multi-developer/shared-warehouse dbt project without revisiting the tradeoff.
- `sources.yml` groups: `raw` (ENTSO-E + GeoSphere parquet), `raw_calendar` (calendar spine), `raw_manual` (OESPI CSV), `raw_processed` (M4/M6 stand-in parquet, not yet populated — `data/processed/` is currently empty aside from `.gitkeep`, which is expected; these sources are wired now so 04-05's stand-in generator and later marts have a place to read from).
- Macro header comments deliberately avoid naming the specific alternative package being skipped, so a plain grep across `dbt/` for that package name reliably proves zero adoption (rather than accidentally matching an explanatory comment).

## Deviations from Plan

None - plan executed exactly as written. The one incidental fix (adding `dbt/.user.yml` to `.gitignore`) is a Rule 3 blocking-adjacent auto-fix: `dbt seed` generates this file on first run in every dbt project and it is not project content, so it was added alongside the pre-existing `dbt/target/`, `dbt/logs/`, `dbt/dbt_packages/` ignore entries to keep `git status` clean per the phase's D-02 requirement (`git status` must stay clean of generated artifacts).

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required. `dbt-core`/`dbt-duckdb`/`duckdb` were already resolved in the committed `uv.lock` prior to this plan (per 04-RESEARCH.md Package Legitimacy Audit); no install step was needed.

## Next Phase Readiness

Foundation plumbing is in place for 04-02 onward: the schema-name macro guarantees staging/marts models land in the right literal schemas, `sources.yml` gives every staging model a single `source('raw', ...)`-style entry point with zero direct file access, and `month_spine`/`accepted_range` are available to the marts and dbt test suite (04-04/04-05/04-06) with no new package dependency to manage. No blockers.

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-07-24*

## Self-Check: PASSED

All 5 created files found on disk; all 3 task commit hashes (`b5c0cca`, `32dfc9e`, `cb8a956`) found in git log.
