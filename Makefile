# SPEC-07 §5 — canonical interface. Every target idempotent (EN-050).
# Unimplemented targets fail LOUDLY with their milestone (AGENTS.md M0 rule) — never silently.
# Windows note: run via `make` from Git Bash / WSL, or invoke the underlying `uv run` commands.

UV ?= uv

.PHONY: setup backfill ingest validate-ingest geosphere calendar oespi oespi-reconcile \
        transform warehouse freshness profile analyze simulate ssot export report \
        test test-live lint token-guard all refresh

setup:               ## EN-030 — install exactly the committed uv.lock (ADR-012)
	$(UV) sync --frozen --extra dev
	$(UV) run pre-commit install

lint: token-guard
	$(UV) run ruff check src tests scripts
	$(UV) run ruff format --check src tests scripts
	$(UV) run mypy

token-guard:         ## A-7 / EN-003 — no ENTSO-E token literal in any tracked file
	git ls-files -z | xargs -0 $(UV) run python scripts/check_no_token_in_code.py

test:                ## EN-070 — offline suite, same selection as CI
	$(UV) run pytest -m "not live" --cov=epra --cov-fail-under=80 --cov-report=term-missing

test-live:           ## EN-070 — live API tests only (needs network; ENTSO-E ones need the token)
	$(UV) run pytest -m live

backfill:            ## M1 — SPEC-01 §4: full 2019→last complete month, ENTSO-E only (GeoSphere/calendar/ÖSPI: own targets)
	$(UV) run python -m epra.ingest.entsoe --backfill

ingest:              ## M1 — SPEC-01 §4: incremental 45-day refresh (ING-041)
	$(UV) run python -m epra.ingest.entsoe --incremental

validate-ingest:     ## M1/M2 — SPEC-01 §§8-11 gates → reports/ingestion/
	$(UV) run python -m epra.ingest.validate

geosphere:           ## M2 — SPEC-01 §9: GeoSphere daily temperature 2019 → latest (ING-093)
	$(UV) run python -m epra.ingest.geosphere

calendar:            ## M2 — SPEC-01 §11: hourly UTC calendar spine (ING-110)
	$(UV) run python -m epra.ingest.calendar

oespi:               ## M2 — SPEC-01 §10: ÖSPI loader + series gates (ING-103)
	$(UV) run python -m epra.ingest.oespi

oespi-reconcile:     ## M2 — ING-101: double-entry reconcile of data/manual/oespi_monthly_entry{1,2}.csv
	$(UV) run python scripts/oespi_reconcile.py --dir data/manual

transform:           ## M3 — SPEC-02: dbt build (models + tests)
	cd dbt && $(UV) run dbt build

warehouse:           ## M3 — SPEC-02: dbt build + human-readable build report (reports/warehouse/)
	$(MAKE) transform
	$(UV) run python -m epra.warehouse.report

freshness:           ## M3 — DM-066 freshness gate on stg_prices_at_hourly (needs real, current data)
	cd dbt && $(UV) run dbt test --select freshness_stg_prices_at_hourly --vars '{check_freshness: true}'

# ---------------------------------------------------------------- not yet implemented ----
profile:             ## M4 — consumer load profiles (styriametal_v1 + flat_baseload)
	@echo "ERROR: 'make profile' not implemented yet (M4 — SPEC-03)." >&2; exit 1

analyze:             ## M5 — SPEC-04 modules → reports/analytics/
	@echo "ERROR: 'make analyze' not implemented yet (M5 — SPEC-04)." >&2; exit 1

simulate:            ## M6 — SPEC-05 retrospective + forward risk
	@echo "ERROR: 'make simulate' not implemented yet (M6 — SPEC-05)." >&2; exit 1

ssot:                ## M6 — scripts/generate_ssot.py
	@echo "ERROR: 'make ssot' not implemented yet (M6 — SPEC-08 GV-301)." >&2; exit 1

export:              ## M7 — scripts/export_marts.py → exports/
	@echo "ERROR: 'make export' not implemented yet (M7 — SPEC-02 §7)." >&2; exit 1

report:              ## M7 — executive charts
	@echo "ERROR: 'make report' not implemented yet (M7 — SPEC-06 §2)." >&2; exit 1

all: transform profile analyze simulate ssot export report

refresh: ingest validate-ingest freshness all
