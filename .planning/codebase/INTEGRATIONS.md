# External Integrations

**Analysis Date:** 2026-07-20

## APIs & External Services

**Payment Processing:**
- Not applicable — offline analytics / portfolio project; no billing

**Email/SMS:**
- Not applicable

**External APIs:**

- ENTSO-E Transparency Platform — AT/DE-LU day-ahead prices, AT actual load, AT generation by type (D1, VERIFIED)
  - Integration method: `entsoe-py` (`EntsoePandasClient`); raw REST only with ADR (ING-022)
  - Auth: API token in `ENTSOE_API_TOKEN` env var (`.env` or GitHub Actions secret); never in YAML/logs (A-7, ING-021)
  - Client module: `src/epra/ingest/entsoe.py` (M1 — stub until implemented)
  - Rate / politeness: ≤90-day chunks, ≥0.5 s sleep (`config/settings.yaml` `ingest.entsoe_sleep_s`), retry via tenacity (ING-006/007/030)
  - Registration: https://transparency.entsoe.eu (human-owned account)

- GeoSphere Austria Data Hub — daily mean temperature Graz station (D3, VERIFIED)
  - Integration method: REST via `requests` to `https://dataset.api.hub.geosphere.at/v1` (`config/settings.yaml` `geosphere.base_url`)
  - Auth: none (public API)
  - Client module: `src/epra/ingest/geosphere.py` (M2 — stub; mandatory station discovery ING-091)
  - Dataset: `klima-v2-1d`, parameter `tl_mittel`; sleep ≥0.2 s (`geosphere_sleep_s`)

- Austrian Energy Agency — ÖSPI (Österreichischer Strompreisindex) — monthly Base/Peak index (D2, VERIFIED)
  - Integration method: **no machine API** — human double-entry transcription into CSV; reconcile with `scripts/oespi_reconcile.py` (ING-101)
  - Auth: none (public publication)
  - Loader: `src/epra/ingest/oespi.py` (M2 — stub); reconciled file `data/manual/oespi_monthly.csv`
  - Source page: https://www.energyagency.at/fakten/strompreisindex

- `holidays` PyPI package — Austrian national + Styrian subdiv holidays (D4, VERIFIED)
  - Integration method: local library (`holidays`, `subdiv='6'`), not an HTTP API
  - Client module: `src/epra/ingest/calendar.py` (M2 — stub)

## Data Storage

**Databases:**
- DuckDB (local single file) — analytical warehouse
  - Path: `data/warehouse/epra.duckdb` (`config/settings.yaml` `paths.warehouse`)
  - Connection: `epra.common.db.connect()` in `src/epra/common/db.py`; dbt profile in `dbt/profiles.yml` (relative path, no credentials)
  - Client: native `duckdb` Python API for mart reads; dbt-duckdb for transforms
  - Migrations: dbt models/tests/seeds under `dbt/` (not Alembic/Prisma)

**File Storage:**
- Local filesystem only (no S3/cloud object store)
  - Raw parquet: `data/raw/<dataset>/<YYYY>/…` (ING-003; gitignored)
  - Cache: `data/cache/` (ING-009; gitignored)
  - Manual: `data/manual/` (ÖSPI CSVs; committed when reconciled)
  - Processed / exports: `data/processed/`, `exports/` (gitignored CSVs for BI)
  - Reports: `reports/` (SSOT, analytics, charts)

**Caching:**
- HTTP/response cache on disk under `data/cache/` (ingest layer, ING-009) — not Redis
  - Cache used when request window ended > `cache_min_age_days` (default 7)

## Authentication & Identity

**Auth Provider:**
- None — no end-user login, sessions, or OAuth app
  - Only external credential: ENTSO-E API token (service credential for ingestion)

**OAuth Integrations:**
- Not applicable

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Datadog)

**Analytics:**
- None (product analytics N/A)

**Logs:**
- stdlib `logging` via `src/epra/common/logging.py` (EN-060)
  - INFO to stdout; optional file `reports/ingestion/ingest_<date>.log` for ingest runs
  - Per-request ingest lines (ING-008); token must never appear in logs (A-7)

## CI/CD & Deployment

**Hosting:**
- Not hosted as a service — runs on developer machines and GitHub Actions runners
  - Human Power BI Desktop consumes `exports/` CSVs → `dashboards/epra.pbix` (M7; see `dashboards/README.md`)

**CI Pipeline:**
- GitHub Actions — `.github/workflows/ci.yml`
  - Triggers: push/PR to `main`
  - Jobs live: `lint` (ruff check/format, mypy), `test` (`pytest -m "not live"`)
  - Planned (commented stubs): `dbt-check` (M3), `ssot-check` (M6) per EN-080
  - Secrets: `ENTSOE_API_TOKEN` for live/backfill workflows when added; CI unit tests need no network/token
- Planned: `.github/workflows/refresh.yml` (EN-081–083) — monthly cron `0 5 6 * *` + `workflow_dispatch`, `make refresh`, artifact upload, automated PR; **file not present yet** (M7)

## Environment Configuration

**Development:**
- Required env vars: `ENTSOE_API_TOKEN` for live ENTSO-E ingest / `@pytest.mark.live` only
- Secrets location: `.env` (gitignored; copy from `.env.example`); never commit token
- Mock/stub services: committed fixtures under `tests/fixtures/` for ENTSO-E/GeoSphere parsing (EN-070); ingest modules raise `NotImplementedError` until M1/M2
- Config YAML: `config/settings.yaml`, `config/consumer_profile.yaml`, `config/strategies.yaml`

**Staging:**
- Not applicable — no separate staging environment; fixture mini-warehouse used in CI for dbt (planned M3)

**Production:**
- “Production” = reproducible local/`make all` and scheduled GitHub refresh (when landed)
- Secrets management: GitHub Actions repository secret `ENTSOE_API_TOKEN` for refresh workflow
- Failover: none; gaps stay NULL and documented (A-2) — no synthetic market data

## Webhooks & Callbacks

**Incoming:**
- None — no HTTP server or webhook endpoints

**Outgoing:**
- None — no outbound webhooks; GitHub PR creation planned for refresh workflow only (CI automation, not an app webhook)

---

*Integration audit: 2026-07-20*
*Update when adding/removing external services*
