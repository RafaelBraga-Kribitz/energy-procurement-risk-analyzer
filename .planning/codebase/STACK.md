# Technology Stack

**Analysis Date:** 2026-07-20

## Languages

**Primary:**
- Python 3.12 (pinned `>=3.12,<3.13` / `==3.12.*` in lock) — all application code under `src/epra/`, tests under `tests/`, CLI scripts under `scripts/`

**Secondary:**
- SQL (dbt models) — warehouse transforms under `dbt/models/` (staging + marts; skeleton at M0, models land at M3)
- YAML — project config (`config/*.yaml`), dbt (`dbt/dbt_project.yml`, `dbt/profiles.yml`), CI (`.github/workflows/ci.yml`)
- Makefile — canonical pipeline interface (`Makefile`; invoke via Git Bash/WSL on Windows)
- Markdown — specs, charter, reports (`docs/`, `reports/`, `PROJECT_CHARTER.md`)

## Runtime

**Environment:**
- CPython 3.12.x only (SPEC-07 EN-001)
- Batch / CLI analytics pipeline — no web server, no browser runtime
- Local filesystem + in-process DuckDB (no remote app runtime)

**Package Manager:**
- `uv` (Astral) — `uv venv`, `uv pip install -e ".[dev]"`, `uv run …` (EN-001)
- Lockfile: `uv.lock` present (revision 3, `requires-python = "==3.12.*"`)
- Build backend: `hatchling` (`pyproject.toml` `[build-system]`; wheel packages `src/epra`)

## Frameworks

**Core:**
- None (no web/UI framework). Domain pipeline composed as Python packages + dbt.
- dbt-core 1.12.x + dbt-duckdb 1.10.x — analytical warehouse transforms (`dbt/`)
- pydantic 2.13.x — frozen config models in `src/epra/common/config.py` (EN-040)

**Testing:**
- pytest 9.x + pytest-cov — unit/contract tests; coverage fail-under 80% on `epra` (EN-070/071)
- Marker `live` — optional real-API suite; excluded in CI (`pytest -m "not live"`)

**Build/Dev:**
- ruff 0.15.x — lint + format (`target-version = "py312"`, line-length 100)
- mypy 2.x — `--strict` on `src/epra` (EN-002); stubs for pandas/PyYAML/requests; ignore_missing_imports for `entsoe.*`, `hmmlearn.*`, `arch.*`, `statsmodels.*`
- pre-commit — ruff, ruff-format, end-of-file-fixer, check-yaml, detect-private-key, custom ENTSO-E token guard (`scripts/check_no_token_in_code.py`)
- hatchling — package build for editable install `epra`

## Key Dependencies

**Critical:**
- pandas 2.3.x / numpy 2.5.x — time series, frames, analytics I/O
- duckdb 1.5.x — single-file warehouse at `data/warehouse/epra.duckdb` (`src/epra/common/db.py`)
- entsoe-py 0.8.x — ENTSO-E Transparency client (`EntsoePandasClient`; M1 ingest)
- requests 2.34.x + tenacity 9.x — GeoSphere HTTP + retry/backoff (ING-006/007)
- holidays 0.100 — Austrian/Styrian calendar (`subdiv='6'`; M2)
- arch 8.x / hmmlearn 0.3.x / statsmodels 0.14.x — volatility regimes (SPEC-04 A3; M5)
- matplotlib 3.11.x — executive charts, Agg backend (SPEC-06 RP-701; no seaborn for exec charts)
- PyYAML 6.x + python-dotenv 1.x — config YAML load + `.env` for `ENTSOE_API_TOKEN`

**Infrastructure:**
- dbt-core / dbt-duckdb — SQL models, tests, seeds against DuckDB profile `epra`
- stdlib `logging` + `zoneinfo` — logging (`src/epra/common/logging.py`) and Europe/Vienna time (`src/epra/common/timeutil.py`)

## Configuration

**Environment:**
- Non-secrets: `config/settings.yaml`, `config/consumer_profile.yaml`, `config/strategies.yaml` — loaded once via pydantic (`load_settings`, `load_consumer_profile`, `load_strategy_config`)
- Secret: `ENTSOE_API_TOKEN` only — via `.env` (gitignored) or process env; template in `.env.example` (EN-041, ING-021)
- GeoSphere base URL / dataset / station fields live in `config/settings.yaml` under `geosphere:` (no auth)

**Build:**
- `pyproject.toml` — deps, ruff, mypy, pytest, coverage, hatch packages
- `uv.lock` — pinned transitive resolution
- `Makefile` — `setup`, `lint`, `test`; M1–M7 targets stubbed to fail loudly until implemented
- `.pre-commit-config.yaml` — local + astral/pre-commit hooks
- `dbt/profiles.yml` — DuckDB path `../data/warehouse/epra.duckdb`, no credentials
- `.github/workflows/ci.yml` — lint + test jobs (dbt-check / ssot-check commented until M3/M6)

## Platform Requirements

**Development:**
- Any OS with Python 3.12 + `uv` (Windows supported; Makefile via Git Bash/WSL or run `uv run` commands directly)
- Disk for `data/raw`, `data/cache`, `data/warehouse` (gitignored generated paths)
- Optional: ENTSO-E API token for live backfill / `@pytest.mark.live`
- Optional: Power BI Desktop at M7 for human `.pbix` build from `exports/`

**Production:**
- Not a hosted app — local or CI batch runs
- GitHub Actions (ubuntu-latest) for CI; planned monthly `refresh.yml` cron (SPEC-07 EN-081; not present yet)
- Deliverables: `reports/` (SSOT, charts), `exports/*.csv`, optional Power BI file under `dashboards/`

---

*Stack analysis: 2026-07-20*
*Update after major dependency changes*
