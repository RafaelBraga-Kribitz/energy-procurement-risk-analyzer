# Phase 7: M6 Strategy Simulator - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning
**Mode:** Interactive discuss — spec-supremacy project. `docs/SPEC-05_strategy_simulator.md` (ST-xxx) locks *what* to build (S1–S4 formulas, ST-201..204 anchors, retrospective matrix, exactly three sensitivities, seasonal block bootstrap, ST-601..604). WBS §M6 (T6.01–T6.10) locks order. This discussion captures the **operational / HOW decisions the spec leaves open** — shared NULL-price aligner, 2019 vs ADR-010 fixture, parquet path vs dbt glob, vectorized cells, HMM reuse, ST-502 captions, goldens vs A-2, SG-07/08/09 ADRs, SSOT `updated_at`, and `make simulate` vs dbt.

<domain>
## Phase Boundary

Build the procurement strategy simulator answering Charter Q1 and Q3, and emit `reports/NUMERIC_SSOT.md` (REQ-ST-01, REQ-Q1, REQ-Q3). One milestone. This is the heart of the portfolio — implement SPEC-05 **exactly**.

- **Modules:** `src/epra/strategies/{align,calibration,retrospective,forward_risk}.py` plus `epra.report.ssot` / `epra.report.ssot_check` (new; scripts are thin shells). Replace `NotImplementedError` stubs. Public pins in `docs/EXECUTION_BLUEPRINT/03_MODULES.md`: `Anchors`, `AlignedVolumes`, `cost_s1`, `p_s2`, `p_s3`, `build_cost_cells` → `CostCells`, `simulate`, `summarize`.
- **Config:** `config/strategies.yaml` is already verbatim SPEC-05 §8. All tunables from `load_strategy_config()` (ST-003). No magic numbers in code except spec-pinned seeds/methods adopted via ADR.
- **Strategy ids:** `dim_strategy` rows only — `S1`, `S2`, `S3`, `S4_30`, `S4_50`, `S4_70`. Dispatch table, not a class hierarchy (08_PATTERNS).
- **Inputs:** DuckDB **marts only** for prices/load/calendar/ÖSPI-in-warehouse; `w_peak` from `ssot_inputs_profile.parquet` (never retyped); no-crisis years from `epra.analytics.regimes.fit_hmm` + `december_regime` (M5 D-10, calm wins ties). Never `data/raw`.
- **Outputs:** `data/processed/strategy_costs_monthly.parquet` (ST-001) + dbt drop-in under `procurement_cost_monthly/` (D-05); `reports/strategies/*` (charts, unit-cost table, sensitivity matrix); `ssot_inputs_strategies.parquet`; `reports/NUMERIC_SSOT.md` via `make ssot`.
- **Order:** T6.01 align → T6.02 anchors → T6.03 S1 → T6.04 S2/S3/S4 → T6.05 annual/headline/charts → T6.06 sensitivities → T6.07 forward cells → T6.08 SSOT → T6.09 checker + CI job 4 → T6.10 goldens/determinism/BUILD_LOG.
- **Gates:** ST-601 (synthetic CI golden; real-euro replacement is human), ST-602 a/b/c fail-closed when coverage exists, ST-603 determinism + no-lookahead, ST-604 SSOT complete. Trap T-5 (ÖSPI is an index) and T-6 (draw prices+ÖSPI together) are load-bearing.
- **Honesty:** ST-502 caption on every S2/S3/S4 artifact. Do not invent 2019 prices, ÖSPI, or SSOT euros (A-2). If ST-602(a) fails on real data, **stop and debug calibration** — do not rationalize.

**Exit gate (SC):** (1) ST-601..604 green on the contracts this phase can honestly test; (2) two seeded runs → identical SSOT numeric values; (3) `NUMERIC_SSOT.md` contains the GV-302 key set with correct epistemic tags.

**Out of this phase:**
- README / EXEC_SUMMARY euro headlines (M7; A-6, SG-12). Checker must still pass on current docs (whitelist / no result numerals).
- Power BI `.pbix`, `refresh.yml`, exports CSVs, executive RP-201..204 charts (M7). `epra.report.charts.render_executive_charts` stays a loud M7 stub.
- Fifth strategy family, extra sensitivities, forecasting (Charter §4.2 / O-7).
- Extending the ADR-010 CI fixture to 2019 to green calibration or ST-602(a).
- Widening ST-602 tolerances without an ADR.
- Marking GitHub `ssot-check` / `dbt-check` **required** (operator; same class as TP.02).
- Replacing `tests/golden/strategy_annual_summary.json` with real-warehouse euros without human approval (AGENTS §2.6 / EN-072).

</domain>

<decisions>
## Implementation Decisions

### Shared aligner (Area A — ST-101, ST-501, T6.01)
- **D-01:** Implement the NULL-price drop **once** in `epra.strategies.align` (name pinned at plan time if a better module is greppable). Join `fct_consumer_load_hourly` × `fct_price_hourly` on `ts_utc`. Drop hours where `price_at_eur_mwh` is NULL from **both** volume and cost. The resulting `AlignedVolumes` (hourly load+price with no NULLs, plus monthly `volume_mwh` sums) is the **only** volume every strategy sees. Log dropped-hour count (stdlib logging). Unit test: 3 NULL hours in a synthetic month → identical monthly volume for S1–S4. Do **not** drop independently inside `cost_s1` / S4.
- **D-02:** `w_peak` is the `consumer_peak_share` value in `data/processed/ssot_inputs_profile.parquet` (`tag=CALIBRATED`). Missing file or key → raise naming the path. Never copy 0.48 / 0.486 / YAML into strategy code.

### Operator interface (Area B — ST-002, EN-050)
- **D-03:** `make simulate` = `python -m epra.strategies.retrospective` then `python -m epra.strategies.forward_risk`. **No dbt** inside simulate (same pattern as `make analyze`). Missing warehouse → exit 1 with `make warehouse` hint. After simulate, operator `make warehouse` re-exposes parquet via `fct_procurement_cost_monthly`. `make ssot` is `python scripts/generate_ssot.py` only (reads persisted outputs, never recomputes costs).
- **D-04:** Do **not** commit fixture-warehouse strategy PNGs/MD or `NUMERIC_SSOT.md` filled with synthetic euros as Q1/Q3 evidence. Tests write via `tmp_settings`. Operator `make warehouse && make simulate && make ssot` on real marts produces DL-2/DL-4 files. This checkout has no `data/raw` backfill (A-2).

### Stand-in parquet vs ST-001 name (Area C — ST-001, ADR-010, SG-06)
- **D-05:** Canonical write is `data/processed/strategy_costs_monthly.parquet` (ST-001 columns: `year_local, month_local, strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh`). **Also** write the same frame to `data/processed/procurement_cost_monthly/strategy_costs_monthly.parquet` so existing `sources.yml` glob and ADR-010 drop-in keep working with **zero mart SQL change**. Bootstrap stand-in remains until this write lands; do not disable `fct_procurement_cost_monthly`. Clear the stand-in glob directory before writing so old synthetic months cannot mix with real engine output.

### 2019 calibration vs CI fixture (Area D — ST-201, ADR-010, ST-602)
- **D-06:** ADR-010 warehouse is **2022–2024** and **has no 2019**. Anchors and ST-602(a) **cannot** run honestly on fixtures. Pattern matches M5 D-06: pure functions + injected synthetic-2019 frames in unit tests; `compute_anchors` / ST-602 assertions **skip** (not pass) when 2019 or crisis-year coverage is incomplete; `make simulate` on a real warehouse **fails closed** if anchors cannot be formed or ST-602(a) is violated. Do **not** extend the fixture to 2019. Do **not** invent 2019 prices or ÖSPI. Plausibility band `p_ref_base ∈ [30, 60]` EUR/MWh is an operator/real-data check recorded in the PR when a warehouse exists — never fabricate the number to land in band.

### Vectorized forward engine from day one (Area E — ST-406, T-6, T6.07)
- **D-07:** Implement **ST-406 cost cells in T6.07 from the first commit** — do not ship an N=2000 hourly loop and vectorize later. `CostCells` indexed by `(horizon_month, pool_year, strategy_id)` with count `horizon_months × pool_years × 7` (12 × ~7 × 7 when horizon is 12). Horizon-month **volumes** come from the SPEC-03 forward-window profile (aligned). Horizon-month **prices and ÖSPI** come from the drawn pool year of the same calendar month, mapped with SG-07, **together** (T-6). Document the additivity equivalence in the `build_cost_cells` docstring (guide 5.6).
- **D-08:** One `numpy.random.default_rng(seed)` for the whole engine; draw order **path-major, month-minor** (`for path: for month: draw`). Never re-seed inside loops. Seed from `config/strategies.yaml` (`forward.seed`, default 42).
- **D-09:** S3 lock in the forward engine: use **real** (already observed) lock-window ÖSPI where that window is in the past; use **drawn** ÖSPI where it lies in the future (ST-402). For a typical next-12-month horizon after a complete year, H2 of Y−1 is fully observed → `p_S3` constant; **still implement and unit-test** the drawn-ÖSPI branch with a synthetic horizon where the lock window is not yet observed. Missing ÖSPI in a lock or drawn month → **raise** (never extrapolate, A-2).

### Day-mapping, quantiles, HMM reuse (Area F — ST-401, SG-07, SG-08)
- **D-10:** Adopt **SG-07 at T6.07 via ADR-014**: map by `(day-of-month index, hour_local)`. If target day `d` exceeds drawn-month length, reuse the drawn month's **last day whose `is_weekend` equals the target day's** (weekday-type, not a third “holiday” class unless `is_weekend` already encodes it via calendar). DST-missing hour: forward-fill from the previous local hour. DST-extra hour: reuse the drawn 02:00 value. Deterministic; documented in the mapper docstring. Do not invent hours from another month.
- **D-11:** Adopt **SG-08 at T6.07 via ADR-015**: `numpy.quantile(..., method="linear")` for P5/P50/P95. `CVaR95` = mean of the `ceil(0.05 * N)` **highest** annual costs (N=2000 → 100 paths). Pin in `summarize()` only. Closed-form test on a crafted vector.
- **D-12:** No-crisis pool: **reuse** `fit_hmm` + `december_regime(year, dates, labels)` from `epra.analytics.regimes` on mart `fct_price_daily` (same `d_t` / BLAS pins). Exclude years whose December label is `crisis`. Do **not** reimplement HMM. Do **not** require a new A3 parquet (M5 did not persist daily labels). Tie-break is **M5 D-10 (calm wins)** — ignore the outdated guide 5.5 sentence that said higher-volatility wins. Missing December in a pool year → that year cannot enter the no-crisis pool (raise or exclude with a log; never guess).

### Captions, sensitivities, peak fallback (Area G — ST-502, ST-303, ST-104)
- **D-13:** `ST502_SENTENCE` constant (exact SPEC-05 §7 text) applied by a helper on every S2/S3/S4 PNG (`save_png` tag **CALIBRATED** for retrospective contract prices; **SIMULATED** for forward) and markdown. Tests `assert ST502_SENTENCE in body` / artist text. S1 charts are VERIFIED spot × constructed load — stamp LP-050 on artifacts that show StyriaMetal MWh (consumer-load-derived).
- **D-14:** Exactly **three** sensitivities (ST-303), each a **config-delta rerun** of the same engine: (a) `fixed_premium_eur_mwh ∈ {0, 5, 10}`; (b) `flat_baseload` via existing `build_profile(..., profile_name=...)` then re-align (no forked formulas); (c) `lock_window_months = [1..12]` of Y−1. One compact `reports/strategies/sensitivity_matrix.md`. No fourth sensitivity (A-3).
- **D-15:** `peak_available: false` (ST-104) is implemented and unit-tested with injected ÖSPI; default YAML stays `true`. If peak series is all-NULL, `p_S2`/`p_S3` use base-only formula and LIMITATIONS already has / gains the ING-104 sentence — do not invent peak index values.

### SSOT, checker, goldens (Area H — GV-301..303, ST-601, SG-09)
- **D-16:** Producers write `ssot_inputs_{profile,analytics,strategies}.parquet` (existing schema `key,value,unit,tag,produced_by`). `epra.report.ssot.assemble` concatenates, asserts GV-302 keys present **exactly once**, E-2 (tag comes from the producer row, not retyped in the renderer), sorts by key, renders markdown. `data_last_month` is derived from the warehouse latest complete month (VERIFIED, `produced_by=epra.report.ssot`) — not invented. `make ssot` does not call simulate.
- **D-17:** Adopt **SG-09 at T6.08 via ADR-016**: `updated_at` = max(mtime of input artifacts) rendered ISO-8601 UTC. Two `make ssot` runs with unchanged inputs → **byte-identical** `NUMERIC_SSOT.md`. Rounding rule for GV-303: README/EXEC literal with `d` displayed decimals matches SSOT iff `|literal − round_half_up(value, d)| = 0`. Whitelist `scripts/ssot_whitelist.txt` with mandatory `# reason` per line (years, section numbers, config echoes). Mutation test: change one README digit → checker fails naming the key. At M6, README still has no result euros (SG-12) — job 4 must pass on whitelist only until M7.
- **D-18:** CI `ssot-check` job is **added** in T6.09 (EN-080 job 4). Making it a GitHub **required** check is operator (do not claim TP.02-class settings). Job runs `python scripts/check_ssot_consistency.py` on the committed SSOT + docs; it must not require a live warehouse.
- **D-19:** `scripts/generate_golden_metrics.py` refuses a dirty git tree. `tests/golden/strategy_annual_summary.json` first commit is a **synthetic**, hand-computable annual matrix from the same injected frames as unit tests (engine regression / ST-601 in CI). It is **not** Austrian market evidence. Replacing it with real-warehouse values requires human approval in the same PR as the diff (AGENTS §2.6). Do not write fixture-warehouse euros into that file and call them accepted results.

### ADR governance (Area I)
- **D-20:** Next free ADR number is **014**. Assign: **ADR-014 = SG-07** (T6.07), **ADR-015 = SG-08** (T6.07), **ADR-016 = SG-09** (T6.08). Do not speculative-ADR anything else. If ST-602(a) fails on real data, stop (2 focused attempts) — calibration bug, not a tolerance ADR.

### Claude's Discretion
- Internal helpers under 03_MODULES names; functions ~60 lines (W-3); vectorized pandas/numpy.
- Whether align module is `align.py` vs `_data.py` — one shared loader, no copy-paste SQL.
- Chart implementation (grouped bar vs pandas plot) provided RP-701/702/704 (`STRATEGY_COLORS`) and object-inspection tests.
- Whether `make simulate` wipes known `reports/strategies/` filenames before write (prefer wipe-then-write of the known set, not `rm -rf` reports).
- `CostCells` storage (xarray vs MultiIndex DataFrame) as long as the contract and draw lookups are deterministic.
- Hybrid dispatch: three functions vs one `cost_s4(h)` — prefer one function parameterized by `h` keyed as `S4_30`/`S4_50`/`S4_70`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Binding spec (authority)
- `docs/SPEC-05_strategy_simulator.md` — whole file.
- `docs/SPEC-08_governance_quality.md` §3 (GV-301..303 key set and checker).
- `docs/SPEC-06_reporting_dashboard.md` §7 (RP-701..705) for strategy charts.
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M6 T6.01–T6.10.
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` strategies + scripts table.
- `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §5.6 (anchor identities, ST-406 equivalence, draw order, SSOT/checker design). **Exception:** December-regime tie-break — use M5 D-10 (calm wins), not guide 5.5.
- `docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md` §M6.
- `docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md` SG-07, SG-08, SG-09 (adopt via ADRs 014–016).
- Traps T-5 (ÖSPI index through P_ref) and T-6 (joint month draw).

### Upstream already shipped
- `epra.common.config.StrategyCfg` / `load_strategy_config`.
- `epra.analytics.regimes.fit_hmm`, `daily_diff`, `december_regime` (D-09/D-10).
- `epra.analytics._kit.save_png` / SSOT upsert pattern.
- `epra.consumer.profile.build_profile` + `flat_baseload` + `ssot_inputs_profile.parquet`.
- `epra.report.style.STRATEGY_COLORS`, `FIGSIZE`, `DPI`, `SOURCE_NOTE`.
- `dbt/seeds/dim_strategy.csv` (6 ids); `fct_procurement_cost_monthly` loader; ADR-010 stand-in glob.
- Stubs: `calibration.compute_anchors`, `retrospective.run`/`main`, `forward_risk.run`/`main`.

### Governance
- Charter Q1 / Q3 / REQ-ST-01 / REQ-Q1 / REQ-Q3.
- A-2 no invented market facts; A-3 no extra strategies/sensitivities; A-4 determinism; A-6 no hand-typed README euros.
- ST-602(a) failure = calibration bug. Golden real-euro regen = human.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Three strategy modules + charts stub are loud stubs (`test_stubs_fail_loudly.py` M6 rows). Delete a stub row in the commit that un-stubs that entrypoint. M7 `charts.render_executive_charts` stays.
- Warehouse report still flags `fct_procurement_cost_monthly` as stand-in — clear that flag in T6.05/T6.10 when real parquet is the contract (or keep flag for fixture-only checkouts — planner should prefer: stand-in flag iff glob still looks like bootstrap, else not).
- `tmp_settings` redirects `reports`, `warehouse`, `data_processed`.
- Chart colors exist; strategy charts **must call** `STRATEGY_COLORS`, not duplicate hex.

### Established Patterns
- Functional core / imperative shell (analytics, profile).
- SSOT producer parquet per milestone; M6 concatenates.
- Isolated injected DataFrames for unit tests; skip-if-incomplete for gates that need 2019.
- Docstrings `Implements: ST-xxx`.
- Dual-write processed parquet if dbt glob ≠ spec filename (do not fork mart SQL).

### Integration Points
- New: `align.py`, `epra.report.ssot`, `epra.report.ssot_check`, `scripts/generate_ssot.py`, `scripts/check_ssot_consistency.py`, `scripts/ssot_whitelist.txt`, `scripts/generate_golden_metrics.py`, ADRs 014–016, `tests/golden/strategy_annual_summary.json`.
- Modified: calibration/retrospective/forward_risk, Makefile `simulate`/`ssot`, CI job 4, bootstrap writer only if the dual-write filename must stay glob-compatible, warehouse stand-in tuple, stub tests, BUILD_LOG.
- Unchanged: SPEC-05 text, `config/strategies.yaml` numerics, dim_strategy seed, analytics HMM math, consumer YAML, fixture year window.

</code_context>

<specifics>
## Specific Ideas

- **Anchor identities (guide 5.6):** at ÖSPI = ref, `p_S2` = `p_ref_base*(1-w) + p_ref_peak*w`; S3 at ref + premium 0 equals the same blend. If a test S3 lands ~5000 EUR/MWh, T-5 fired.
- **ST-202 docstring** must contain the spec sentence about 2019 peak rescaled by realized-vs-base ratio.
- **ST-503:** spy/fixture test that `p_s3(2022, ...)` reads only 2021-07..12 ÖSPI rows.
- **ST-602(b):** `min(S1,S3) ≤ S4_50 ≤ max(S1,S3)` within ±0.5% (premium tolerance) every retrospective year present.
- **ST-304 files:** `s5_annual_costs.png`, `s5_cumulative.png`, markdown unit-cost table under `reports/strategies/`.
- **ST-403/404 files:** `s5_forward_fan.png`, `s5_risk_return.png`, `forward_risk_summary` table (unconditional + no-crisis).
- **GV-302 matrix keys:** `cost_<strategy>_<year>` for each of 6 ids × 5 years when the year exists; absent years are omitted (NULL/absent), never filled with invented costs.
- **LP-050** on S1 volume-derived artifacts: constructed-profile sentence already in LIMITATIONS; stamp the caption where StyriaMetal MWh appear.

</specifics>

<deferred>
## Deferred Ideas

- README / EXEC_SUMMARY quoting SSOT (M7; human co-writes EXEC §5 recommendation).
- `exports/` CSVs and RP-201..204 executive charts (M7).
- `refresh.yml` / Power BI `.pbix` (M7; `.pbix` is human).
- TP.02 required-check flip for `dbt-check` and the new `ssot-check`.
- EN-072 replacement of synthetic ST-601 golden with real-warehouse euros (human).
- AN-304 / ST-602(a) on a real 2019+ warehouse (operator).
- Committing real `reports/strategies/` PNGs and real `NUMERIC_SSOT.md` — operator machine with backfill.

</deferred>
