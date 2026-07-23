# SPEC-07 §5 — canonical interface. Every target idempotent (EN-050).
# Unimplemented targets fail LOUDLY with their milestone (AGENTS.md M0 rule) — never silently.
# Windows note: run via `make` from Git Bash / WSL, or invoke the underlying `uv run` commands.

UV ?= uv

.PHONY: setup backfill ingest validate-ingest geosphere calendar oespi transform profile \
        analyze simulate ssot export report test lint all refresh

setup:
	$(UV) venv --allow-existing
	$(UV) pip install -e ".[dev]"
	$(UV) run pre-commit install

lint:
	$(UV) run ruff check src tests scripts
	$(UV) run ruff format --check src tests scripts
	$(UV) run mypy

test:
	$(UV) run pytest

backfill:            ## M1 — SPEC-01 §4: full 2019→latest ingestion (all sources)
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

# ---------------------------------------------------------------- not yet implemented ----
transform:           ## M3 — dbt build (models + tests)
	@echo "ERROR: 'make transform' not implemented yet (M3 — SPEC-02)." >&2; exit 1

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

refresh: ingest validate-ingest all
