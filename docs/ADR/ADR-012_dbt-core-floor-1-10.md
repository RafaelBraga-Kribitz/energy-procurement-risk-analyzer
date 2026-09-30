# ADR-012: Raise the dbt-core / dbt-duckdb floor to 1.10 and enforce the lock file
Date: 2026-09-30  |  Status: accepted

## Context
SPEC-07 §3 lists `dbt-core>=1.8,<2` and `dbt-duckdb>=1.8,<2`. The M3 test YAML
(`dbt/models/marts/facts_price.yml`, `facts_future.yml`) uses the generic-test
`arguments:` block, which only exists from dbt-core 1.10; `staging.yml` still
used the pre-1.10 form, which dbt-core 1.12 flags as deprecated. A fresh
environment resolving dbt-core 1.8/1.9 would fail to parse the project, so the
declared floor did not describe what the project actually runs on (audit
2026-09-30, §2). `uv.lock` already pins dbt-core 1.12.0 / dbt-duckdb 1.10.1.

Separately, `make setup` and every CI job installed with `uv pip install -e`,
which ignores `uv.lock`: the "pinned" dependency set of SPEC-07 §3 / EN-030 was
never actually what got installed.

## Decision
- `pyproject.toml`: `dbt-core>=1.10,<2`, `dbt-duckdb>=1.10,<2`.
- `dbt/dbt_project.yml`: `require-dbt-version: [">=1.10.0", "<2.0.0"]`, so an
  older dbt fails with a clear message instead of a parse error.
- All dbt test YAML uses the `arguments:` form.
- `make setup` and CI install with `uv sync --frozen --extra dev`, so the
  committed `uv.lock` (EN-030) is the installed dependency set, and a
  `pyproject.toml` change without a matching lock update fails loudly.
- The pre-commit ruff hooks run the lock-pinned `uv run ruff` instead of a
  separately pinned `ruff-pre-commit` revision, so the linter version exists
  in exactly one place.

## Consequences
- dbt 1.8/1.9 are no longer supported; nothing in the repo ever ran on them.
- Upgrading any dependency means `uv lock` + a committed `uv.lock` (GV-203:
  upgrades still need an ADR when they change behaviour).

## Spec deviations
SPEC-07 §3 (dbt-core / dbt-duckdb lower bounds); EN-001 (names
`uv pip install -e ".[dev]"`; `uv sync --frozen --extra dev` installs the same
package set, pinned by EN-030's lock file). Output contract preserved: same
models, same marts, same tests.
