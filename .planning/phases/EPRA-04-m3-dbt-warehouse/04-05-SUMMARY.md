---
phase: EPRA-04-m3-dbt-warehouse
plan: 05
subsystem: database
tags: [dbt, dbt-duckdb, duckdb, sql, python, numpy, pytest]

# Dependency graph
requires:
  - phase: EPRA-04-m3-dbt-warehouse plan 03
    provides: dbt/seeds/dim_strategy.csv (validated DM-060 FK target for DM-063)
provides:
  - scripts/bootstrap_fixture_warehouse.py — D-04 deterministic synth of data/raw (2022-2024) + data/manual/oespi_monthly.csv + data/processed stand-ins, --force guard, --processed-only safe local mode
  - tests/unit/test_bootstrap_fixture_warehouse.py — determinism, guard, window/DST/crisis-month coverage tests (network-free)
  - dbt/models/marts/fct_consumer_load_hourly.sql — thin loader over the consumer-load stand-in (SPEC-02 §5, SG-06)
  - dbt/models/marts/fct_procurement_cost_monthly.sql — thin loader over the procurement-cost stand-in (SPEC-02 §5, DM-063)
  - dbt/models/marts/facts_future.yml — DM-060 keys + DM-063 relationship for the two future marts
  - docs/ADR/ADR-010_ci-fixture-standin-policy.md — SG-06 synthesis + environment-aligned stand-in policy
affects: [EPRA-04-m3-dbt-warehouse plan 06 (M3 exit-gate schema contract diff-checks these 2 marts alongside 04-04's four); EPRA-04-m3-dbt-warehouse plans 07-08 (CI dbt-check job wiring uses this generator); future M4/M6 phases (real module outputs replace these stand-ins with zero mart-code change)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A single numpy.random.default_rng seeded from one module-level constant drives every synthetic draw, so two same-window runs are data-identical byte-for-byte except the wall-clock ingested_at_utc provenance column (the same seam _io.write_month's own idempotency tests already document)"
    - "Every synthetic parquet write reuses epra.ingest._io.write_month by constructing a Settings.model_copy with paths.data_raw redirected to the target root (raw or processed) — no second hand-rolled parquet-writing path, consistent project-wide convention"
    - "Two distinct, separately-guarded CLI modes on one script: default/--force (full CI rebuild, refuses to clobber populated data/raw or data/manual/oespi_monthly.csv without --force) vs. --processed-only (writes only data/processed, aligned to the real local window discovered from calendar.parquet, never touches data/raw/data/manual — always safe locally)"

key-files:
  created:
    - scripts/bootstrap_fixture_warehouse.py
    - tests/unit/test_bootstrap_fixture_warehouse.py
    - dbt/models/marts/fct_consumer_load_hourly.sql
    - dbt/models/marts/fct_procurement_cost_monthly.sql
    - dbt/models/marts/facts_future.yml
    - docs/ADR/ADR-010_ci-fixture-standin-policy.md
  modified: []

key-decisions:
  - "D-04/ADR-010: the generator synthesizes every raw/processed row programmatically (seeded numpy RNG) — it never copies a committed fixture parquet, since a capped ~200-row sample cannot satisfy the M3 exit gate's DM-062 row-count or DM-065 DST tests over a full contiguous multi-year window."
  - "D-06/ADR-010: added a --processed-only CLI mode (not in the plan's literal text) that writes only data/processed, discovering the real local ingestion window from data/raw/calendar/calendar.parquet, and never touches data/raw or data/manual. This is the mode used to verify Task 3 in THIS repository, since data/raw and data/manual/oespi_monthly.csv already hold real 2019-2024 ingested data that must never be overwritten by synthetic rows — confirmed via `git diff --stat data/raw data/manual/oespi_monthly.csv` returning empty both before and after running the generator."
  - "The --force guard also covers data/manual/oespi_monthly.csv (not just data/raw as the plan's literal text states) — both hold irreplaceable real ingested data per the execution context's CRITICAL SAFETY directive, so the guard is symmetric across both roots."
  - "fct_procurement_cost_monthly's underlying data/processed parquet carries an extra helper `date` column (first-of-month) purely so the frame can be validated/written through write_month's key_column='date' path — the mart itself selects only its own SPEC-02 §5 columns, so the extra column is invisible downstream."
  - "Calendar/geosphere/price/load/gen synthesis is self-contained (Austria holidays + epra.common.timeutil.is_peak_hour + a Vienna-local hourly walk converted to UTC) rather than reusing epra.ingest.calendar.build_calendar or epra.ingest.entsoe.latest_complete_month, since both of those read real ingested data that does not exist on a fresh CI checkout (avoids a chicken-and-egg dependency)."

patterns-established:
  - "CLI scripts needing both a 'fresh/CI' and a 'safe against real local data' mode expose the safe mode as an explicit, separately-named flag (--processed-only) rather than overloading --force semantics — --force always means 'I explicitly accept overwriting real data'."

requirements-completed: [REQ-DWH-01, DM-050, DM-063, SG-06]

coverage:
  - id: D1
    description: "bootstrap_fixture_warehouse.py synthesizes a contiguous, seeded 2022-2024 data/raw window (all 4 ENTSO-E datasets + geosphere + calendar) plus data/manual/oespi_monthly.csv and data/processed stand-ins, refuses to overwrite populated data/raw or data/manual without --force, and never copies committed fixture parquet"
    requirement: "SG-06"
    verification:
      - kind: unit
        ref: "tests/unit/test_bootstrap_fixture_warehouse.py::test_force_guard_refuses_populated_raw_without_force, ::test_force_guard_refuses_populated_manual_oespi_without_force, ::test_force_guard_proceeds_with_force"
        status: pass
      - kind: other
        ref: "grep confirms the script imports epra.ingest._io.write_month and contains no shutil.copy/file-copy of tests/fixtures or data/ parquet; a module-level _SEED constant seeds numpy.random.default_rng"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two same-seed runs of the generator produce identical data columns for every written dataset (raw + processed + calendar + oespi CSV), excluding only the wall-clock ingested_at_utc provenance column"
    requirement: "DM-050"
    verification:
      - kind: unit
        ref: "tests/unit/test_bootstrap_fixture_warehouse.py::test_determinism_same_seed_identical_data_across_two_runs"
        status: pass
    human_judgment: false
  - id: D3
    description: "The default 2022-2024 window is contiguous (1096 unique local dates), includes both 2024 DST transition days with correct 23/25 local-hour counts, includes the 2022-08 crisis month, respects DM-061 accepted ranges, and procurement_cost_monthly covers all 6 dim_strategy strategy_ids x 36 gap-free months"
    requirement: "DM-050"
    verification:
      - kind: unit
        ref: "tests/unit/test_bootstrap_fixture_warehouse.py::test_default_window_covers_2022_2024_with_dst_days_and_crisis_month, ::test_processed_only_discovers_real_local_window_from_calendar"
        status: pass
    human_judgment: false
  - id: D4
    description: "fct_consumer_load_hourly and fct_procurement_cost_monthly build green as thin, never-disabled loaders over the data/processed stand-ins, with DM-060 unique/not_null and the DM-063 relationships test (strategy_id -> dim_strategy) passing; full-project dbt build has no regression"
    requirement: "DM-063"
    verification:
      - kind: other
        ref: "python scripts/bootstrap_fixture_warehouse.py --processed-only (writes data/processed only, git diff --stat data/raw data/manual/oespi_monthly.csv empty before and after); cd dbt && dbt build --select fct_consumer_load_hourly fct_procurement_cost_monthly (9/9 PASS: 2 models + 7 tests); full dbt build re-run: 59 PASS / 1 pre-existing non-blocking WARN (predup_count_prices, 04-02, unrelated) / 0 ERROR"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-07-24
status: complete
---

# Phase EPRA-04 Plan 05: Fixture/Stand-in Generator + Future Marts (D-04, SG-06) Summary

**A deterministic, seeded fixture generator (`bootstrap_fixture_warehouse.py`) that synthesizes the CI 2022-2024 raw window and local `data/processed` stand-ins without ever copying committed parquet, plus the two never-disabled future marts (`fct_consumer_load_hourly`, `fct_procurement_cost_monthly`) it feeds — verified safe against this repository's real 2019-2024 ingested data via a dedicated `--processed-only` mode**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-24T09:20Z
- **Tasks:** 3/3
- **Files modified:** 6 (all created)

## Accomplishments
- `scripts/bootstrap_fixture_warehouse.py` synthesizes, from a single seeded `numpy.random.default_rng`, a contiguous Vienna-local-DST-correct hourly window (default 2022-01-01..2024-12-31 — 1096 unique local dates) into `entsoe_prices_at`/`entsoe_prices_delu`/`entsoe_load_at`/`entsoe_gen_at` (long-format, `kind='aggregated'` only), `geosphere_graz_daily`, the ING-110 `calendar.parquet` spine, `data/manual/oespi_monthly.csv`, and the two `data/processed` stand-ins (`consumer_load_hourly`, `procurement_cost_monthly` — every month x all 6 `dim_strategy` strategy_ids) — every value crafted inside DM-061's accepted ranges, with the 2022-08 crisis month and both 2024 DST transition days (23/25 local hours) verifiably present
- Every write goes through `epra.ingest._io.write_month`'s atomic `.tmp` + `os.replace` path (by redirecting a `Settings.model_copy` of `paths.data_raw`) — zero hand-rolled parquet writers, zero copying of committed fixture parquet (D-04)
- The `--force` guard refuses to touch an already-populated `data/raw` or an existing `data/manual/oespi_monthly.csv` without explicit override (both proven real-irreplaceable-data-safe in unit tests); a `--processed-only` mode (added beyond the plan's literal text, D-06) writes *only* `data/processed`, discovering the real local ingestion window from the committed `calendar.parquet` spine, and **never** touches `data/raw`/`data/manual` — this is the mode used to safely verify Task 3 against this repository's real 2019-2024 ingested data
- Determinism proven: two independent same-seed runs produce byte-for-byte identical data columns across every dataset (raw + processed + calendar + the OESPI CSV), excluding only the wall-clock `ingested_at_utc` provenance column
- `fct_consumer_load_hourly` (`ts_utc, load_mwh`) and `fct_procurement_cost_monthly` (`year_local, month_local, strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh`) are plain, never-disabled `select` loaders over `source('raw_processed', ...)` (SG-06); `facts_future.yml` pins DM-060 unique/not_null on both grain keys and the DM-063 `relationships` test (`strategy_id` -> `dim_strategy.strategy_id`), nested under dbt 1.12's `arguments:` property (04-04 convention)
- Verified against this repo's real warehouse: `python scripts/bootstrap_fixture_warehouse.py --processed-only` populated `data/processed/**` only (confirmed via empty `git diff --stat` on `data/raw`/`data/manual/oespi_monthly.csv` before and after), then `dbt build --select fct_consumer_load_hourly fct_procurement_cost_monthly` passed 9/9 (2 models + 7 generic tests); full-project `dbt build` re-run: 59 PASS / 1 pre-existing non-blocking WARN (`predup_count_prices`, 04-02, unrelated) / 0 ERROR — no regression to any prior plan's models
- `ADR-010` records the D-04 synthesis-not-copy deviation from the WBS T3.06 wording and the D-06 dual-mode (`--force` full rebuild vs. `--processed-only` safe local) stand-in policy

## Task Commits

Each task was committed atomically:

1. **Task 1: bootstrap_fixture_warehouse.py — deterministic synth + --force guard** - `5dfe072` (feat)
2. **Task 2: test_bootstrap_fixture_warehouse.py — determinism, guard, window coverage** - `a08587d` (test)
3. **Task 3: fct_consumer_load_hourly + fct_procurement_cost_monthly + facts_future.yml + ADR-010** - `f4b07c6` (feat)

## Files Created/Modified
- `scripts/bootstrap_fixture_warehouse.py` - deterministic D-04 synth of raw/manual/processed, `--force`/`--processed-only`/`--data-root`/`--window-start`/`--window-end` CLI
- `tests/unit/test_bootstrap_fixture_warehouse.py` - 8 network-free tests: guard (raw + manual), `--force` override, `--processed-only` isolation, determinism, default-window DST/crisis-month coverage, real-window discovery
- `dbt/models/marts/fct_consumer_load_hourly.sql` - thin loader over the consumer-load stand-in
- `dbt/models/marts/fct_procurement_cost_monthly.sql` - thin loader over the procurement-cost stand-in
- `dbt/models/marts/facts_future.yml` - DM-060 keys + DM-063 relationship for the two future marts
- `docs/ADR/ADR-010_ci-fixture-standin-policy.md` - D-04/D-06 synthesis + dual-mode stand-in policy

## Decisions Made
- **D-04 (plan-anticipated deviation, recorded in ADR-010):** synthesize every row programmatically instead of copying a committed fixture parquet, per the plan's own explicit instruction — a capped fixture cannot satisfy the M3 exit gate's row-count/DST tests over a full multi-year window.
- **D-06 extension (Rule 2 — missing critical functionality, execution-context-mandated):** added an explicit `--processed-only` CLI mode not spelled out verbatim in the plan's task text, because the plan's literal Task 3 verify command (`bootstrap_fixture_warehouse.py --force && dbt build ...`) would, if run literally against this repository's real, already-populated `data/raw` (real 2019-2024 ENTSO-E/GeoSphere data), overwrite genuine irreplaceable ingested parquet with synthetic 2022-2024 rows — directly forbidden by this execution's CRITICAL SAFETY directive. `--processed-only` fulfills the plan's D-06 intent ("locally it fills only the empty data/processed stand-ins... aligned to the real 2019->latest window") as a first-class, always-safe mode, verified via empty `git diff --stat` on `data/raw`/`data/manual/oespi_monthly.csv` before and after the real-repo run.
- **Guard symmetry (Rule 2):** extended the `--force` guard to also cover `data/manual/oespi_monthly.csv`, not just `data/raw` as the plan's literal wording states — both hold real, irreplaceable ÖSPI/ENTSO-E data per this execution's CRITICAL SAFETY directive.
- Reused `epra.ingest._io.write_month` for every parquet write (raw and processed alike) by constructing a `Settings.model_copy` with `paths.data_raw` redirected to the target root — no second hand-rolled parquet writer, per the plan's explicit instruction and the codebase-wide convention.
- Self-contained calendar/holiday synthesis (Austria holidays + `timeutil.is_peak_hour` directly) rather than reusing `epra.ingest.calendar.build_calendar`/`entsoe.latest_complete_month`, since both read real ingested price data that does not exist on a fresh CI checkout — avoids a circular dependency the generator must not have.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pandas DeprecationWarning/UserWarning on DST-range construction and tz-aware-to-period conversion**
- **Found during:** Task 1 (initial smoke-test run of the generator)
- **Issue:** `pd.Timestamp(end) + pd.Timedelta(hours=23)` triggered a pandas 2.3.3 "generic unit" `DeprecationWarning` (same class already fixed in `epra.ingest.calendar`), and `frame["ts_utc"].dt.tz_convert("UTC").dt.to_period("M")` triggered a "drops timezone information" `UserWarning` on every monthly grouping call.
- **Fix:** Used stdlib `timedelta(hours=23)` instead of `pd.Timedelta`, and inserted an explicit `.dt.tz_localize(None)` before `.dt.to_period("M")` (the tz drop is intentional there — only the calendar-month bucket is needed).
- **Files modified:** `scripts/bootstrap_fixture_warehouse.py`
- **Verification:** Re-ran the generator; zero warnings in output.
- **Committed in:** `5dfe072` (Task 1 commit)

**2. [Rule 3 - Blocking] mypy --strict rejected pandas-stubs' incomplete `date_range` overload for the `nonexistent`/`ambiguous` DST kwargs**
- **Found during:** Task 1 (`uv run mypy scripts/bootstrap_fixture_warehouse.py`)
- **Issue:** pandas-stubs' `date_range` overloads don't type the `nonexistent`/`ambiguous` keyword arguments, even though they exist and work correctly at runtime (verified against real 2024-03-31/2024-10-27 DST transitions).
- **Fix:** Added a single `# type: ignore[call-overload]` with an explanatory comment on that one call.
- **Files modified:** `scripts/bootstrap_fixture_warehouse.py`
- **Verification:** `uv run mypy scripts/bootstrap_fixture_warehouse.py` — Success, no issues.
- **Committed in:** `5dfe072` (Task 1 commit)

**3. [Rule 2 / D-06 extension — see "Decisions Made" above] Added `--processed-only` CLI mode not in the plan's literal text**
- **Found during:** Task 1 design, confirmed necessary at Task 3 verification
- **Issue:** the plan's literal Task 3 verify command uses `--force`, which per this generator's designed behavior would overwrite this repository's real `data/raw` (real 2019-2024 ENTSO-E/GeoSphere ingest) with synthetic 2022-2024 data — forbidden by the execution context's CRITICAL SAFETY directive.
- **Fix:** Added a dedicated `--processed-only` flag that never touches `data/raw`/`data/manual`, fulfilling D-06's "locally it fills only the empty data/processed stand-ins" intent as a safe, explicit mode; used it for all local/real-repo verification in this plan.
- **Files modified:** `scripts/bootstrap_fixture_warehouse.py`, `tests/unit/test_bootstrap_fixture_warehouse.py` (covering tests added)
- **Verification:** `git diff --stat data/raw data/manual/oespi_monthly.csv` returns empty both before and after running `--processed-only` against the real repo; `dbt build --select fct_consumer_load_hourly fct_procurement_cost_monthly` then passes 9/9 against the resulting real `data/processed` files.
- **Committed in:** `5dfe072` (script), `a08587d` (tests)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 safety-driven design addition)
**Impact on plan:** All three keep this plan's real deliverables (generator behavior, both future marts, ADR-010) exactly as specified while adding the safety margin the execution context explicitly mandated. No scope creep beyond that margin.

## Issues Encountered
None beyond the auto-fixed items above.

## User Setup Required

None — the generator is fully self-contained (no network, no credentials); `data/processed` is git-ignored (`data/processed/*` in `.gitignore`), so the synthetic stand-in files this plan produced locally are correctly untracked and will not be committed.

## Next Phase Readiness

`fct_consumer_load_hourly` and `fct_procurement_cost_monthly` are built, tested, and documented — the remaining two of the six marts the M3 exit-gate schema contract (04-06) will diff-check (alongside 04-04's four price/generation marts). `ADR-010` is ready for 04-06's documentation-completeness checks. `scripts/bootstrap_fixture_warehouse.py` is also ready for the CI `dbt-check` job wiring anticipated in later 04-05/04-07/04-08 plans (run with no flags / `--force` against an empty checkout). No blockers for 04-06. This repository's real `data/raw`/`data/manual` remain byte-for-byte untouched throughout (confirmed via `git diff --stat`); `data/processed/**` now holds this plan's stand-in files, correctly git-ignored.

---
*Phase: EPRA-04-m3-dbt-warehouse*
*Completed: 2026-07-24*

## Self-Check: PASSED

All 6 created files found on disk; all 3 commit hashes (`5dfe072`, `a08587d`, `f4b07c6`) found in git log.
