# Phase 7: M6 Strategy Simulator - Research

**Researched:** 2026-09-03
**Domain:** Mart-backed S1–S4 costs, 2019 CALIBRATED anchors, seasonal block bootstrap via ST-406 cells, NUMERIC_SSOT assembly, GV-303 checker
**Confidence:** HIGH for in-repo marts/config/stubs/HMM reuse (read this session). HIGH for numpy.quantile / Decimal rounding (stdlib+numpy already pinned). MEDIUM for ST-602(a) on real 2022 vs locked 2021 H2 ÖSPI (this checkout has no warehouse — gate is skip-if-incomplete per D-06).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Shared ST-101 aligner; `AlignedVolumes` is the only volume.
- **D-02:** `w_peak` from `ssot_inputs_profile.parquet` / `consumer_peak_share`.
- **D-03:** `make simulate` = retrospective then forward_risk; no dbt.
- **D-04:** No committed fixture euros as Q1/Q3 evidence.
- **D-05:** Dual-write ST-001 parquet + ADR-010 glob.
- **D-06:** Skip-if-incomplete 2019; fail-closed when coverage exists; no fixture extension.
- **D-07:** ST-406 cells from day one; grain `(horizon_month, pool_year, strategy)`.
- **D-08:** One `default_rng`; path-major, month-minor.
- **D-09:** S3 lock: real ÖSPI if past, drawn if future; missing → raise.
- **D-10:** SG-07 + ADR-014.
- **D-11:** SG-08 + ADR-015.
- **D-12:** Reuse M5 `fit_hmm` + `december_regime` (calm wins).
- **D-13:** ST-502 helper; CALIBRATED retro / SIMULATED forward; LP-050 on StyriaMetal MWh.
- **D-14:** Exactly three ST-303 config-delta sensitivities.
- **D-15:** ST-104 implemented; default YAML `peak_available: true`.
- **D-16:** Concatenate `ssot_inputs_*.parquet`; `data_last_month` from marts.
- **D-17:** ADR-016 mtime `updated_at`; half-up GV-303.
- **D-18:** Add `ssot-check` job; required-check is operator.
- **D-19:** Synthetic ST-601 golden; real-euro replace is human.
- **D-20:** ADRs 014/015/016 only.

### Deferred
- README/EXEC euros (M7), exports, `.pbix`, TP.02, EN-072 real goldens, operator ST-602(a)/AN-304.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ST-01 / REQ-Q1 | 5-year × 6-id cost matrix + wrong-strategy headline | Patterns 1–4 |
| REQ-Q3 | Forward mean/P5/P50/P95/CVaR95, seed-reproducible | Patterns 5–6 |
| ST-602 a/b/c | Hard sanity; (a) skip-if-no-2019-anchors | D-06 + Validation |
| ST-601 | Golden JSON vs recomputed matrix | D-19 synthetic |
| GV-301..303 | SSOT markdown + checker + CI job 4 | Patterns 7–8 |
</phase_requirements>

## Summary

M6 is **pure-Python costing on mart frames**, not dbt. `fct_price_hourly` already has `price_at_eur_mwh`, `is_peak_hour`, `year_local`/`month_local`/`hour_local`/`is_weekend`/`date_local`. `fct_consumer_load_hourly` has only `ts_utc, load_mwh` — local month comes from the price/calendar join. `fct_price_monthly` already left-joins ÖSPI (`oespi_base`, `oespi_peak`). `StrategyCfg` and `dim_strategy` (6 ids) are committed. M5 HMM is importable.

Non-obvious HOW items:

1. **Aligner join:** inner-join load to hourly prices on `ts_utc`, then drop rows with NULL `price_at_eur_mwh`. Monthly `volume_mwh` = sum of remaining `load_mwh`. Consumer mart has no `year_local` — take it from the price frame (same calendar spine). Log `dropped_null_price_hours`.
2. **ÖSPI source:** read `marts.fct_price_monthly` (oespi columns). Do **not** call `epra.ingest.oespi.load_oespi` from the engine (raw/manual bypass). Missing lock-window months → raise listing YYYY-MM (D-09, A-2).
3. **ST-202:** `p_ref_peak = mean(peak-hour AT prices, 2019 aligned) * (p_ref_base / mean(all-hour AT prices, 2019 aligned))`. Copy the spec sentence into `compute_p_ref_peak` docstring. `w_peak` is **not** in this formula; it enters `p_s2`/`p_s3` blends.
4. **T-5 identity:** if `oespi_base == oespi_base_ref` and `oespi_peak == oespi_peak_ref`, `p_s2 = p_ref_base*(1-w)+p_ref_peak*w`. S3 with premium 0 and lock-window mean equal to ref → same blend. A ~10× spot S3 is index×volume (stop).
5. **S4:** `cost_s4(h) = h * volume_mwh * p_s3(year) + (1-h) * cost_s1_month`. Reuse monthly S1 costs; do not re-sum hours. Ids `S4_30`/`S4_50`/`S4_70` from `hybrid_ratios`.
6. **Cells (D-07):** For each horizon month M (12 months after `data_last_month`), each pool year y′ that has a complete calendar-month c = M.month in 2019…latest, map y′’s hourly prices + that month’s ÖSPI onto M’s local hours (ADR-014), apply aligned forward volumes for M, compute 7 strategy costs. `simulate` draws y′ per (path, month) and **adds cells** — never replays hours. Joint draw is automatic because one y′ keys both price mapping and ÖSPI (T-6).
7. **No-crisis pool:** `daily_diff` + `fit_hmm` on `fct_price_daily` once per `run()`; `december_regime(y, dates, labels)` for each pool year; drop `crisis`. Inject labels in unit tests so CI does not require 2019 daily prices.
8. **`data_last_month`:** derive from **marts** (max complete local month in `fct_price_hourly` / `fct_price_monthly`), **not** `ingest.entsoe.latest_complete_month` (that reads `data/raw` and fails in mart-only tests). Format `YYYY-MM`.
9. **Procurement dtypes:** mart contract types `year_local`/`month_local` as **BIGINT**. Write pandas `int64` so `dbt build` after dual-write does not flip the contract YAML.
10. **CI `ssot-check` vs D-04:** do **not** commit a fake `reports/NUMERIC_SSOT.md`. Job 4 runs the checker: README/EXEC have no result euros yet (SG-12) so doc-side matching is whitelist-only; if `reports/NUMERIC_SSOT.md` is absent, checker **skips** GV-302 completeness (log skip) and still scans docs. Full GV-302 is asserted in unit tests on tmp_settings. Operator `make ssot` on real data creates the committed SSOT (M7 quotes it).
11. **Rounding:** Python `round` is banker’s rounding. GV-303 must use `decimal.Decimal.quantize(..., ROUND_HALF_UP)` to `d` places (ADR-016).
12. **Guide 5.5 vs M5:** December ties already shipped as **calm wins**. Do not “fix” to higher-volatility.

**Primary recommendation:** T6.01 align+loaders → T6.02 anchors → T6.03 S1 → T6.04 S2/S3/S4 → T6.05 annual/charts/parquet → T6.06 sensitivities → T6.07 ADRs+cells+simulate → T6.08 SSOT module → T6.09 checker+CI → T6.10 golden script+determinism+BUILD_LOG.

## Architectural Responsibility Map

| Capability | Primary | Secondary | Rationale |
|------------|---------|-----------|-----------|
| SQL → frames | `strategies.align` / `_data.py` | `epra.common.db.connect` | 08_PATTERNS repository |
| NULL drop + volumes | `AlignedVolumes` | logging | ST-101 once |
| Anchors | `calibration.py` | SSOT producer rows | ST-201..204 |
| S1–S4 formulas | `retrospective.py` | dispatch table | 03_MODULES |
| Annual + charts | `retrospective.run` | `_kit.save_png`, `STRATEGY_COLORS` | ST-301..304 |
| Sensitivities | same engine, cfg copy | `build_profile(flat_baseload)` | ST-303 |
| Cells + bootstrap | `forward_risk.py` | `regimes.fit_hmm` | ST-401/406 |
| SSOT markdown | `epra.report.ssot` | `scripts/generate_ssot.py` | GV-301 |
| Checker | `epra.report.ssot_check` | `scripts/check_ssot_consistency.py` | GV-303 |
| Operator | `make simulate` / `make ssot` | Makefile | D-03 |

## Standard Stack

| Library | Already pinned | Use |
|---------|----------------|-----|
| duckdb + `connect` | yes | read-only marts |
| pandas / numpy | yes | costs, `default_rng`, `quantile` |
| matplotlib Agg | yes | ST-304 / ST-403 charts |
| hmmlearn via `regimes` | yes | no-crisis years |
| pydantic `StrategyCfg` | yes | ST-003 |
| decimal (stdlib) | yes | ROUND_HALF_UP |
| pyarrow | yes | parquet atomic write |

**No new packages.** Do not add seaborn. Do not add a strategy ABC.

## Pitfalls (read before coding)

| # | Pitfall | Mitigation |
|---|---------|------------|
| P1 | ÖSPI × volume without P_ref (T-5) | Identity tests at ref index; fail ST-602(a) → debug calibration |
| P2 | Independent price vs ÖSPI draws (T-6) | Cell keyed by single `pool_year` |
| P3 | Drop NULLs only in S1 | Shared aligner (D-01) |
| P4 | `w_peak` hardcoded | Read parquet or raise |
| P5 | `latest_complete_month` from raw | Mart-derived `data_last_month` |
| P6 | Python `round` vs half-up | Decimal quantize |
| P7 | Dual-write mixing stand-in months | Wipe `procurement_cost_monthly/` before write |
| P8 | BIGINT vs INTEGER year | Write int64 |
| P9 | HMM tie-break regression | Import M5 `december_regime` |
| P10 | Committing fixture SSOT as the answer | D-04; checker skip if file absent |
| P11 | En-dash in Python strings | ASCII hyphen (RUF001) |
| P12 | S3 lookahead | ST-503 fixture spy on ÖSPI rows |
| P13 | CVaR as quantile | Mean of worst `ceil(0.05*N)` paths |
| P14 | Re-seed per path | One RNG, D-08 order |

## GV-302 key enumeration (assembler must emit)

Minimum (SPEC-08). Extra keys allowed (`oespi_peak_ref` **must** also be emitted — ST-204 four anchors; GV-302 lists three of them as the minimum).

- `wrong_strategy_cost_total`, `wrong_strategy_cost_<year>` for each retrospective year present
- `best_strategy_5yr` (strategy_id of min 5-year total among years present; if a year missing, 5-year total uses only present years and the key is still emitted with tag CALIBRATED and a LIMITATIONS note — do not invent missing years)
- `cost_<strategy>_<year>` for each of `S1,S2,S3,S4_30,S4_50,S4_70` × present years
- `p95_next12m_<strategy>`, `cvar95_next12m_<strategy>` (SIMULATED)
- `p_ref_base`, `p_ref_peak`, `oespi_base_ref`, `oespi_peak_ref` (CALIBRATED)
- `consumer_peak_share` (from profile producer)
- `annual_mean_price_<year>`, `neg_hours_<year>`, `spread_mean_<year>`, `garch_persistence` (from analytics producer)
- `data_last_month` (VERIFIED)

Absent years: **omit** `cost_*` / `wrong_strategy_cost_<year>` keys rather than fill 0 (A-2). GV-302 “×5” is the full-window contract on a real warehouse; CI synthetic golden may have fewer years.

## ADR drafts (implementing tasks write the files)

- **ADR-014 (T6.07):** SG-07 mapping algorithm (CONTEXT D-10).
- **ADR-015 (T6.07):** quantile linear + CVaR ceil-highest (D-11).
- **ADR-016 (T6.08):** `updated_at` max mtime ISO-8601 UTC; GV-303 half-up.

## Confidence notes

- Hour mapping on DST: `dim_calendar` / hourly mart already has 23/25-hour local days. Mapper must iterate **target** local hours, not assume 24.
- Forward lock window often fully observed: still unit-test the drawn-ÖSPI branch (D-09).
- `p_ref_base ∈ [30, 60]` is **not** a CI assert on fixtures.
