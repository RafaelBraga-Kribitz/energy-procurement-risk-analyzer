# SPEC-07 — Engineering, Tooling, CI/CD

Requirement IDs: `EN-xxx`.

---

## 1. Toolchain

- EN-001: Python 3.12, managed with `uv` (`uv venv`, `uv pip install -e ".[dev]"`).
- EN-002: Lint/format: `ruff` (lint + format), line length 100. Type hints mandatory on
  all public functions; `mypy --strict` on `src/epra/` (allow `ignore_missing_imports`
  for entsoe/hmmlearn/arch).
- EN-003: `pre-commit` hooks: ruff, ruff-format, end-of-file-fixer, check-yaml,
  detect-private-key, and a custom hook running `scripts/check_no_token_in_code.py`
  (greps for `securityToken=` followed by a literal).

## 2. Repository layout (create exactly this; empty dirs get `.gitkeep`)

```
energy-procurement-risk-analyzer/
├── PROJECT_CHARTER.md          ├── AGENTS.md
├── README.md                   ├── LIMITATIONS.md
├── LICENSE (MIT)               ├── Makefile
├── pyproject.toml              ├── .pre-commit-config.yaml
├── .env.example                ├── .gitignore
├── config/
│   ├── settings.yaml           # zones, window dates, geosphere station, paths
│   ├── consumer_profile.yaml   # SPEC-03 §6 verbatim
│   └── strategies.yaml         # SPEC-05 §8 verbatim
├── src/epra/
│   ├── ingest/    (entsoe.py, geosphere.py, oespi.py, calendar.py, validate.py)
│   ├── consumer/  (profile.py)
│   ├── analytics/ (descriptive.py, spread.py, regimes.py, weather.py)
│   ├── strategies/(calibration.py, retrospective.py, forward_risk.py)
│   ├── report/    (charts.py, format.py, style.py)
│   └── common/    (config.py, db.py, logging.py, timeutil.py)
├── dbt/           (dbt_project.yml, profiles.yml, models/, seeds/, tests/)
├── scripts/       (generate_ssot.py, export_marts.py, generate_golden_metrics.py,
│                   oespi_reconcile.py, check_ssot_consistency.py,
│                   check_no_token_in_code.py)
├── data/          (raw/, cache/, manual/, processed/, warehouse/ — all gitignored
│                   except manual/)
├── exports/       (gitignored except .gitkeep; refresh workflow uploads as artifact)
├── reports/       (committed: NUMERIC_SSOT.md, EXEC_SUMMARY.md, analytics/,
│                   strategies/, executive_charts/, ingestion/)
├── dashboards/    (epra.pbix, README.md)
├── docs/          (SPEC-01..08, ADR/, assets/)
└── tests/         (unit/, fixtures/, golden/)
```

## 3. Dependencies (pin these in `pyproject.toml`; upgrades require ADR)

Runtime: `pandas>=2.2,<3`, `numpy>=1.26,<3`, `duckdb>=1.0`, `dbt-core>=1.8,<2`,
`dbt-duckdb>=1.8,<2`, `entsoe-py>=0.6`, `requests>=2.32`, `tenacity>=8.3`,
`holidays>=0.50`, `arch>=7`, `hmmlearn>=0.3`, `statsmodels>=0.14`, `matplotlib>=3.8`,
`pydantic>=2.7`, `PyYAML>=6`, `python-dotenv>=1`.
Dev: `pytest>=8`, `pytest-cov`, `ruff`, `mypy`, `pre-commit`, `jupytext` (only if
notebooks are added; notebooks are OPTIONAL and never load-bearing).

- EN-030: `uv.lock` (or a pinned `requirements.txt` exported by uv) is committed.

## 4. Configuration & secrets

- EN-040: `config/settings.yaml` holds ALL non-secret settings: zones/EIC codes, analysis
  window dates, geosphere dataset+station, file path roots, chunk sizes, sleep intervals.
  Loaded once by `epra.common.config.load_settings()` into a pydantic model
  (`Settings`) — modules receive the object, never re-read YAML ad hoc.
- EN-041: Secrets: only `ENTSOE_API_TOKEN`, via env/.env (never in YAML). `.env.example`
  documents it. CI uses a repo secret of the same name.

## 5. Makefile (canonical interface; targets and their meaning)

```
setup            uv venv + install + pre-commit install
backfill         full 2019→latest ingestion (all sources)
ingest           incremental 45-day refresh (ING-041)
validate-ingest  SPEC-01 §8–§11 gates → reports/ingestion/
transform        dbt build (models + tests)
profile          build consumer load profiles (styriametal_v1 + flat_baseload)
analyze          SPEC-04 modules → reports/analytics/
simulate         SPEC-05 retrospective + forward risk
ssot             scripts/generate_ssot.py
export           scripts/export_marts.py → exports/
report           executive charts
test             pytest -q (with coverage gate ≥ 80% on src/)
lint             ruff check + format --check + mypy
all              transform→profile→analyze→simulate→ssot→export→report (assumes data present)
refresh          ingest→validate-ingest→all   (what the cron runs)
```

- EN-050: Every target is idempotent and safe to re-run. `make all` from clean data must
  finish < 30 min on a laptop.

## 6. Logging & errors

- EN-060: `epra.common.logging.setup()` — stdlib logging, format
  `%(asctime)s %(levelname)s %(name)s %(message)s`, INFO to stdout; ingestion also logs
  to `reports/ingestion/ingest_<date>.log`.
- EN-061: Fail-fast policy: pipeline steps raise on gate failure (non-zero exit) — no
  warn-and-continue for gates. Warnings are reserved for non-contract anomalies.

## 7. Testing policy

- EN-070: Unit tests never hit the network. All ENTSO-E/GeoSphere parsing tested on
  committed fixtures (`tests/fixtures/`, small real excerpts; scrub nothing — data is
  public). One optional `@pytest.mark.live` suite hits real APIs; excluded in CI.
- EN-071: Coverage gate: `--cov=src/epra --cov-fail-under=80`.
- EN-072: Golden tests: SPEC-03 LP-040 and SPEC-05 ST-601. Golden regeneration only via
  `scripts/generate_golden_metrics.py` and only in a PR that explains why.
- EN-073: Every bug found after M3 gets a regression test in the same PR that fixes it.

## 8. GitHub Actions

### `ci.yml` (push + PR to main)

- EN-080: Jobs: (1) lint (ruff + mypy); (2) test (pytest, no network, coverage gate);
  (3) dbt-check: `dbt build` against a mini-warehouse built from `tests/fixtures/`
  parquet (a fixture bootstrap script creates data/raw from fixtures); (4) ssot-check:
  `scripts/check_ssot_consistency.py` (SPEC-08 §4). All four required for merge.

### `refresh.yml` (cron)

- EN-081: Schedule: `cron: '0 5 6 * *'` (06th of each month, 05:00 UTC — ENTSO-E and
  ÖSPI publication comfortably settled for the prior month). Also `workflow_dispatch`.
- EN-082: Steps: checkout → setup uv/python → `make refresh` with `ENTSOE_API_TOKEN`
  secret → upload `exports/` + `reports/` as workflow artifacts → open an automated PR
  (peter-evans/create-pull-request or equivalent) containing ONLY changed committed
  report files (SSOT, analytics md/png, executive charts). Never auto-push to main.
- EN-083: ÖSPI is manual: the refresh workflow checks whether
  `data/manual/oespi_monthly.csv` covers the latest complete month; if not, the PR body
  says so and strategy outputs for the uncovered month are suppressed (not extrapolated).

## 9. Git conventions

- EN-090: Conventional commits (`feat:`, `fix:`, `data:`, `docs:`, `test:`, `chore:`).
  One milestone = one PR (AGENTS.md). `main` is protected by CI.
- EN-091: `.gitignore` covers: `.venv/`, `data/raw/`, `data/cache/`, `data/processed/`,
  `data/warehouse/`, `exports/*.csv`, `.env`, `__pycache__/`, `.pytest_cache/`,
  `dbt/target/`, `dbt/logs/`.
