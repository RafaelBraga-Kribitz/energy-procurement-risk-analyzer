# Phase 5: M4 Consumer Profile - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning
**Mode:** Interactive discuss — spec-supremacy project. `docs/SPEC-03_consumer_load_profile.md` (LP-xxx) locks *what* to build (algorithm steps 1–5, YAML parameters, golden/property tests, outputs). WBS §M4 (T4.01–T4.05) locks the task shape. This discussion captures the **operational / HOW decisions the spec leaves open** — calendar input source, SG-03/SG-04 ADR adoptions, `flat_baseload` config switch, golden checksum persistence, SSOT-input path, and how the real parquet replaces the M3 consumer stand-in.

<domain>
## Phase Boundary

Build the deterministic, CALIBRATED StyriaMetal hourly load profile (REQ-LP-01). One milestone.

- **Module:** `src/epra/consumer/profile.py` — replace `NotImplementedError` stubs with SPEC-03 §2 exactly (steps 1–5 in order). Public API already pinned in `docs/EXECUTION_BLUEPRINT/03_MODULES.md`: `day_type`, `special_factor`, `hourly_weights`, `normalize_by_local_year`, `build_profile`, `monthly_volumes`.
- **Config:** `config/consumer_profile.yaml` is already committed verbatim (SPEC-03 §6). All numerics come from `load_consumer_profile()` (LP-002). Zero randomness (LP-001).
- **Outputs:** `data/processed/consumer_load_hourly.parquet` (`ts_utc`, `load_mwh`, LP-003); `data/processed/consumer_load_monthly.parquet` (`year_local`, `month_local`, `volume_mwh`, LP-021); `consumer_peak_share` as a typed SSOT-input row (LP-020, CALIBRATED).
- **Variant:** `flat_baseload` via the same function (LP-030).
- **Tests:** LP-040 golden (2023 slice + sha256), LP-041 property, LP-042 checksum meta-test, LP-034 partial-year fixture, T4.01 rule tests, SG-03 yearly peak-share deviation < 1 pp.
- **Honesty:** LIMITATIONS.md §1 already contains the LP-051 sentence; this phase confirms it. LP-050 captions belong on later artifacts (M5/M7), not invented here.

**Exit gate (SC):** (1) LP-040..042 green with persisted 2023 checksum; (2) each full local year sums to 50,000.00 MWh ± 0.01; (3) `consumer_peak_share` computed and ready for SSOT inputs.

**Out of this phase:**
- Analytics A1–A4 (M5), strategy simulator / `generate_ssot.py` concatenation (M6), exports/README/EXEC_SUMMARY (M7).
- LP-050 caption stamping on charts/tables that do not yet exist.
- Replacing the *procurement-cost* stand-in (still M6).
- TP.02 GitHub required-check flip (operator; still open from M3).
- Anything in Charter §4.2.

</domain>

<decisions>
## Implementation Decisions

### Calendar input (Area A — LP-001, ING-110 vs dim_calendar)
- **D-01:** The weight engine reads the **ING-110 calendar DataFrame** — the same columns as `data/raw/calendar/calendar.parquet` / `epra.ingest.calendar.build_calendar()`: `ts_utc, date_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour, year_local, month_local`. Tests call `build_calendar(settings, end=…)` (already the M2 fixture pattern) rather than requiring a warehouse. The engine does **not** query DuckDB `dim_calendar` (that mart adds weather/season/degree-days unused by SPEC-03) and does **not** use GeoSphere temperature. `build_profile(calendar_df, cfg)` stays a pure function of those two arguments.

### Special-window rules (Area B — SG-04, §3.3)
- **D-02:** Adopt **SG-04 via ADR-012** (confirm next-free number at planning time; currently ADR-012 is free): first Monday `m` with `m ≥ Aug 1`; maintenance window = `[m, m+6]` inclusive. If 1 August is a Monday → 1–7 August. Mandatory test year: **2022** (1 Aug 2022 was Monday). Maintenance days **keep** weekday/weekend `day_type`; `special_factor = cfg.maintenance.factor`.
- **D-03:** Christmas shutdown is Dec 24 through Jan 1 inclusive, spanning the year boundary. Dec 24–31 belong to local year Y's normalization; Jan 1 belongs to Y+1 (LP §3.3 / guide 5.4). `day_type = shutdown`. Extra `shutdown_factor` is the identity **1.0** ("no double dampening") — a rule, not a YAML knob. Do **not** add `shutdown_factor` to `config/consumer_profile.yaml` (SPEC-03 §6 is frozen verbatim). Do **not** hardcode the grep-forbidden literals `0.18`, `0.60`, or `1.06` in `src/` (those come from YAML).

### Peak share → SSOT (Area C — SG-03, LP-020)
- **D-04:** Adopt **SG-03 via ADR-013**: compute peak share per local year (peak = `is_peak_hour` from the calendar, already holiday-aware per ADR-011); publish the **2019** value to SSOT as `consumer_peak_share` (CALIBRATED). Test: max absolute deviation across complete local years vs 2019 **< 1 percentage point**; if the test fails, STOP (do not silently pick another year). Plausibility: the published value ∈ [0.42, 0.48] (LP-020).
- **D-05:** SSOT-input path follows `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §5.6: `data/processed/ssot_inputs_profile.parquet` with columns `key, value, unit, tag, produced_by`. `generate_ssot.py` (M6) concatenates producer files; this phase only emits the profile producer file. `produced_by = "epra.consumer.profile"`; `tag = "CALIBRATED"`; `unit` is a dimensionless fraction (document as `1` or `fraction` consistently in the emitter — planner pins the string).

### flat_baseload (Area D — LP-030 vs 03_MODULES extension note)
- **D-06:** **SPEC-03 §5 wins** over the 03_MODULES "new YAML file" extension sentence: `flat_baseload` is the **same function** with `cfg.profile_name == "flat_baseload"` (or CLI `--profile flat_baseload` that copies the loaded YAML cfg and sets `profile_name`). All hourly weights = 1.0 before the same LP-004/LP-034 normalization. **No second YAML file.** Unknown `profile_name` → `ValueError`. Accepted names: `styriametal_v1`, `flat_baseload` only.

### Golden checksum (Area E — LP-040, EN-072)
- **D-07:** On first green LP-040 run, **commit** `tests/golden/consumer_load_2023.sha256` in the T4.04 implementing PR (not a CI first-write). Subsequent runs assert the digest. Regeneration requires human approval (EN-072 / AGENTS stop-list) — do not silently refresh the golden.

### Stand-in replacement & operator interface (Area F — SG-06, Makefile)
- **D-08:** Canonical hourly output is the SPEC-03 single file `data/processed/consumer_load_hourly.parquet` (and monthly sibling `consumer_load_monthly.parquet`). Update `dbt/models/sources.yml` `raw_processed.consumer_load_hourly` to `read_parquet('../data/processed/consumer_load_hourly.parquet')` so `fct_consumer_load_hourly` reads the real LP-003 file. Update `scripts/bootstrap_fixture_warehouse.py` to write that **same single-file path** for the CI/local stand-in (procurement stand-in stays monthly-partitioned). `make profile` writes the real profile parquet (idempotent; atomic replace). Reorder Makefile `all:` to **`profile` then `transform`** then the rest, so a full pipeline never feeds the stand-in into the warehouse after M4. `make profile` itself does **not** invoke dbt (keeps the ingest/validate two-step precedent: write data, then transform).
- **D-09:** LIMITATIONS.md §1 already states the LP-051 text. T4.05 confirms it; do not invent LP-050 captions on artifacts this milestone does not produce.

### ADR governance (Area G)
- **D-10:** Two **single-topic ADRs** (ADR-001..011 precedent). Confirm numbers against `docs/ADR/` at planning time:
  - **ADR-012** — SG-04 first-Monday-on-or-after-1-August maintenance week (T4.01).
  - **ADR-013** — SG-03 reference-year 2019 `consumer_peak_share` + <1 pp yearly-deviation test (T4.03).

### Claude's Discretion
- Internal decomposition inside the 03_MODULES pinned names; vectorized pandas/numpy (no Python-level per-hour loops); function length ~60 lines (W-3).
- CLI flag set beyond `--profile` (e.g. `--end` for tests, output path override) — implementer's choice provided defaults match SPEC-03 paths.
- Atomic parquet write (`.tmp` + `os.replace`) mirroring `_io.write_month` without routing processed files through the raw-only writer.
- How `flat_baseload` is constructed from cfg (model_copy vs a tiny helper) — as long as YAML numerics are unused for that variant's weights.
- Whether monthly volumes join calendar columns from `build_profile`'s index or re-attach `year_local`/`month_local` from the input calendar — grain must match LP-021.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Binding spec (authority)
- `docs/SPEC-03_consumer_load_profile.md` — whole file. §1 principles (LP-001..004), §2 algorithm (five steps, first-match day_type), §3 parameters / special windows, §4 derived facts (LP-020/021), §5 `flat_baseload` + LP-034, §6 YAML (already committed), §7 tests LP-040..042, §8 honesty LP-050/051.
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M4 — T4.01 weights, T4.02 normalize, T4.03 outputs, T4.04 goldens, T4.05 Makefile/PR.
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` — `epra.consumer.profile` internal API, failure modes, vectorization, accepted profile names.
- `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §5.4 — worked micro-examples, Christmas year-split, partial-year Σw over hypothetical full year; §5.6 SSOT producer parquet shape.
- `docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md` §6.7 M4 row + global lists for the M4 PR.
- `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` — **SG-03** (T4.03 ADR-013), **SG-04** (T4.01 ADR-012).

### Upstream already shipped (do not rebuild)
- `src/epra/ingest/calendar.py` + `tests/unit/test_calendar.py` — ING-110 spine; reuse `build_calendar(settings, end=fixed)` in tests.
- `src/epra/common/config.py` — `ConsumerProfileCfg`, `load_consumer_profile()`.
- `config/consumer_profile.yaml` — SPEC-03 §6 verbatim.
- `src/epra/common/timeutil.py` — peak-hour constants already encoded in the calendar's `is_peak_hour` column; do not re-derive peak in the profile module.
- `dbt/models/marts/fct_consumer_load_hourly.sql` — thin loader over `source('raw_processed', 'consumer_load_hourly')` (SG-06, never disabled).
- `LIMITATIONS.md` §1 — LP-051 placeholder already has the required sentence.

### Governance
- `docs/PROJECT_CHARTER.md` + `docs/ADR/ADR-001_light-governance-no-external-kit.md` — append-only single-topic ADRs.
- `docs/ADR/ADR-011_holiday-aware-peak.md` — `is_peak_hour` is the one internal peak definition (D-04 consumes it).
- EN-072 / AGENTS.md stop-list — golden regeneration needs human approval.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `profile.py` is a typed stub with the two public functions tests already import. `test_stubs_fail_loudly.py` rows for `build_profile` / `monthly_volumes` are deleted at T4.05 (or as soon as those functions no longer raise — delete in the same commit that un-stubs them).
- Calendar tests already build a 2019→2027 spine with `end=date(2027,12,31)` — enough for 2022 maintenance-edge, 2023 golden, 2019 peak-share, DST 2024, and LP-034 6-month windows.
- `Makefile` `profile:` is a loud-fail stub; `all:` currently runs `transform` *before* `profile` (M3 stand-in would still land in the warehouse). D-08 reorders this.
- `dbt/models/sources.yml` currently globs `../data/processed/consumer_load_hourly/**/*.parquet` (M3 monthly `write_month` stand-in layout). D-08 switches that glob to the SPEC-03 single file and updates the bootstrap writer to match.
- No `tests/golden/` directory yet.

### Established Patterns
- Spec-ID in public-function docstrings (`Implements: LP-xxx`) — W-2.
- TDD-lean: tests land in the same commit as the implementation (W-1).
- Live/real isolated from CI: this milestone is fully offline (calendar builder + YAML). No `@pytest.mark.live`.
- Atomic parquet via temp-file + `os.replace` (`_io.write_month`). Processed output must not use the raw-only writer; copy the atomic-replace *pattern*.
- ADRs use Context / Decision / Consequences / Spec deviations (ADR-006 template).
- Fixture calendar: `build_calendar(settings, end=…)` — never invent hours.

### Integration Points
- New: `src/epra/consumer/profile.py` (real body + CLI `python -m epra.consumer.profile`), `tests/unit/test_profile.py` (and golden file), `docs/ADR/ADR-012` + `ADR-013`, `data/processed/` writers, `ssot_inputs_profile.parquet` emitter.
- Modified: `Makefile` (`profile:` + `all:` order), `dbt/models/sources.yml`, `scripts/bootstrap_fixture_warehouse.py` (single-file consumer stand-in), `tests/unit/test_stubs_fail_loudly.py` (drop M4 rows), `docs/BUILD_LOG.md`, `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` (SG-03/SG-04 → adopted).
- Unchanged: `config/consumer_profile.yaml` (verbatim), `LIMITATIONS.md` §1 text (confirm only), procurement stand-in path.

</code_context>

<specifics>
## Specific Ideas

- **T4.01 rule tests (must include):** Dec 25 vs Dec 26 equality of *weights* (both shutdown); holiday Monday → weekend shape; 2022-08-01..07 maintenance with weekday/weekend shapes × `maintenance.factor`; a non-maintenance August day has factor 1.0; `grep -E '0\.18|0\.60|1\.06' src/` is empty after implementation.
- **Guide 5.4 intuition checks** (not a substitute for LP-040): weekday hour 14 in March ≈ `1.00 × 1.02 × 1.0`; Sunday 03:00 in July ≈ `0.30 × 0.95`.
- **Partial year (LP-034):** 6-month window fixture; monthly volumes match the corresponding months of a full-year run; Σw for the partial year uses the hypothetical full local year's weights (calendar rules extended beyond the profile window — tests may build a full-year calendar and slice, or extend internally; planner picks, but the *output* must only emit hours inside the requested calendar_df).
- **Checksum input:** sha256 of the 2023 `load_mwh` slice in a stable encoding (planner pins: sorted `ts_utc` + float64 little-endian bytes, or parquet-file digest of a canonical write). Must be bit-stable across two clean rebuilds.
- **`make all` order after D-08:** `profile transform analyze simulate ssot export report`.

</specifics>

<deferred>
## Deferred Ideas

- **LP-050 captions** on charts/tables/README — those artifacts are M5/M7; the verbatim sentence is already in LIMITATIONS.md §1.
- **SSOT markdown render** (`reports/NUMERIC_SSOT.md`, `generate_ssot.py`, GV-302/303) — M6 concatenates `ssot_inputs_*.parquet`.
- **Procurement-cost stand-in** replacement — M6.
- **Power BI / exports / refresh.yml** — M7.
- **TP.02** — operator GitHub setting (dbt-check required on `main`).
- **03_MODULES "new profile = new YAML file"** — not used for `flat_baseload`; remains a future-extension note if a *third* named shape is ever chartered (out of scope, Charter O-7 analog / A-3).

None outside these — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-M4 Consumer Profile*
*Context gathered: 2026-09-02*
