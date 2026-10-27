# SPEC-07 §5 — canonical interface. Every target idempotent (EN-050).
# Unimplemented targets fail LOUDLY with their milestone (AGENTS.md M0 rule) — never silently.
# Windows note: run via `make` from Git Bash / WSL, or invoke the underlying `uv run` commands.

UV ?= uv

.PHONY: setup backfill ingest validate-ingest geosphere calendar oespi oespi-reconcile \
        transform warehouse freshness profile analyze simulate ssot ssot-check export report dashboard-html \
        pbip-validate publish clean-fixture real-run \
        test test-live lint token-guard linkcheck all refresh

setup:               ## EN-030 — install exactly the committed uv.lock (ADR-012)
	$(UV) sync --frozen --extra dev
	$(UV) run pre-commit install

linkcheck:           ## dead relative links / anchors in tracked Markdown (network-free)
	$(UV) run python scripts/check_links.py

lint: token-guard linkcheck
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

transform:           ## M3 — SPEC-02: dbt build (models + tests); cost mart is built by `simulate`
	cd dbt && $(UV) run dbt build --exclude fct_procurement_cost_monthly+
	cp dbt/target/run_results.json dbt/target/run_results_transform.json

warehouse:           ## M3 — SPEC-02: full dbt build + human-readable build report (reports/warehouse/)
	cd dbt && $(UV) run dbt build
	$(UV) run python -m epra.warehouse.report

freshness:           ## M3 — DM-066 freshness gate on stg_prices_at_hourly (needs real, current data)
	cd dbt && $(UV) run dbt test --select freshness_stg_prices_at_hourly --vars '{check_freshness: true}'

# ------------------------------------------------------------- M4-M7 analysis + reporting ----
profile:             ## M4 — SPEC-03: styriametal_v1 + flat_baseload → data/processed/
	$(UV) run python -m epra.consumer.profile

analyze:             ## M5 — SPEC-04 A1→A2→A4→A3 from marts → reports/analytics/
	$(UV) run python -m epra.analytics

simulate:            ## M6 — SPEC-05 retrospective + forward risk + ST-602 gate, then re-expose costs via dbt
	$(UV) run python -m epra.strategies
	cd dbt && $(UV) run dbt build --select fct_procurement_cost_monthly+

ssot:                ## M6 — SPEC-08 GV-301/302: reports/NUMERIC_SSOT.md from tagged producer rows
	$(UV) run python scripts/generate_ssot.py

ssot-check:          ## GV-303 — README/EXEC_SUMMARY numbers ⊂ SSOT, SSOT fresh vs results
	$(UV) run python scripts/check_ssot_consistency.py

export:              ## M7 — SPEC-02 §7 / DM-070: exports/*.csv for Power BI
	$(UV) run python scripts/export_marts.py

report:              ## M7 — SPEC-06: data quality, executive charts, EXEC_SUMMARY, README blocks
	$(UV) run python -m epra.report

dashboard-html:      ## ADR-022 — static HTML twin of the Power BI report: exports/ → dashboards/html/index.html
	$(UV) run python -m epra.report.html_dashboard

PBIP_SCHEMA_DIR ?=
pbip-validate:       ## ADR-022 — PBIP JSON vs Microsoft schemas (offline copy: PBIP_SCHEMA_DIR=…; skips without)
	$(UV) run python scripts/validate_pbip.py $(if $(PBIP_SCHEMA_DIR),--schema-dir $(PBIP_SCHEMA_DIR),)

clean-fixture:       ## ADR-018 — delete synthetic fixture data (only if the fixture marker is present)
	$(UV) run python scripts/clean_fixture.py

real-run:            ## Full real-data run: clear fixture, ingest 2019 → last month, gates, make all
	@test -n "$$ENTSOE_API_TOKEN" || grep -qE '^ENTSOE_API_TOKEN=.{8,}' .env 2>/dev/null || \
	  { echo "ERROR: set ENTSOE_API_TOKEN (env or .env) first — see docs/REAL_DATA_RUN.md" >&2; exit 1; }
	$(MAKE) clean-fixture
	$(MAKE) backfill
	$(MAKE) geosphere
	$(MAKE) calendar
	$(MAKE) validate-ingest
	$(MAKE) all
	$(MAKE) freshness
	$(MAKE) warehouse

TARGET ?= local
publish:             ## ADR-020 — publish exports (+ raw for azure): make publish TARGET=local|azure
	$(UV) run python -m epra.cloud --target $(TARGET)

all: profile transform analyze simulate ssot export report dashboard-html ssot-check publish

refresh: ingest validate-ingest all freshness
