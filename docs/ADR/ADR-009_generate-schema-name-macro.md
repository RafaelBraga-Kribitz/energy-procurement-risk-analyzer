# ADR-009: `generate_schema_name` override — literal `staging`/`marts` schemas

**Status:** accepted
**Date:** 2026-07-24
**Deciders:** M3 dbt warehouse (EPRA-04)
**Related:** SPEC-02 DM-003 (layers/schemas table), `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-13,
`dbt/dbt_project.yml` (`+schema: staging` / `+schema: marts` configs, `dim_strategy` seed
`+schema: marts`), `dbt/profiles.yml` (single `dev` target, local DuckDB file)

## Context

dbt's default `generate_schema_name` macro concatenates the connection's `target.schema`
with any model/seed `+schema:` config, e.g. a model configured `+schema: marts` running
against a `dev` target whose `profiles.yml` schema is `main` materializes into
`main_marts`, not `marts`. This is dbt's documented, intentional default: it lets many
developers (or many CI runs) share one physical database/catalog without their
`dev`/`ci_pr_123`/etc. schemas colliding.

SPEC-02 DM-003 requires the opposite: dbt schemas in the project's DuckDB file must be
**literally** `staging` and `marts` (not `main_staging`/`main_marts`), because
downstream consumers (M5/M6 analytics modules, ad-hoc `duckdb` CLI inspection, the
`fct_price_hourly`-family mart contract) all query `staging.*` / `marts.*` by their
plain, literal names. `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-13 recorded this as
a spec gap to resolve via ADR before implementation.

## Decision

Override `generate_schema_name(custom_schema_name, node)` in
`dbt/macros/generate_schema_name.sql` to return:

- `target.schema` when no `custom_schema_name` is configured (i.e. the model/seed did
  not set `+schema:`), and
- the trimmed `custom_schema_name` verbatim otherwise — **omitting** the
  `<target.schema>_` prefix dbt's built-in macro normally prepends.

This is exactly the pattern dbt's own documentation (`docs.getdbt.com/docs/build/custom-schemas`)
labels **unsafe for shared dev/CI environments** — the docs' own example calls the
prefix-omitting version "incorrect" because two developers (or two concurrent CI runs)
targeting the *same* warehouse would silently overwrite each other's `staging`/`marts`
schemas.

We adopt it anyway because `dbt/profiles.yml` (D-08, DM-002) defines **exactly one**
`dev` target pointing at one local `data/warehouse/epra.duckdb` file, with no
shared/remote warehouse and no concurrent-developer scenario — this is a
single-operator local analytics project, not a team data warehouse. The failure mode
the docs warn about (schema collision across concurrent users) cannot occur here.

## Consequences

- `dbt seed --full-refresh` (building the existing `dim_strategy` seed) and every
  later staging/mart model land in DuckDB schemas literally named `staging` / `marts`,
  matching SPEC-02 DM-003 and every downstream consumer's literal-schema expectations.
- **This macro must NOT be copied verbatim into any future multi-target or
  multi-developer dbt project** (e.g. a shared team warehouse, a CI job that persists
  its DuckDB file across runs, or a cloud-warehouse target) without first revisiting
  this tradeoff — doing so would reintroduce the exact collision risk dbt's default
  behavior exists to prevent. Any future generalization of this project's dbt setup to
  a multi-operator context is an explicit trigger to re-open this ADR.
- The CI fixture-build job (T3.06, D-04) always builds a **fresh, ephemeral** DuckDB
  file per run (never a shared/persistent one), so it inherits this macro safely — no
  separate CI-specific schema-naming logic is needed.
- No change to `dbt_project.yml`'s existing `+schema: staging` / `+schema: marts`
  configs or `profiles.yml` — this ADR only adds the macro override.

## Spec deviations

None against SPEC-02 — DM-003 explicitly requires literal `staging`/`marts` schema
names; this macro is the mechanism that satisfies that requirement given dbt's
default behavior would otherwise produce `main_staging`/`main_marts`. This ADR
resolves SG-13's open gap by adopting the literal-schema-override macro as the
accepted implementation.
