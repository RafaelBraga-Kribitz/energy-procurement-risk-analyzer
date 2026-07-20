# Codebase Concerns

**Analysis Date:** 2026-07-20

## Tech Debt

**Milestone stubs across the analytic pipeline (intentional M0 scaffolding):**
- Issue: Almost all domain modules raise `NotImplementedError` naming their milestone; Makefile pipeline targets and several scripts `sys.exit("not implemented yet …")`.
- Files: `src/epra/ingest/entsoe.py`, `src/epra/ingest/validate.py`, `src/epra/ingest/geosphere.py`, `src/epra/ingest/oespi.py`, `src/epra/ingest/calendar.py`, `src/epra/consumer/profile.py`, `src/epra/analytics/{descriptive,spread,regimes,weather}.py`, `src/epra/strategies/{calibration,retrospective,forward_risk}.py`, `src/epra/report/charts.py`, `scripts/{generate_ssot,check_ssot_consistency,export_marts,generate_golden_metrics}.py`, `Makefile` (`backfill`…`report`)
- Why: AGENTS.md M0 rule — fail loudly, never silently; stubs carry binding REQ IDs in docstrings (`docs/BUILD_LOG.md` 2026-07-19).
- Impact: `make all` / `make refresh` cannot produce SSOT, exports, or charts; DL-1…DL-10 unmet until M1–M7 land.
- Fix approach: Replace stubs milestone-by-milestone per Charter §7; delete corresponding rows from `tests/unit/test_stubs_fail_loudly.py` as each API becomes real.

**Eighteen specification gaps still `proposed` (not yet ADRs):**
- Issue: Ambiguities that affect parsers, calendar windows, peak definition, bootstrap day-mapping, P95/CVaR method, dbt schema naming, and SSOT rounding are recorded but not binding until ADR adoption.
- Files: `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` (SG-01…SG-18); only ADR-001/002 exist under `docs/ADR/`
- Why: Blueprint proposes decisions; GV-201..203 require ADR at the implementing task (not silent adoption).
- Impact: Agents implementing M1+ without the scheduled ADR can diverge from the intended OUTPUT CONTRACT or re-litigate the same ambiguity later.
- Fix approach: Adopt the listed ADR at the WBS task named in the SG table (e.g. SG-01 at T1.02) before coding against the interpretation.

**dbt warehouse is skeleton-only:**
- Issue: `dbt/models/staging/` and `dbt/models/marts/` contain only `.gitkeep`; no `sources.yml`, no schema-contract YAML, no CI dbt job.
- Files: `dbt/`, `dbt/README.md`, `.github/workflows/ci.yml` (jobs 3–4 commented)
- Why: M3 not started; M0 shipped project config + `seeds/dim_strategy.csv` only.
- Impact: No warehouse marts; analytics/strategies cannot read real facts; CI cannot gate schema contracts.
- Fix approach: Implement per `dbt/README.md` + SPEC-02; enable EN-080 job 3; apply SG-13 schema-name macro at T3.01.

**Coverage gate currently satisfied largely by stub-raise tests:**
- Issue: Parametrized tests in `tests/unit/test_stubs_fail_loudly.py` execute every stub and count toward `--cov-fail-under=80` while real logic is absent.
- Files: `tests/unit/test_stubs_fail_loudly.py`, `pyproject.toml` `[tool.pytest.ini_options]` / `[tool.coverage.*]`
- Why: M0 needs green CI with loud stubs; EN-071 gate is active from day one.
- Impact: As stubs are deleted (RB-12), coverage can drop below 80% mid-PR if implementation lands without matching tests (violates W-1).
- Fix approach: Same-commit TDD (W-1); never use per-module coverage exemptions (RB-12 fallback forbids them).

**GeoSphere station not discovered:**
- Issue: `geosphere.station_id` / `station_name` are `null` in settings; test asserts pending discovery.
- Files: `config/settings.yaml`, `tests/unit/test_config.py` (`test_settings_geosphere_station_pending_discovery`), stub `src/epra/ingest/geosphere.py`
- Why: ING-091 discovery + ADR required before pinning a station (R-7).
- Impact: M2 temperature ingest cannot run until discovery writes a concrete id.
- Fix approach: Run discovery at T2.x, write ADR-003, flip the pending test to assert the chosen id (`docs/BUILD_LOG.md` open question 4).

**ÖSPI manual series absent:**
- Issue: `data/manual/` has only `.gitkeep`; no `oespi_monthly_entry{1,2}.csv` or reconciled `oespi_monthly.csv`.
- Files: `data/manual/`, `scripts/oespi_reconcile.py` (implemented)
- Why: Human/double-entry transcription is M2 (ING-101); reconcile script is ready.
- Impact: Contract/index strategies (S3) and forward proxy calibration cannot proceed; ING-103 MoM gate blocked.
- Fix approach: Two independent transcriptions → `python scripts/oespi_reconcile.py` → commit reconciled CSV; ADR for series/methodology (ING-102).

**No Git remote / refresh cron / GitHub secret:**
- Issue: No `git remote`; no `refresh.yml`; ENTSO-E token cannot be stored as a Actions secret yet.
- Files: `.github/workflows/ci.yml` only; `docs/BUILD_LOG.md` open question 6
- Why: M0 local bootstrap; EN-081..083 and remote protection land with M7 / when GitHub exists.
- Impact: DL-8 (monthly refresh) impossible; CI not enforced on a protected `main`.
- Fix approach: Create remote, push, protect `main` with CI, add `ENTSOE_API_TOKEN` secret, land `refresh.yml` at M7 (SG-18 empty-diff behavior).

## Known Bugs

**No confirmed runtime defects in implemented M0 surface.**
- Symptoms: N/A — `epra.common` (config, timeutil, db, logging), `epra.report.{format,style}`, and `scripts/{oespi_reconcile,check_no_token_in_code}.py` have unit tests and no open bug reports in `docs/BUILD_LOG.md`.
- Trigger: N/A
- Workaround: N/A
- Root cause: Domain pipelines are stubs; defects will surface when M1+ parsers and simulators land.

**Latent peak-definition inconsistency (pre-bug if coded wrong):**
- Symptoms: Charter glossary peak omits holiday exclusion; ING-110 / `timeutil.is_peak_hour` exclude holidays — anchors and ÖSPI peak may disagree if both definitions are mixed.
- Trigger: Implementing `price_peak_eur_mwh` or ST-202 anchors using Charter glossary wording instead of `is_peak_hour`.
- Files: `PROJECT_CHARTER.md` §10 glossary, `src/epra/common/timeutil.py`, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` (SG-14)
- Workaround: Use `is_peak_hour` everywhere today (already implemented in `timeutil`).
- Root cause: Spec/glossary vs ING-110 wording; resolution proposed in SG-14, ADR pending at T3.04 + LIMITATIONS note.

**Latent ENTSO-E client/contract mismatch (pre-bug):**
- Symptoms: Raw XML / resolution / curveType fields needed for ING-009/060 may be unavailable if `PandasClient` is used for persistence.
- Trigger: First live M1 ingest against real API (RB-9 / SG-01).
- Files: `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` (SG-01), planned `src/epra/ingest/entsoe.py`
- Workaround: Spike with `EntsoeRawClient` + own Appendix-A parser (proposed); fallback to raw REST via `requests` with ADR.
- Root cause: ING-009 raw-cache mandate vs ING-022 `entsoe-py` PandasClient behavior.

## Security Considerations

**ENTSO-E API token (sole secret):**
- Risk: Token printed, committed, logged, or embedded in cache URLs → credential compromise (A-7); requires human rotation.
- Files: `src/epra/common/config.py` (`entsoe_token`), `.env` (present locally, gitignored), `.env.example`, `scripts/check_no_token_in_code.py`, `.pre-commit-config.yaml` (`no-entsoe-token-in-code`, `detect-private-key`)
- Current mitigation: Env-only load with fail-fast; `.gitignore` lists `.env`; pre-commit regex flags `securityToken=` literals; tests in `tests/unit/test_scripts.py` / `test_config.py`.
- Recommendations: Keep guard in every ingest PR; never log request URLs that embed the token; on first leak STOP and rotate; when GitHub exists store only as Actions secret (EN-041). Do not weaken or bypass `check_no_token_in_code.py`.

**Token-guard pattern coverage is narrow:**
- Risk: Leak via `Authorization:` headers, query params named differently, or plaintext in fixtures may evade `securityToken=` regex.
- Files: `scripts/check_no_token_in_code.py` (`_TOKEN_LITERAL`)
- Current mitigation: Detects the ENTSO-E URL query form; private-key hook covers PEM-style keys.
- Recommendations: When M1 builds `_fetch`, assert token never appears in logged strings; extend guard if a second literal pattern appears in code/fixtures.

**Untracked agent tooling trees:**
- Risk: Accidental commit of `.cursor/` / `.claude/` (large scaffolding) bloats the repo; unlikely secret leak but noisy and may confuse reviews.
- Files: `.cursor/`, `.claude/` (untracked per `git status`)
- Current mitigation: Not in git history yet.
- Recommendations: Keep out of milestone PRs (A-5); add to `.gitignore` if they remain local-only, or vendor deliberately under ADR if the project intends to ship them.

## Performance Bottlenecks

**Forward block-bootstrap (not implemented; budget-bound):**
- Problem: ST-406 N=2000 paths over coupled monthly price+ÖSPI draws is the heaviest stochastic step.
- Files: stub `src/epra/strategies/forward_risk.py`; budgets in `docs/EXECUTION_BLUEPRINT/07_QUALITY_STANDARDS.md` §7.2
- Measurement: Budget `< 10 min` (ST-406); full `make all` `< 30 min` (EN-050). No measured run yet (stub).
- Cause: Path count × month resampling; naive Python loops will blow the budget.
- Improvement path: Implement vectorized design required by ST-406 / AGENTS M6 note; measure before any extra caching (AP-21).

**ENTSO-E backfill volume after SDAC 15-min MTU:**
- Problem: Mixed PT60M/PT15M responses inflate download time, cache size, and parse memory (R-2, RB-15).
- Files: planned `src/epra/ingest/entsoe.py`, `config/settings.yaml` (`ingest.chunk_days: 90`)
- Measurement: Backfill budget **[BP]** `< 90 min` incl. politeness sleeps; peak memory **[BP]** `< 4 GB`.
- Cause: 4× row density post-SDAC; quarter-sized frames may spike RAM.
- Improvement path: Month-partitioned parquet (ING-003); per-month frames if budgets fail; ADR before raising budgets (RB-15).

**HMM regime fitting nondeterminism / platform drift:**
- Problem: A3 regimes may disagree across CI vs local BLAS (RB-11), breaking AN-705 / A-4.
- Files: stub `src/epra/analytics/regimes.py`; risk `docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md` RB-11
- Measurement: None yet; gate is identical SSOT inputs on two consecutive `make analyze` runs (AN-705).
- Cause: `hmmlearn` + numeric libs; unseeded or unstable restarts.
- Improvement path: Seeded restarts 42..51, deterministic tie-break (guide §5.5); if unstable, ADR to commit regime parquet from one canonical platform.

## Fragile Areas

**Timezone / DST doctrine (`timeutil` + future `dim_calendar`):**
- Why fragile: Analytic vs storage TZ split; DST days have 23/25 local hours; wrong conversion silently shifts annual means (T-1).
- Files: `src/epra/common/timeutil.py`, future `src/epra/ingest/calendar.py`, dbt `dim_calendar` (M3)
- Common failures: Naive datetimes; subtracting same-tzinfo datetimes on DST days; aggregating without local-hour attributes from calendar.
- Safe modification: Only convert via `to_utc` / `to_local`; use `local_hours_in_day` for DST counts; never ad-hoc `.tz_localize` outside this module (AP-05).
- Test coverage: `tests/unit/test_timeutil.py` covers peak + DST hour counts; ingest DST fixtures not yet present (M1 EN-070).

**15-min → hourly aggregation (prices mean, load mean):**
- Why fragile: Agents commonly sum instead of mean (T-2); mixed resolutions in one month (R-2).
- Files: planned staging models under `dbt/models/staging/`, `src/epra/ingest/entsoe.py`
- Common failures: Gate failures on annual means; unit errors after SDAC switch.
- Safe modification: Follow ING-062 fixture + SPEC-01 §6; never invent fills outside ING-063 (AP-01).
- Test coverage: Fixture/tests not landed (M1); only stub raise tests today.

**ÖSPI → EUR/MWh calibration:**
- Why fragile: Index base ≠ EUR/MWh; multiplying index by volume yields ~10× absurd S3 costs (T-5).
- Files: stub `src/epra/strategies/calibration.py`, future LIMITATIONS §2
- Common failures: ST-602 sanity relation (a) fails; strategy ranking nonsense.
- Safe modification: Always translate through P_ref anchors (ST-201…204); debug calibration before other M6 work if ST-602 fails.
- Test coverage: None yet (M6).

**Forward bootstrap joint draws:**
- Why fragile: Independent draws of prices vs ÖSPI destroy spot/contract correlation (T-6, AP-09).
- Files: stub `src/epra/strategies/forward_risk.py`
- Common failures: Forward risk distributions that look “reasonable” but invalidate strategy comparison.
- Safe modification: Draw month once; take both series (ST-401 step 2); pin seed 42 / Generator plumbing (AP-16).
- Test coverage: None yet; ST-405 determinism gate lands with M6.

**Config load caches (`functools.cache`):**
- Why fragile: `load_settings` / `load_consumer_profile` / `load_strategy_config` cache by path argument; mid-process YAML edits are invisible until process restart / `cache_clear`.
- Files: `src/epra/common/config.py`
- Common failures: Tests or notebooks that mutate YAML then reload without clearing cache see stale models.
- Safe modification: Prefer passing validated models as arguments (AP-06); in tests use distinct temp paths or call `.cache_clear()` on the loaders.
- Test coverage: `tests/unit/test_config.py` uses default paths; no explicit cache-invalidation test.

**Peak-hour single source of truth:**
- Why fragile: SG-14 peak definition split; duplicate peak logic outside `timeutil` will drift (AP-14).
- Files: `src/epra/common/timeutil.py` (`PEAK_START_HOUR`, `PEAK_END_HOUR`, `is_peak_hour`)
- Common failures: Holiday hours counted as peak in one mart and not another; anchors disagree with ÖSPI convention.
- Safe modification: Import `is_peak_hour` only; document ÖSPI convention difference in LIMITATIONS when M6 fills §2.
- Test coverage: Unit tests for `is_peak_hour`; no end-to-end mart peak test until M3.

**Windows native shell vs Makefile:**
- Why fragile: Makefile uses Unix `$(UV)` / `@echo` recipes; comment says Git Bash / WSL (or invoke `uv run` directly).
- Files: `Makefile`
- Common failures: `make` missing or recipe failures under PowerShell-only environments.
- Safe modification: Document/use Git Bash or WSL for Make targets; CI is Ubuntu (arbiter per RB-14).
- Test coverage: CI on `ubuntu-latest` only.

## Scaling Limits

**Local DuckDB analytics pipeline (not a multi-tenant service):**
- Current capacity: Single laptop / CI runner; hourly frames ~60k rows × few columns expected to stay well under 4 GB (`07_QUALITY_STANDARDS.md` §7.2).
- Limit: Breaks when algorithms load multi-year 15-min frames into one DataFrame or bootstrap loops are non-vectorized (RB-15 / ST-406 budgets).
- Symptoms at limit: Backfill > ~90 min; bootstrap > 10 min; OOM / thrashing near 4 GB.
- Scaling path: Partition by month; vectorize bootstrap; do not add distributed compute (O-4 / AP-21) — measure then ADR if budgets must change.

**External API rate / completeness:**
- Current capacity: Politeness sleeps `entsoe_sleep_s: 0.5`, `geosphere_sleep_s: 0.2` in `config/settings.yaml`; 90-day chunk max (ING-030).
- Limit: ENTSO-E throttling or A03 omitted points (R-3); ÖSPI publication lag (RB-16).
- Symptoms at limit: Retries exhaust; incomplete months; refresh PR with suppressed strategy outputs.
- Scaling path: Cache raw responses (ING-009); incremental 45-day lookback (ING-041); suppress missing ÖSPI month without extrapolation (RB-16).

## Dependencies at Risk

**entsoe-py:**
- Risk: PandasClient hides raw HTTP/XML fields required by ING-009/060; RawClient behavior may differ from assumptions (SG-01, RB-9). Untyped — mypy `ignore_missing_imports` for `entsoe.*` (`pyproject.toml`, ADR-002).
- Impact: M1 ingest/parser redesign mid-milestone; wrong resolution aggregation.
- Migration plan: Treat library as transport only; own parser owns contracts; sanctioned fallback to Appendix-A REST via `requests` + ADR.

**hmmlearn / arch / statsmodels:**
- Risk: Untyped; HMM nondeterminism across platforms (RB-11); easy to “improve” formulas against SPEC-04 (AP-11, T-3 arithmetic diffs not logs).
- Impact: AN-705 / A-4 failures; invalid scientific claims.
- Migration plan: Pin versions via ADR (GV-203); seed + tie-break; never swap methods without ADR.

**holidays (Styria subdiv):**
- Risk: Subdivision code `"6"` may rename (SG-10).
- Impact: Wrong holiday flags → wrong peak hours and load profile.
- Migration plan: Assert `subdiv="6"` at T2.01; ADR only on deviation.

**pandas-stubs / types-* (dev):**
- Risk: Stub packages lag runtime pandas/PyYAML (ADR-002 consequences).
- Impact: CI mypy noise or false confidence.
- Migration plan: Pin stub versions; never loosen `mypy --strict` to silence stub drift.

## Missing Critical Features

**End-to-end procurement answer (Q1–Q4):**
- Problem: No ingested prices, no marts, no retrospective costs, no forward P95/CVaR, no SSOT, no EXEC_SUMMARY / Power BI.
- Current workaround: Specs + blueprint + M0 foundation; README states answer lands at M6/M7.
- Blocks: Charter DL-1…DL-10; hiring-manager-facing euro answer.
- Implementation complexity: Full M1→M7 critical path (`docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md`); portfolio risk is stalling before M6/M7 (`12_RISK_REGISTER.md` closing statement).

**CI jobs 3–4 (dbt + SSOT consistency):**
- Problem: Only lint + test jobs live; dbt-check and ssot-check commented out.
- Files: `.github/workflows/ci.yml`
- Current workaround: Local `make lint` / `make test` only.
- Blocks: EN-080 complete gate set; GV-303 number integrity in CI.
- Implementation complexity: Medium — land with M3 and M6 respectively.

**Human-owned Power BI deliverable:**
- Problem: `.pbix` and dashboard screenshots are human tasks (AGENTS.md §2.5); agents prepare `exports/` + `dashboards/README.md` only.
- Current workaround: None until M7 handoff.
- Blocks: DL-6.
- Implementation complexity: Human build after `make export`; agent docs per SPEC-06 §4.

**ENTSO-E token acquisition (external blocker):**
- Problem: Live M1 backfill blocked until human obtains token (R-1); BUILD_LOG notes ETA ~2026-07-22 for TP.01.
- Current workaround: Proceed with M2 (no auth) and M3-on-fixtures in parallel.
- Blocks: Real-data gates ING-080…085; DL-1 with live data.
- Implementation complexity: Process/external — not code.

## Test Coverage Gaps

**Ingest contract / fixture suite (M1):**
- What's not tested: 15-min aggregation fixture (ING-062), DST ingest fixtures, A03 fill accounting, live-marker exclusion end-to-end against real API.
- Files: planned under `tests/`; stubs only in `tests/unit/test_stubs_fail_loudly.py`
- Risk: Silent unit/resolution errors once backfill runs (R-2, R-3).
- Priority: High
- Difficulty to test: Fixtures are specified; need ENTSO-E sample XML/parquet — no network in CI (`-m "not live"`).

**dbt model + schema-contract tests (M3):**
- What's not tested: Staging MEAN aggregation, DM-020 dedup warn counts, mart schema byte-match to contract YAML, DST 23/25 hour tests.
- Files: `dbt/tests/.gitkeep`, empty model dirs
- Risk: Warehouse silently diverges from SPEC-02 §5.
- Priority: High
- Difficulty to test: Needs fixture-bootstrap mini-warehouse (EN-080 job 3).

**Consumer profile goldens / properties (M4):**
- What's not tested: LP-040…042 annual sum 50,000.00 MWh, checksum stability, peak-share SSOT publication (SG-03).
- Files: stub `src/epra/consumer/profile.py`
- Risk: Wrong load shape quietly skews all strategy euros.
- Priority: High
- Difficulty to test: Deterministic given config — golden generation needs human approval path (EN-072).

**Analytics gates AN-701…705 / AN-304 (M5):**
- What's not tested: Crisis-regime sanity, deterministic analyze twice, weather HDD/CDD.
- Files: stubs under `src/epra/analytics/`
- Risk: Plausibility failures or nondeterministic SSOT inputs.
- Priority: Medium–High
- Difficulty to test: Needs warehouse marts; HMM stability may need platform pinning (RB-11).

**Strategy ST-601…604 / SSOT consistency (M6):**
- What's not tested: Calibration anchors, ST-602 relations, seed-reproducible forward metrics, GV-303 README↔SSOT checker.
- Files: strategy stubs; `scripts/generate_ssot.py`, `scripts/check_ssot_consistency.py` exit not-implemented
- Risk: Wrong headline euros published; golden laundering (AP-20 / RB-13).
- Priority: High
- Difficulty to test: Requires full upstream data + human golden approval.

**Integration / `make all` reproducibility:**
- What's not tested: Two consecutive full pipeline runs → identical SSOT (A-4).
- Risk: Nondeterminism discovered only at M6/M7.
- Priority: Medium (enforced late, designed early)
- Difficulty to test: Heavy; rely on per-module determinism tests until refresh cron exists.

---

*Concerns audit: 2026-07-20*
*Update as issues are fixed or new ones discovered*
