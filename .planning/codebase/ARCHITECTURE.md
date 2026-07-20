# Architecture

**Analysis Date:** 2026-07-20

## Pattern Overview

**Overall:** Spec-driven batch analytics pipeline (Makefile-orchestrated monolothic Python package + dbt/DuckDB warehouse)

**Key Characteristics:**
- Single installable package `epra` under `src/epra/` — no web/API server (Charter O-4)
- Explicit staged pipeline: ingest → validate → dbt transform → profile → analyze → simulate → SSOT → export → report
- Functional core / imperative shell: pure frame math + thin `run()`/`main()` I/O shells
- DuckDB warehouse is the only interface between ingest and analytics/strategies (no cross-layer Python imports)
- Deterministic, single-process, single-threaded; seeded RNG only where SPEC-05 requires it
- Milestone M0 complete: `epra.common` + report kit helpers live; domain modules are typed stubs that raise `NotImplementedError` until their milestone

## Layers

**Orchestration (Makefile):**
- Purpose: Canonical operator interface; each target is one pipeline stage (EN-050)
- Contains: `setup`, `lint`, `test`, and pipeline stubs (`backfill`…`report`, `all`, `refresh`)
- Location: `Makefile`
- Depends on: `uv run` invoking package modules / `scripts/` / dbt
- Used by: Local operators and (future) refresh CI cron

**Configuration:**
- Purpose: Single validated source of non-secret settings and domain tunables
- Contains: YAML files loaded once into frozen pydantic models
- Location: `config/settings.yaml`, `config/consumer_profile.yaml`, `config/strategies.yaml`; loaders in `src/epra/common/config.py`
- Depends on: pydantic, PyYAML; secrets only via env (`ENTSOE_API_TOKEN`)
- Used by: Every pipeline module (passed as `Settings` / `ConsumerProfileCfg` / `StrategyCfg` arguments)

**Shared common utilities:**
- Purpose: Cross-cutting primitives used by all domain packages; imports nothing from other `epra` packages
- Contains: config loaders, logging setup, UTC↔Vienna time helpers, DuckDB connect helper
- Location: `src/epra/common/` (`config.py`, `logging.py`, `timeutil.py`, `db.py`)
- Depends on: stdlib, pydantic, duckdb, dotenv
- Used by: ingest, consumer, analytics, strategies, report, scripts

**Ingestion:**
- Purpose: External sources → contracted raw parquet under `data/raw/` (and manual CSV under `data/manual/`)
- Contains: One module per source + validation gate framework
- Location: `src/epra/ingest/` (`entsoe.py`, `geosphere.py`, `oespi.py`, `calendar.py`, `validate.py`); planned internals `_io`, `_fetch` per blueprint
- Depends on: `epra.common` only; never analytics/strategies/report
- Used by: Makefile `backfill`/`ingest`/`validate-ingest`; raw files consumed by dbt staging

**Warehouse (dbt + DuckDB):**
- Purpose: Staging views + mart tables; hourly aggregation, calendar dims, schema contracts (SPEC-02)
- Contains: dbt project skeleton; models land at M3
- Location: `dbt/` (`models/staging/`, `models/marts/`, `seeds/dim_strategy.csv`, `dbt_project.yml`, `profiles.yml`)
- Depends on: parquet/CSV under `data/`; warehouse file `data/warehouse/epra.duckdb`
- Used by: analytics/strategies via `epra.common.db.connect(..., read_only=True)`; Python must not create model tables by hand

**Consumer profile:**
- Purpose: Deterministic calibrated hourly load for StyriaMetal (+ flat baseload sensitivity)
- Contains: Pure weight/normalize algorithm + thin write of processed parquet
- Location: `src/epra/consumer/profile.py`
- Depends on: `ConsumerProfileCfg`, calendar frame from ingest; writes `data/processed/`
- Used by: strategies (volumes), SSOT (`consumer_peak_share`)

**Analytics:**
- Purpose: Market structure answers (Q2): descriptive, AT–DE spread, regimes, weather
- Contains: One module per analysis family with `run(settings)` shell
- Location: `src/epra/analytics/` (`descriptive.py`, `spread.py`, `regimes.py`, `weather.py`)
- Depends on: marts via `db`; report kit for charts; never imports `ingest`
- Used by: Makefile `analyze`; regime outputs consumed as data by forward risk

**Strategies:**
- Purpose: Procurement cost retrospective (Q1) + forward bootstrap risk (Q3/Q4)
- Contains: calibration → retrospective (S1–S4 dispatch) → forward_risk
- Location: `src/epra/strategies/` (`calibration.py`, `retrospective.py`, `forward_risk.py`)
- Depends on: marts/processed parquet + strategy config; dispatch table of pure cost functions (not class hierarchy)
- Used by: Makefile `simulate`; SSOT generation

**Reporting:**
- Purpose: Shared chart style/format kit + executive chart renderers
- Contains: Implemented formatters/style; stub charts
- Location: `src/epra/report/` (`format.py`, `style.py`, `charts.py`)
- Depends on: matplotlib conventions (SPEC-06 §7); settings for output paths
- Used by: analytics, strategies, `make report`

**Scripts / governance tooling:**
- Purpose: One-off CLIs outside the import graph of domain packages
- Contains: SSOT generator/checkers, mart export, golden regeneration, ÖSPI reconcile, token guard
- Location: `scripts/`
- Depends on: warehouse/processed outputs or filesystem; not imported by `src/epra`
- Used by: Makefile targets, pre-commit, CI (future ssot-check)

## Data Flow

**Full refresh pipeline (`make refresh` → ingest → validate → `make all`):**

1. Operator sets `ENTSOE_API_TOKEN` (env / `.env`); non-secrets from `config/*.yaml` via `load_settings()` (`src/epra/common/config.py`)
2. `make backfill` / `make ingest` → `epra.ingest.entsoe` (and geosphere/oespi/calendar) write monthly parquet under `data/raw/` and cache under `data/cache/`
3. `make validate-ingest` → `epra.ingest.validate` runs ING gates → `reports/ingestion/validation_*.md`; fails fast on gate failure
4. `make transform` → `dbt build` reads raw → staging views → mart tables in `data/warehouse/epra.duckdb`
5. `make profile` → `epra.consumer.profile.build_profile` → `data/processed/consumer_load_hourly.parquet`
6. `make analyze` → each `epra.analytics.*.run(settings)` reads marts → `reports/analytics/`
7. `make simulate` → calibration → retrospective → forward_risk → `data/processed/` strategy costs + `reports/strategies/`
8. `make ssot` → `scripts/generate_ssot.py` writes `reports/NUMERIC_SSOT.md` (numbers only from computed outputs)
9. `make export` → `scripts/export_marts.py` → `exports/` CSVs for Power BI
10. `make report` → `epra.report.charts.render_executive_charts` → `reports/executive_charts/`

**Manual ÖSPI path (M2):**

1. Human/agent transcribes ÖSPI twice into `data/manual/oespi_monthly_entry{1,2}.csv`
2. `scripts/oespi_reconcile.py` diffs → writes `data/manual/oespi_monthly.csv` on match
3. `epra.ingest.oespi` loads reconciled CSV into the pipeline (no invented fills)

**State Management:**
- File-based durable state: parquet under `data/`, DuckDB warehouse, markdown/PNG under `reports/`, CSV under `exports/`
- No long-lived in-process state; config loaders use `@cache` for YAML only
- Frozen pydantic models / frozen dataclasses for config and gate results
- Stochastic paths receive an explicit seed from `config/strategies.yaml` (`StrategyCfg.forward.seed`)

## Key Abstractions

**Settings / domain config objects:**
- Purpose: Validated, immutable configuration passed by argument (EN-040, LP-002, ST-003)
- Examples: `Settings`, `ConsumerProfileCfg`, `StrategyCfg` in `src/epra/common/config.py`
- Pattern: Frozen pydantic `BaseModel` (`extra="forbid"`); YAML read only in this module

**Functional core / imperative shell:**
- Purpose: Keep formulas pure and golden-testable; confine I/O to thin `run()`/`main()`
- Examples: planned `build_profile`, gate functions in `validate`, strategy cost functions; shells like `descriptive.run`, `retrospective.run`
- Pattern: Pure functions on DataFrames + dict dispatch for strategies (`{"S1": cost_s1, ...}`)

**Gate / ValidationReport:**
- Purpose: Pre-warehouse data-quality contracts (SPEC-01 §§8–11); fail-fast pipeline stop
- Examples: planned `GateResult`, `ValidationReport` in `src/epra/ingest/validate.py`
- Pattern: One pure gate function per REQ ID; aggregate → markdown report → `raise_if_failed()`

**Mart reader boundary:**
- Purpose: Analytics/strategies consume warehouse frames, never raw ingest APIs
- Examples: `epra.common.db.connect(settings, read_only=True)`; planned package-local SQL readers
- Pattern: Repository-style — all SQL in one place per package; computation modules take DataFrames

**Numeric SSOT:**
- Purpose: Single table of quotable numbers for README/EXEC_SUMMARY (SPEC-08 GV-301..303)
- Examples: `reports/NUMERIC_SSOT.md` produced by `scripts/generate_ssot.py`; consistency via `scripts/check_ssot_consistency.py`
- Pattern: Generated artifact + CI gate; never hand-type result numbers (A-6)

**Typed milestone stubs:**
- Purpose: Fail loudly until implemented; docstring carries binding SPEC + REQ IDs
- Examples: `src/epra/ingest/entsoe.py`, `src/epra/consumer/profile.py`, `src/epra/strategies/*.py`
- Pattern: Public API signatures present; body raises `NotImplementedError` naming milestone

## Entry Points

**Makefile pipeline:**
- Location: `Makefile`
- Triggers: Operator / CI (`make setup|lint|test|…`)
- Responsibilities: Stage orchestration; unimplemented stages exit 1 with milestone message

**Package CLIs (module `__main__`):**
- Location: e.g. `src/epra/ingest/entsoe.py` (`main`), `src/epra/strategies/retrospective.py` (`main`)
- Triggers: `python -m epra.ingest.entsoe …` (when implemented); Makefile will invoke these
- Responsibilities: Parse argv, load settings, call shell functions, exit codes

**Scripts:**
- Location: `scripts/oespi_reconcile.py` (implemented); `scripts/generate_ssot.py`, `export_marts.py`, `generate_golden_metrics.py`, `check_ssot_consistency.py`, `check_no_token_in_code.py`
- Triggers: Direct `uv run python scripts/…` or Makefile / pre-commit / CI
- Responsibilities: Governance and operational side paths outside the package import DAG

**dbt:**
- Location: `dbt/` with profile `epra` → `data/warehouse/epra.duckdb`
- Triggers: `make transform` → `dbt build` (when wired)
- Responsibilities: Staging/mart materialization and warehouse tests

**pytest:**
- Location: `tests/unit/` (fixtures/golden dirs reserved)
- Triggers: `make test` / CI job `test`
- Responsibilities: Unit coverage of implemented common/report/scripts; stub-loudness contract

## Error Handling

**Strategy:** Fail-fast (EN-061). Contract/gate violations raise; pipeline steps exit non-zero. No warn-and-continue for gates.

**Patterns:**
- Domain stubs raise `NotImplementedError` with milestone + SPEC pointer
- Config/secret missing → `RuntimeError` / pydantic `ValidationError` at load time (`entsoe_token()`, model validate)
- Planned ingest: typed errors (`IngestAuthError`, `ContractError`, `GateFailure`) with actionable context
- Retry/backoff only in planned `ingest._fetch` (tenacity); nowhere else
- Warnings reserved for non-contract anomalies (e.g. A03 fill counts)

## Cross-Cutting Concerns

**Logging:**
- `epra.common.logging.setup()` — stdlib logging, format `%(asctime)s %(levelname)s %(name)s %(message)s`, INFO to stdout
- Ingestion also writes `reports/ingestion/ingest_<date>.log`
- Module loggers via `logging.getLogger(__name__)`; never log the ENTSO-E token (A-7)

**Validation:**
- pydantic at config boundary; ING gate framework pre-warehouse; dbt tests in warehouse; golden/property tests for profile/strategies; GV-303 SSOT consistency script

**Authentication:**
- No user auth. Sole secret: `ENTSOE_API_TOKEN` via env/`.env` (EN-041). Guarded by `scripts/check_no_token_in_code.py` in pre-commit

**Timezones:**
- Stored UTC (`ts_utc`); analytic local Europe/Vienna. Only sanctioned conversion helpers: `src/epra/common/timeutil.py` and dbt `dim_calendar` (T-1)

**Import law (layering):**
- `common` → nothing in epra; `ingest` ↛ analytics/strategies/report; analytics/strategies ↛ ingest; data interfaces (marts/parquet) only — see `docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md`

**Spec supremacy:**
- Code must implement REQ IDs from `docs/SPEC-01…08`; silent deviation forbidden — ADR in `docs/ADR/` (A-1)

---

*Architecture analysis: 2026-07-20*
*Update when major patterns change*
