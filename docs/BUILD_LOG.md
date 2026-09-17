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

---

## 2026-07-22 — M1 live backfill run: two data-loss bugs found and fixed

The live backfill (2019→latest) was run against the real ENTSO-E Transparency
Platform with the operator token in `.env`. It surfaced two bugs that every
single-document offline fixture had masked:

1. **ENTSO-E 100-document response cap (silent truncation).** ING-030's ≤90-day
   window is necessary but not sufficient: ENTSO-E caps a response at 100 market
   documents, and AT/DE-LU day-ahead prices come back as ~2 TimeSeries per
   delivery day, so a 90-day request returned only its first ~50 days. Every
   year held ~4,880/8,760 price hours (~44% missing). Fixed: `ingest_dataset`
   now pages each chunk, resuming from the day after the last covered day until
   the window is filled (`fix(EPRA-02)` pagination commit).
2. **Chunk-boundary month overwrite.** Adjacent Vienna-aligned chunks overlap by
   the UTC-boundary hour (a "January" Vienna chunk starts Dec 31 23:00 UTC), so
   writing per-chunk let a later chunk's 1-hour sliver overwrite a prior chunk's
   full month — interior months collapsed to ~2 hours. Fixed: accumulate all of
   a dataset's frames, de-duplicate, and write each UTC month once.

Regression test added simulating the 100-document cap. `make lint && make test`
green (178 tests, ~96% coverage).

**Gate evidence after the fix (real 2019→2024-01 data):** complete years
2019–2023 hold full ~8,760 hourly prices (2020 leap = 8,784) and pass ING-080
coverage and ING-082 plausibility. ING-081/084/085 PASS.

**Remaining gate reds are boundary/horizon artifacts, not data loss (operator
decision, do not widen bands per A-2):**
- ING-080 fails only for **2018** (a 1-hour Dec-2018 UTC-boundary sliver created
  because backfill starts at 2019-01-01 Vienna = 2018-12-31 23:00 UTC) and
  **2024** (partial — the real ENTSO-E data horizon is ~Jan 2024).
- ING-082 fails only for the **2018** sliver (no plausibility-table entry).
- ING-083 expects negative prices in 2023/2024/2025; **2025** has no data
  (horizon), so it fails.

**Resolved (ADR-006).** The boundary/horizon gate reds were not data defects but
a domain-alignment bug: the gates bucketed per-year checks by **UTC** year,
contradicting T-1 (analytics are Vienna-local) and manufacturing the phantom
"2018" year from the Jan-1-2019 00:00 Vienna = Dec-31-2018 23:00 UTC hour.
ADR-006 groups the gates by **Vienna-local** year and asserts pass/fail only for
years the ingest window fully spans; the leading/trailing boundary years are
reported informationally, never failed, and never trimmed (no data discarded).
ING-083 now checks the spec-required years that are *complete* in the data (today
2023), extending to 2024/2025 automatically. On the real 2019→2024-01 data
**`make validate-ingest` exits 0 — ALL GATES PASSED (ING-080..085)**; 2024 is
reported as a boundary partial. All three ROADMAP Phase 2 success criteria are
met end-to-end: ING-070 contract tests in CI, real backfill under `data/raw/`,
and `make validate-ingest` green on real data. **M1 complete; M2 can start.**

---

## 2026-07-24 — M3 dbt Warehouse (SPEC-02) — both builds green, schema contract byte-matched

**Shipped**

- Full dbt project (`dbt/`): sources (`sources.yml`, all 9 raw/manual/processed
  datasets via `../data/`-prefixed `read_parquet`/`read_csv` globs, DM-004),
  `generate_schema_name` macro (ADR-009 — literal `staging`/`marts` schemas),
  8 staging models, `dim_calendar` + `dim_strategy` (seed), 6 marts
  (`fct_price_hourly`, `fct_price_daily`, `fct_price_monthly`,
  `fct_generation_monthly`, plus the two D-05/SG-06 stand-in marts
  `fct_consumer_load_hourly`/`fct_procurement_cost_monthly` feeding M4/M6),
  the DM-060..066 test suite (generic + 5 singular tests: DM-062 row-count
  boundary, DM-064 2022-08 reconciliation, DM-065 DST adjacency, DM-050
  no-gap month spine, DM-066 var-gated freshness), and the D-07 hand-authored
  `dbt/contracts/marts_contract.yml` schema contract.
- `src/epra/warehouse/report.py` (D-02): reads the built warehouse read-only
  and renders `reports/warehouse/dbt_build_<date>.md` (per-year row counts,
  month coverage, 2022-08 reconciliation delta, stand-in-mart flags);
  `make transform` un-stubbed to `dbt build`, new `make warehouse` composes
  transform + report.
- `scripts/bootstrap_fixture_warehouse.py` (D-04/SG-06/ADR-010): deterministic,
  seeded synth of a contiguous 2022-2024 fixture warehouse (raw + manual +
  processed) for CI, plus a `--processed-only` mode safe to run against real
  local data.
- `.github/workflows/ci.yml`: required `dbt-check` job (EN-080 job 3) —
  `bootstrap_fixture_warehouse.py --force` then `cd dbt && dbt build`,
  network-free, a genuinely separate job from `test:`.
- `tests/unit/test_marts_contract.py` (D-07): `information_schema.columns`
  diff vs. the hand-authored contract, all 6 marts.

**Gate evidence — BOTH builds green (M3 exit gate, T3.07)**

1. **Local real-data build (D-01, SC#1)** — `make warehouse` on real
   `data/raw` 2019→latest (calendar horizon extends to 2028):
   **`dbt build`: PASS=63 WARN=1 (pre-existing `predup_count_prices`,
   informational, unrelated to this milestone) ERROR=0 SKIP=0 TOTAL=64**.
   `reports/warehouse/dbt_build_2026-07-24.md` committed: 10 years of
   `fct_price_hourly` row counts, 3 monthly marts' month coverage, the
   2022-08 reconciliation delta = `0.0000` (`482.7263` both sides), and both
   future marts flagged `stand-in (M4/M6 pending)`.
2. **CI fixture build (D-03/D-04, SC#3)** — verified locally by cloning this
   repository into an isolated, disposable checkout (empty `data/`) and
   running the exact CI sequence: `bootstrap_fixture_warehouse.py --force`
   then `cd dbt && dbt build` — **PASS=64 WARN=0 ERROR=0 SKIP=0 TOTAL=64**,
   fully network-free. This repository's real `data/raw`/`data/manual` were
   never touched (a separate, disposable clone was used, then deleted).
3. **D-07 schema contract (SC#2)** — `uv run pytest
   tests/unit/test_marts_contract.py -m "not live" --no-cov`: **6 passed**
   (all 6 marts byte-match `dbt/contracts/marts_contract.yml`).
4. **Full non-live suite** — `uv run pytest -m "not live"`: **259 passed, 2
   skipped**, coverage 92.48% (gate: 80%).
5. **`git status` clean of `data/`** — `epra.duckdb`, synthesized/real
   `data/raw`, `data/processed` all remain gitignored (`!!` in
   `git status --ignored`); only the markdown build report + this BUILD_LOG
   entry are committed (DM-001/D-02). (Three pre-existing, unrelated manual
   reference PDFs under `data/manual/` remain untracked from before this
   plan — out of scope, not committed here.)

**Open questions:** none on the automated side. The GitHub push, branch-
protection required-check flip for `dbt-check` (TP.02), and M3 PR opening
remain human-only per the phase-exit checkpoint (D-01/D-02).

---

## 2026-09-02 — M4 Consumer Profile (T4.05 operator close-out)

**Shipped**

- `python -m epra.consumer.profile` CLI (`--profile` optional override via
  `cfg.model_copy`). Missing `data/raw/calendar/calendar.parquet` exits 1
  with an actionable `make calendar` hint (D-01).
- `make profile` un-stubbed to that CLI; **does not** invoke dbt.
- `all:` order is `profile transform analyze simulate ssot export report`
  (D-08) so a full pipeline never feeds the consumer stand-in into dbt.
- Warehouse report `_STAND_IN_MARTS` is only `fct_procurement_cost_monthly`
  (consumer mart is M4 profile output).
- LIMITATIONS.md §1 already contains the LP-051 sentence (constructed, not
  measured; RLM would change levels not ordinal ranking; `flat_baseload`
  bounds shape). Confirmed; no M6 sensitivity euros invented.

Prior M4 plans on this stack (05-01..05-04): vectorized weights + ADR-012;
LP-004/LP-034 normalization; LP-003 parquet + ADR-013 2019 peak share;
LP-040 golden `tests/golden/consumer_load_2023.sha256`; LP-030 `flat_baseload`.

**Gate evidence**

```
make lint
  ruff check: All checks passed
  ruff format --check: 62 files already formatted
  mypy: Success: no issues found in 32 source files

uv run pytest tests/unit/test_profile.py tests/unit/test_warehouse_report.py \
  -m "not live" --no-cov -q
  38 passed

uv run pytest -m "not live"
  287 passed, 2 skipped, 1 deselected
  coverage 92.64% (gate: 80%)
```

CLI second-run hourly parquet is byte-identical (no `ingested_at_utc`).
`rg -n "^all: profile transform" Makefile` matches.

**Open questions**

- Golden regeneration (EN-072 / ST-601 analog): human approval required;
  do not rewrite `tests/golden/consumer_load_2023.sha256` without a diff + why.
- Real-data `make profile` still needs a local `calendar.parquet`
  (`make calendar`). This cloud checkout has no `data/raw/` backfill (A-2).
- 2019 `consumer_peak_share` is ~0.486 (ADR-013); YAML was **not** retuned
  to force the informal 0.48 cap (A-2, LP-002).

---

## 2026-09-03 — M5 Analytics (T5.07 operator close-out)

**Shipped**

- Shared kit (`_kit.py`) plus `python -m epra.analytics` (A1 → A2 → A4 → A3).
- A1 descriptive: annual table+CSV, 2021-2025 heatmap (empty panel if incomplete),
  duration curves (2022 vermillion, linear EUR/MWh), negative hours, AN-105 prose.
- A2 AT−DE-LU spread: monthly zero line, yearly stats, localization prose.
- A4 system load vs mart HDD_18 (month FE, HC1); StyriaMetal weather-invariance sentence.
- A3 HMM (seeds 42-51, BLAS pin, AN-304 skip-if-incomplete / fail-closed) + GARCH(1,1)
  overlay; `garch_persistence` VERIFIED; α+β never clamped.
- `make analyze` is `$(UV) run python -m epra.analytics` (does not invoke dbt).
- SSOT producer `ssot_inputs_analytics.parquet` upserts by key (tag=VERIFIED).
- No fixture-warehouse PNGs committed (D-05 / A-2).

**Gate evidence**

```
make lint
  ruff check: All checks passed
  ruff format --check: 70 files already formatted
  mypy: Success: no issues found in 34 source files

uv run pytest tests/unit/test_analytics_gates.py -m "not live" --no-cov -q
  AN-701 12 SPEC-04 filenames; AN-705 two-run SSOT identity — passed

uv run pytest -m "not live"
  330 passed, 2 skipped, 1 deselected
  coverage 93.21% (gate: 80%)
```

No invented market EUR in this entry. AN-304 on a real 2019+crisis window is an
operator run (`make warehouse && make analyze`); this checkout has no `data/raw/`.

**Open questions**

- AN-304 on real 2021-2023 (and 2019 calm) remains operator/ROADMAP SC#2.
- Do not commit CI-fixture `reports/analytics/*` as Q2 evidence (D-05).
- TP.02 (`dbt-check` required on `main`) and EN-072 golden regen still human.

---

## 2026-09-03 — M6 Strategy simulator (T6.10 operator close-out)

**Shipped**

- Shared ST-101 aligner; ST-201..204 anchors; S1–S4 monthly costs; annual
  summary, ST-304 charts, dual-write parquet; exactly three ST-303 sensitivities.
- ST-406 cost cells + seeded bootstrap (ADR-014 day-map, ADR-015 quantile/CVaR).
- SSOT assembler (GV-301/302, ADR-016 mtime `updated_at`) and GV-303 checker
  (Decimal ROUND_HALF_UP) plus CI job `ssot-check` (not GitHub-required).
- Synthetic ST-601 golden `tests/golden/strategy_annual_summary.json` — **engine
  contract only, not Austrian market evidence** (D-19).
- `make simulate` = `python -m epra.strategies.retrospective` then
  `python -m epra.strategies.forward_risk`. `make ssot` =
  `python scripts/generate_ssot.py`. Neither invokes dbt.
- M6 loud stubs removed; M7 `render_executive_charts` remains.
- No fixture-warehouse euros committed as Q1/Q3 evidence (D-04).
  `reports/NUMERIC_SSOT.md` is not in this checkout.

**Gate evidence**

```
make lint
  ruff check: All checks passed
  ruff format --check: 86 files already formatted
  mypy: Success: no issues found in 40 source files

uv run pytest tests/test_golden_strategies.py tests/unit/test_strategies_gates.py \
  tests/unit/test_stubs_fail_loudly.py -m "not live" --no-cov -q
  8 passed

uv run pytest -m "not live"
  392 passed, 2 skipped, 1 deselected
  coverage 92.55% (gate: 80%)
```

No invented market EUR in this entry. The committed golden lists toy costs
(S1=120, S3=100 EUR on 10 MWh) that exist only to pin `annual_summary`.

**Open questions**

- ST-602(a) on a real 2019+2022 warehouse remains operator (`make warehouse &&
  make simulate`); this checkout has no `data/raw/`. If (a) fails, debug
  calibration — do not widen the gate.
- Human approval before replacing the synthetic ST-601 JSON with real-warehouse
  euros (EN-072 / AGENTS §2.6).
- Commit `reports/NUMERIC_SSOT.md` only from a real `make ssot` (D-04).
- Mark GitHub `ssot-check` (and `dbt-check`) required on `main` (operator / TP.02).
- Forward `run()` still needs an injected/SPEC-03 forward-window profile for a
  live next-12-month horizon (production currently reuses pool hours when
  `horizon_hours` is omitted).


