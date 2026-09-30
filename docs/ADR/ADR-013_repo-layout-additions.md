# ADR-013: Repository-layout additions beyond the SPEC-07 §2 tree
Date: 2026-09-30  |  Status: accepted

## Context
SPEC-07 §2 says "create exactly this" layout. The shipped M0–M3 repository
contains paths the §2 tree does not list (found by the 2026-09-30 audit,
`.planning/AUDIT-2026-09-30.md` §3). Per AGENTS.md A-1, a code-vs-spec
disagreement is recorded in an ADR rather than left silent. No file is moved
by this ADR; it records what exists, why, and which spec text it relies on.

Paths present in the repository but absent from the SPEC-07 §2 tree:

| Path | Introduced | Purpose |
|------|------------|---------|
| `src/epra/warehouse/` (`report.py`) | M3, commit `a9a34d7` (plan 04-07) | Reads the built DuckDB warehouse read-only and writes the human-readable build report; called by `make warehouse` |
| `reports/warehouse/` (`dbt_build_<date>.md`) | M3, commit `df68473` (plan 04-08) | Committed M3 gate evidence, parallel to `reports/ingestion/` |
| `tests/test_raw_contracts.py` (at `tests/` root) | M1 (plan 02-07, see `docs/BUILD_LOG.md` 2026-07-21) | ING-070 raw-parquet contract tests |
| `scripts/bootstrap_fixture_warehouse.py` | M3, commit `5dfe072` (plan 04-05) | Network-free fixture warehouse for the CI `dbt build` job (EN-080 job 3); ADR-010 |
| `dbt/contracts/marts_contract.yml` | M3, commit `411d8c8` (plan 04-06) | Committed mart schema contract that the M3 gate compares `information_schema` against (AGENTS.md §3 M3 gate) |
| `dbt/macros/` | M3 (plan 04-01) | `generate_schema_name` (ADR-009) and hand-rolled test/spine macros |
| `src/epra/ingest/_io.py`, `_fetch.py`, `exceptions.py` | M1 | Private helpers of the listed ingest modules (single raw-parquet write boundary, HTTP transport/cache, exception types) |
| `docs/BUILD_LOG.md`, `docs/EXECUTION_BLUEPRINT/` | M0 / 2026-07-19 | Build log required by AGENTS.md W-5; planning blueprint (subordinate to Charter/SPEC/ADR) |
| `src/epra/common/gates.py` | 2026-09-30 (audit fix) | Shared `CheckResult`/`CheckReport` behind both the ingest validation report (`validate.py`) and the dbt build report (`warehouse/report.py`), replacing two verbatim copies |
| `.planning/` | 2026-07-21 | Planning/continuity state for the maintainer's local GSD tooling (`.planning/CONTINUITY.md`) |

## Decision
1. The paths above are accepted additions to the SPEC-07 §2 layout. The §2
   tree remains authoritative for everything it lists; these entries extend
   it and do not replace any listed path.
2. `tests/test_raw_contracts.py` stays at the `tests/` root: SPEC-01 ING-070
   names that exact path, and the SPEC-07 §2 tree lists only the `tests/`
   subdirectories. Both specs are satisfied as written.
3. `src/epra/warehouse/` and `reports/warehouse/` are the M3 counterparts of
   `src/epra/ingest/validate.py` and `reports/ingestion/`: a module that
   renders gate evidence and the directory where that evidence is committed.
4. Private (`_`-prefixed) helper modules inside a listed package are allowed
   without a further ADR. A new public module, top-level package, `reports/`
   subdirectory or `scripts/` entry needs an ADR or a SPEC-07 §2 update.

## Consequences
- The "Directory layout still matches SPEC-07 §2 exactly" item in
  `docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md` §6.6 is read as "matches §2 plus
  ADR-013".
- If SPEC-07 is revised, fold this table into the §2 tree and mark this ADR
  `superseded-by` that change.

## Spec deviations
SPEC-07 §2 ("create exactly this"): the additions listed in the table. No
output contract changes. ING-070's test path is unchanged.
