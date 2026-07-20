# Codebase Structure

**Analysis Date:** 2026-07-20

## Directory Layout

```
energy-procurement-risk-analyzer/
├── config/                 # Validated YAML settings (non-secret)
├── src/epra/               # Installable Python package
│   ├── common/             # Config, logging, timeutil, DuckDB helper
│   ├── ingest/             # External sources → raw parquet
│   ├── consumer/           # Calibrated load profile
│   ├── analytics/          # Market analytics (A1–A4)
│   ├── strategies/         # Retrospective + forward risk
│   └── report/             # Format/style kit + charts
├── dbt/                    # DuckDB warehouse models (staging/marts)
├── scripts/                # Ops/governance CLIs (not imported by package)
├── tests/                  # pytest: unit/, fixtures/, golden/
├── data/                   # Runtime data (mostly gitignored)
│   ├── raw/                # Monthly source parquet
│   ├── cache/              # HTTP response cache
│   ├── manual/             # Hand-curated ÖSPI CSV (committed when ready)
│   ├── processed/          # Profile + strategy cost parquet
│   └── warehouse/          # epra.duckdb
├── reports/                # Committed analysis outputs + SSOT
├── exports/                # Mart CSVs for Power BI (gitignored)
├── dashboards/             # Power BI handoff (.pbix human-built)
├── docs/                   # SPEC-01…08, ADR/, EXECUTION_BLUEPRINT/, BUILD_LOG
├── .github/workflows/      # ci.yml (lint + test)
├── Makefile                # Canonical pipeline interface
├── pyproject.toml          # Package + ruff/mypy/pytest config
├── uv.lock                 # Pinned deps
├── PROJECT_CHARTER.md      # Scope & acceptance authority
├── AGENTS.md               # Agent build playbook
├── LIMITATIONS.md          # Honesty / epistemic limits
└── README.md               # User-facing entry
```

## Directory Purposes

**config/**
- Purpose: All non-secret tunables; YAML is the owner of parameters (never hardcode elsewhere)
- Contains: Three YAML files only
- Key files: `settings.yaml` (zones, paths, ingest politeness), `consumer_profile.yaml` (SPEC-03 §6), `strategies.yaml` (SPEC-05 §8)
- Subdirectories: None

**src/epra/**
- Purpose: The `epra` package (hatchling wheel packages this tree)
- Contains: Domain subpackages + `__init__.py` (`__version__`)
- Key files: package `__init__.py`
- Subdirectories: `common/`, `ingest/`, `consumer/`, `analytics/`, `strategies/`, `report/`

**src/epra/common/**
- Purpose: Shared foundation; no imports from other epra packages
- Contains: Implemented modules
- Key files: `config.py`, `logging.py`, `timeutil.py`, `db.py`
- Subdirectories: None

**src/epra/ingest/**
- Purpose: SPEC-01 ingestion + validation (M1/M2 stubs today)
- Contains: One file per source + validate
- Key files: `entsoe.py`, `geosphere.py`, `oespi.py`, `calendar.py`, `validate.py`
- Subdirectories: None (planned internals `_io.py`, `_fetch.py` live here when built)

**src/epra/consumer/**
- Purpose: SPEC-03 load profile (M4 stub)
- Contains: `profile.py`
- Key files: `profile.py` (`build_profile`, `monthly_volumes`)
- Subdirectories: None

**src/epra/analytics/**
- Purpose: SPEC-04 modules A1–A4 (M5 stubs)
- Contains: One module per analysis family
- Key files: `descriptive.py`, `spread.py`, `regimes.py`, `weather.py`
- Subdirectories: None

**src/epra/strategies/**
- Purpose: SPEC-05 simulator (M6 stubs)
- Contains: Calibration, retrospective, forward risk
- Key files: `calibration.py`, `retrospective.py`, `forward_risk.py`
- Subdirectories: None

**src/epra/report/**
- Purpose: SPEC-06 chart kit; format/style implemented, charts stubbed
- Contains: Formatters, Okabe-Ito style, executive chart renderer stub
- Key files: `format.py`, `style.py`, `charts.py`
- Subdirectories: None

**dbt/**
- Purpose: SPEC-02 warehouse project skeleton (models empty until M3)
- Contains: Project/profile YAML, seed, empty staging/marts dirs
- Key files: `dbt_project.yml`, `profiles.yml`, `seeds/dim_strategy.csv`, `README.md`
- Subdirectories: `models/staging/`, `models/marts/`, `macros/`, `seeds/`, `tests/`

**scripts/**
- Purpose: Standalone CLIs for governance and ops
- Contains: Python scripts invoked by Make/pre-commit/CI
- Key files: `oespi_reconcile.py` (implemented), `check_no_token_in_code.py` (implemented), `generate_ssot.py`, `check_ssot_consistency.py`, `export_marts.py`, `generate_golden_metrics.py`
- Subdirectories: None

**tests/**
- Purpose: pytest suite (EN-070/071/072)
- Contains: Unit tests for implemented code; reserved fixture/golden dirs
- Key files: `tests/unit/test_*.py` (config, timeutil, logging/db, report, scripts, smoke, stubs)
- Subdirectories: `unit/`, `fixtures/` (empty until M1), `golden/` (empty until M4/M6)

**data/**
- Purpose: Runtime artifacts; layout fixed by SPEC-07
- Contains: `.gitkeep` placeholders; real data mostly gitignored except reconciled manual ÖSPI when committed
- Key files: paths driven by `config/settings.yaml` → `data/warehouse/epra.duckdb`
- Subdirectories: `raw/`, `cache/`, `manual/`, `processed/`, `warehouse/`

**reports/**
- Purpose: Human-readable pipeline outputs committed to git when produced
- Contains: Subdirs per stage; NUMERIC_SSOT / EXEC_SUMMARY land at later milestones
- Key files: (future) `NUMERIC_SSOT.md`, `EXEC_SUMMARY.md`
- Subdirectories: `ingestion/`, `analytics/`, `strategies/`, `executive_charts/`

**exports/**
- Purpose: Flat CSV marts for Power BI (DM-070)
- Contains: `.gitkeep` only until `make export`
- Key files: produced by `scripts/export_marts.py`
- Subdirectories: None yet

**dashboards/**
- Purpose: Power BI deliverable handoff (human builds `.pbix`)
- Contains: Build instructions README
- Key files: `README.md`, `.gitkeep`
- Subdirectories: None

**docs/**
- Purpose: Specs, ADRs, execution blueprint, build log — authority for WHAT to build
- Contains: SPEC-01…08, ADR-001/002, EXECUTION_BLUEPRINT/*, BUILD_LOG.md
- Key files: `SPEC-0N_*.md`, `ADR/ADR-*.md`, `BUILD_LOG.md`
- Subdirectories: `ADR/`, `EXECUTION_BLUEPRINT/`, `assets/`

**.github/workflows/**
- Purpose: CI (EN-080)
- Contains: `ci.yml` — lint + test jobs live; dbt-check/ssot-check commented for M3/M6
- Key files: `ci.yml`
- Subdirectories: None

**.planning/**
- Purpose: GSD planning artifacts (codebase maps, future phase plans)
- Contains: `codebase/` analysis docs
- Key files: `codebase/ARCHITECTURE.md`, `codebase/STRUCTURE.md` (and siblings from other map foci)
- Subdirectories: `codebase/`

## Key File Locations

**Entry Points:**
- `Makefile` — canonical pipeline (`setup`, `lint`, `test`, stage stubs, `all`, `refresh`)
- `src/epra/ingest/entsoe.py` — planned CLI `python -m epra.ingest.entsoe`
- `src/epra/strategies/retrospective.py` — planned strategy CLI
- `scripts/oespi_reconcile.py` — ÖSPI double-entry reconcile CLI
- `scripts/generate_ssot.py` — SSOT writer (stub exit)
- `dbt/dbt_project.yml` — warehouse build entry (via `dbt build`)

**Configuration:**
- `config/settings.yaml` — zones, window start, paths, ingest parameters
- `config/consumer_profile.yaml` — load profile parameters
- `config/strategies.yaml` — simulator / forward bootstrap parameters
- `.env.example` — documents `ENTSOE_API_TOKEN` (`.env` local only, never commit secrets)
- `pyproject.toml` — package metadata, deps, ruff/mypy/pytest/coverage
- `uv.lock` — locked dependency graph
- `.pre-commit-config.yaml` — ruff + token guard hook
- `dbt/profiles.yml` — DuckDB connection for dbt

**Core Logic:**
- `src/epra/common/` — implemented foundation
- `src/epra/ingest/` — ingestion + gates (stubs)
- `src/epra/consumer/profile.py` — load profile (stub)
- `src/epra/analytics/` — market analytics (stubs)
- `src/epra/strategies/` — cost & risk engines (stubs)
- `src/epra/report/` — format/style live; charts stub
- `dbt/models/` — staging/marts (empty until M3)

**Testing:**
- `tests/unit/` — unit tests for M0 surface
- `tests/fixtures/` — reserved for ENTSO-E/GeoSphere excerpts (EN-070)
- `tests/golden/` — reserved for LP-040 / ST-601 goldens (EN-072)

**Documentation:**
- `PROJECT_CHARTER.md` — goals, scope, acceptance
- `AGENTS.md` — how agents build (milestones, gates, stop rules)
- `docs/SPEC-01_data_ingestion.md` … `docs/SPEC-08_governance_quality.md`
- `docs/EXECUTION_BLUEPRINT/` — modules, patterns, anti-patterns, gates
- `docs/ADR/` — architecture decision records
- `docs/BUILD_LOG.md` — append-only milestone log
- `LIMITATIONS.md` — epistemic honesty
- `README.md` — user-facing overview
- `dashboards/README.md` — Power BI build handoff

## Naming Conventions

**Files:**
- `snake_case.py` for all Python modules (`entsoe.py`, `forward_risk.py`, `timeutil.py`)
- `test_<module>.py` under `tests/unit/` mirroring the surface under test
- `SPEC-NN_snake_topic.md` for binding specs; `ADR-NNN_kebab-topic.md` for decisions
- `UPPERCASE.md` for root authority docs (`PROJECT_CHARTER.md`, `AGENTS.md`, `LIMITATIONS.md`)
- YAML: `snake_case.yaml` in `config/`
- Parquet (runtime): `<dataset>_<YYYY-MM>.parquet` under `data/raw/<dataset>/<YYYY>/` (SPEC-01)

**Directories:**
- `snake_case` package/dirs matching domain nouns (`ingest/`, `strategies/`, `executive_charts/`)
- Plural for collections of artifacts (`reports/`, `exports/`, `dashboards/`, `tests/`)
- dbt layers named by role: `staging/`, `marts/`

**Special Patterns:**
- Package import root: `epra.*` (code under `src/epra/`)
- Public functions document `Implements: REQ-ID, …` in docstrings for greppable traceability
- Milestone stubs keep real signatures and raise `NotImplementedError("M# not implemented…")`
- Scripts are top-level files in `scripts/`, not package modules
- Empty reserved dirs use `.gitkeep`

## Where to Add New Code

**New ingestion source / gate (M1–M2):**
- Primary code: `src/epra/ingest/<source>.py` (or gate fn in `validate.py`)
- Shared I/O/fetch: `src/epra/ingest/_io.py` / `_fetch.py` (per blueprint)
- Tests: `tests/unit/test_<source>.py` + fixtures under `tests/fixtures/`
- Config if needed: extend pydantic models in `src/epra/common/config.py` + `config/settings.yaml` in the same change

**New dbt model (M3):**
- Staging: `dbt/models/staging/stg_*.sql`
- Marts: `dbt/models/marts/<dim|fct>_*.sql`
- Seeds: `dbt/seeds/`
- Schema contract tests: `dbt/tests/` + committed contract YAML per SPEC-02

**New consumer / analytics / strategy feature (M4–M6):**
- Implementation: matching package under `src/epra/consumer|analytics|strategies/`
- Prefer pure functions + thin `run(settings)` shell; strategies use a dispatch dict, not ABC hierarchies
- Tests: `tests/unit/`; goldens via `scripts/generate_golden_metrics.py` only with human approval
- Outputs: `data/processed/` and/or `reports/<analytics|strategies>/`

**New chart / report artifact (M5/M7):**
- Shared format/style: extend `src/epra/report/format.py` or `style.py` (single owners)
- Chart renderers: `src/epra/report/charts.py` (or called from analytics `run`)
- Numbers for docs: only via `scripts/generate_ssot.py` → `reports/NUMERIC_SSOT.md`

**New Makefile stage:**
- Definition: `Makefile` target calling `uv run …`
- Keep idempotent; fail loudly if not ready — never silent no-op

**Utilities:**
- Shared helpers: `src/epra/common/` only (time, db, logging, config)
- Do not put path strings or TZ math in domain modules — use `settings.paths` and `timeutil`
- Ops/governance CLIs: `scripts/`

**New ADR / spec note:**
- ADR: `docs/ADR/ADR-NNN_topic.md` (append-only)
- Spec conflict: Charter wins; then SPEC; silent code deviation forbidden

## Special Directories

**data/**
- Purpose: Runtime inputs/outputs for the pipeline
- Source: Ingest, dbt, profile, simulate writes
- Committed: Structure + `.gitkeep`; `data/manual/oespi_monthly.csv` committed when reconciled; other contents gitignored

**data/warehouse/**
- Purpose: Single DuckDB file `epra.duckdb` (DM-001)
- Source: dbt materializations; Python reads via `epra.common.db`
- Committed: No (gitignored); CI will use fixture bootstrap at M3

**data/cache/**
- Purpose: HTTP response cache for polite re-runs (ING-009)
- Source: Planned `ingest._fetch`
- Committed: No

**exports/**
- Purpose: CSV extracts for Power BI
- Source: `scripts/export_marts.py`
- Committed: No (except `.gitkeep`); refresh workflow may upload as artifact

**reports/**
- Purpose: Markdown/PNG deliverables including NUMERIC_SSOT
- Source: validate, analyze, simulate, ssot, report stages
- Committed: Yes when produced (SSOT consistency gated by CI at M6)

**dbt/target/, dbt/logs/, dbt/dbt_packages/**
- Purpose: dbt build artifacts / deps
- Source: `dbt` CLI
- Committed: No

**.venv/, .mypy_cache/, .pytest_cache/, .ruff_cache/**
- Purpose: Local tooling caches
- Source: uv / mypy / pytest / ruff
- Committed: No

**.planning/**
- Purpose: Agent/planner codebase and phase docs
- Source: `/gsd-map-codebase` and related GSD commands
- Committed: Yes (when project tracks planning artifacts)

---

*Structure analysis: 2026-07-20*
*Update when directory structure changes*
