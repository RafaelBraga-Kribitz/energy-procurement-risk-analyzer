# BUILD_LOG (append-only, per AGENTS.md W-5)

One entry per milestone: date, what shipped, gate evidence, open questions.

---

## 2026-07-19 — M0 Bootstrap (complete) + breadth foundation

**Shipped**

- Repo layout exactly per SPEC-07 §2 (empty dirs with `.gitkeep`); git initialized.
- `pyproject.toml`: pinned deps per SPEC-07 §3, ruff (line 100), `mypy --strict`
  on `src/epra`, pytest with `--cov-fail-under=80` (EN-071); `uv.lock` committed
  (EN-030).
- Makefile per SPEC-07 §5 — `setup/lint/test` real; all pipeline targets fail
  loudly with their milestone ("not implemented", per AGENTS.md M0).
- `.pre-commit-config.yaml` (EN-003) incl. implemented
  `scripts/check_no_token_in_code.py` token guard (tested).
- CI `ci.yml` with lint + test jobs (EN-080 jobs 1–2; jobs 3–4 land with M3/M6).
- Config layer: `config/settings.yaml` (EN-040), `config/consumer_profile.yaml`
  (SPEC-03 §6 verbatim), `config/strategies.yaml` (SPEC-05 §8 verbatim), all
  loaded through validated pydantic models in `epra.common.config`
  (`load_settings` / `load_consumer_profile` / `load_strategy_config` /
  `entsoe_token` fail-fast per ING-021).
- `epra.common` implemented: `logging` (EN-060), `timeutil` (UTC/Vienna doctrine,
  peak-hour rule ING-110, DST hour counts), `db` (DuckDB helper, DM-001).
- `epra.report.format` (RP-703) and `epra.report.style` (RP-701/704, Okabe-Ito,
  fixed strategy colors) implemented and tested.
- `scripts/oespi_reconcile.py` (ING-101) implemented and tested — the M2 human
  transcription workflow is unblocked.
- Every other module exists as a typed stub whose docstring carries its binding
  spec contract + REQ IDs and whose body raises `NotImplementedError` naming its
  milestone (tested: `tests/unit/test_stubs_fail_loudly.py`).
- dbt skeleton: `dbt_project.yml`, committed `profiles.yml` (relative DuckDB
  path), `seeds/dim_strategy.csv` (SPEC-02 §4 verbatim), `dbt/README.md` M3 map.
- Governance: ADR-001 (light governance; governance-bootstrap kit NOT vendored —
  Charter O-5 / SPEC-08 §7), ADR-002 (typing stubs for mypy strict).
  README + LIMITATIONS skeletons with zero untagged/unSSOT'd numbers.

**Gate evidence** (M0: `make setup && make lint && make test`)

- `uv run ruff check` / `ruff format --check` / `mypy` — recorded in the M0
  commit; see CI once a remote exists.
- `uv run pytest` — all tests green, coverage above the 80% gate.

**Open questions / next steps (in build order)**

> Superseded in detail by `docs/EXECUTION_BLUEPRINT/` (2026-07-19, second
> entry below) — items remain valid; the blueprint decomposes them into tasks.

1. **Human, day-0 (R-1):** request the ENTSO-E API token now (SPEC-01 §2) —
   M1 blocks on it; M2 (GeoSphere/ÖSPI/calendar, no auth) can proceed meanwhile.
2. **Human/M2:** transcribe ÖSPI twice (entry1/entry2), run
   `python scripts/oespi_reconcile.py`; series/methodology choice needs an ADR
   (ING-102).
3. **M1 agent:** build `ingest/entsoe.py` + `ingest/validate.py` per module
   docstrings; fixtures first (EN-070), incl. the 15-min aggregation fixture
   (ING-062) and DST fixtures.
4. **M2 agent:** GeoSphere discovery (ING-091) writes `station_id` into
   `config/settings.yaml` + ADR-003; then flip
   `test_settings_geosphere_station_pending_discovery` to assert the chosen id.
5. **M3:** dbt models per `dbt/README.md`; add CI job 3 (fixture warehouse).
6. No remote configured yet — when the GitHub repo exists, push `main`, protect
   it with CI, and add the `ENTSOE_API_TOKEN` secret (EN-041); `refresh.yml`
   (EN-081..083) lands with M7.

---

## 2026-07-19 — Execution Blueprint (planning deliverable, owner-requested)

**Shipped:** `docs/EXECUTION_BLUEPRINT/00..14` — the repository's execution
operating manual: master plan with authority hierarchy + global DoR/DoD +
agent session protocol; phase roadmap with entry/exit/rollback; full WBS
(TP.01–TP.02, T1.01–T7.07, ~47 session-sized tasks with objectives, deps,
validation, acceptance criteria); module/class/function contracts; dependency
graphs + critical path + token-window parallel plan; per-milestone
implementation guides (client strategy, TZ recipes, investigation protocols,
bootstrap vectorization equivalence, SSOT/checker designs); checklists;
measurable quality + coding standards; pattern/anti-pattern catalogs (AP-01..22);
consolidated gate matrix; runnable DL-1..10 release script; extended risk
register (RB-9..18); traceability matrix; and 18 registered specification gaps
(SG-01..18) each with a proposed decision pending ADR adoption.

**Governance note:** the blueprint is a planning artifact subordinate to
Charter > SPEC > ADR (declared in 00_MASTER_PLAN §0.1); it introduces no new
gates, CI jobs, or ceremony (Charter O-5 respected).

**Open questions:** SG-01..SG-18 proposals await ADR adoption at their
scheduled tasks; token ETA ~2026-07-22 (TP.01); ÖSPI transcription (T2.05)
can start any time.

---

## 2026-07-21 — M1 ENTSO-E Ingestion (automated deliverables complete; live-data gate pending operator)

**Shipped**

- `epra.common` extended and `epra.ingest.entsoe` + `epra.ingest.validate`
  implemented per SPEC-01 §§2–8: `EntsoeRawClient` transport (ADR-003) with
  first-party Appendix-A XML parsers (`parse_publication_xml`,
  `parse_gl_xml`), UTC boundary conversion (ING-031), resolution persistence
  + inference (ING-060), A03 forward-fill (ING-063), long-format generation
  (ING-032), quarterly chunking (ING-030), retry/backoff + response caching
  (ING-006/009), request/token-safe logging (ING-008, A-7).
  `_io.write_month` (ING-003/004/005) is the single raw-parquet write
  boundary; `latest_complete_month()` implements ADR-005 (`min(AT, DE-LU)`
  complete price month).
- `epra.ingest.validate` implements all six M1 gates: ING-080 (hour coverage
  + DST 23/25 check), ING-081 (price plausibility bounds), ING-082 (annual
  mean plausibility table), ING-083 (negative-price presence), ING-084 (load
  plausibility), ING-085 (price/load join coverage). Gates fail loudly on
  empty input (no vacuous pass, A-2) and never warn-and-continue
  (`ValidationReport.raise_if_failed`).
- `Makefile` `backfill` / `ingest` / `validate-ingest` targets wired to the
  real CLIs (`python -m epra.ingest.entsoe --backfill|--incremental`,
  `python -m epra.ingest.validate`).
- ADR-003 (EntsoeRawClient transport + own parsers, adopts SG-01), ADR-004
  (pyarrow as the pinned pandas parquet engine), ADR-005
  (`latest_complete_month` = min(AT, DE-LU), adopts SG-02) — all merged and
  referenced from the relevant module docstrings.
- ING-070: `tests/test_raw_contracts.py` (24 parametrized drift-guard tests)
  plus four committed fixture parquets — `entsoe_prices_at_2024-01`,
  `entsoe_prices_delu_2024-01`, `entsoe_load_at_2024-01`,
  `entsoe_gen_at_2024-01` (≤200 rows each) — asserting exact SPEC-01 §7
  column layout, dtypes, UTC `ts_utc`, zone values, and ING-004 provenance
  columns. Fixtures were generated once via the real parsers run against the
  already-committed XML fixtures, through the real `_io.write_month`, then
  flattened into the `tests/fixtures/entsoe/` layout ING-070 expects.
  `entsoe_prices_delu` has no committed DE-LU-domain XML source yet, so its
  4-row frame was hand-built directly in the SPEC-01 §7 shape — logged as
  threat T-02-15 (accepted: small static fixtures, contract tests catch
  schema drift) in plan `02-07`'s threat register.

**Gate evidence (automated, offline — `make lint && make test`)**

- `uv run ruff check` / `mypy --strict` on `src/epra`: clean, 0 issues.
- `uv run pytest -m "not live"`: **169 passed**, coverage 95.87% (gate: 80%).
  Includes the 24 new ING-070 contract tests, all green with zero network
  access.
- ING-070 contract tests specifically: `uv run pytest tests/test_raw_contracts.py`
  — 24 passed, no network.

**PENDING OPERATOR ACTION — live backfill + `make validate-ingest` (ROADMAP
Phase 2 criteria 1 and 3)**

Plan `02-07` Task 2 is a blocking human checkpoint that requires the
operator's real `ENTSOE_API_TOKEN` and live network access to
`transparency.entsoe.eu` — neither is available to the automated executor
that produced this entry (A-2: no invented data under `data/raw/`; the
executor did not fabricate a backfill or a validation report). This gate
remains **the one open item** before M1 can be marked fully done end-to-end.
Operator, run exactly this:

1. Copy `.env.example` to `.env` and set `ENTSOE_API_TOKEN` (ING-020/021).
2. Run `make setup` (if needed), then `make lint && make test` — confirm all
   green including `test_raw_contracts` and the gate unit tests (should
   already be green per the automated evidence above; re-confirm locally).
3. Run `make backfill` — expect progress logs; verify
   `data/raw/entsoe_prices_at/`, `entsoe_prices_delu/`, `entsoe_load_at/`,
   `entsoe_gen_at/` contain `YYYY/*.parquet` files from 2019 onward.
4. Run `make validate-ingest` — expect
   `reports/ingestion/validation_*.md` with ING-080 through ING-085 all PASS.
5. If any gate fails: do not widen bands — investigate parser/timezone/units
   per A-2 and file an ADR if a spec deviation is genuinely needed.

Once steps 1–4 are green, M1 satisfies all three ROADMAP Phase 2 success
criteria (ING-070 contract tests in CI, real backfill under `data/raw/`,
`make validate-ingest` PASS on 2019→latest real data) and M2 (auxiliary data)
can start.

**Open questions:** none on the automated side. The single open item is the
operator-owned live backfill + validate-ingest run above.
