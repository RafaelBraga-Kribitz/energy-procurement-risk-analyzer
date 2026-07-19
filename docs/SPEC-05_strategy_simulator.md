# SPEC-05 — Procurement Strategy Simulator

Answers Q1 (retrospective), Q3 (forward risk), and feeds Q4. Requirement IDs: `ST-xxx`.
Code in `src/epra/strategies/`. This is the heart of the project — implement it EXACTLY.

---

## 1. Scope of the decision being modeled

The consumer buys `volume_mwh(y, m)` (SPEC-03, LP-021) every month. Only the ENERGY price
differs by strategy; volumes are identical across strategies (no demand response — Charter
O-3). Costs exclude grid fees/taxes/levies (Charter §2). All costs in nominal EUR.

## 2. Architecture

- ST-001: Pure-Python computation on pandas DataFrames pulled from DuckDB marts. Results
  are written to `data/processed/strategy_costs_monthly.parquet` and re-exposed via dbt
  (`fct_procurement_cost_monthly`) and `exports/`. dbt does NOT compute strategy costs.
- ST-002: Entry points: `python -m epra.strategies.retrospective` and
  `python -m epra.strategies.forward_risk`. Both are `make` targets.
- ST-003: All tunables in `config/strategies.yaml` (§8). No magic numbers in code.

## 3. Strategy definitions (families S1–S4; grid in dim_strategy, SPEC-02 §4)

### S1 — FULL_SPOT

- ST-101: `cost_S1(y, m) = Σ_h∈(y,m) load_mwh(h) × price_at_eur_mwh(h)`
  Hourly join on `ts_utc` between `fct_consumer_load_hourly` and `fct_price_hourly`.
  Hours with NULL price (post-validation there are ≤ 24/year): drop the hour from BOTH
  volume and cost in S1 *and* rescale that month's other strategies' volume identically,
  so all strategies price the same volume (fair comparison). Log dropped hours.

### S2 — OESPI_INDEXED (monthly floating indexed contract)

- ST-102: Monthly contract price:
  `p_S2(y, m) = p_ref_base × (oespi_base(y,m) / oespi_base_ref) × (1 − w_peak)
              + p_ref_peak × (oespi_peak(y,m) / oespi_peak_ref) × w_peak`
  where `w_peak = consumer_peak_share` (LP-020, from SSOT input file, not retyped).
- ST-103: `cost_S2(y, m) = volume_mwh(y, m) × p_S2(y, m)`.
- ST-104: If `peak_available: false` (ING-104): `p_S2 = p_ref_base × oespi_base/oespi_base_ref`
  and LIMITATIONS gains a sentence.

### S3 — FIXED_ANNUAL (price locked before the delivery year)

Models a supplier fixed-price offer for delivery year Y, priced off the forward market as
approximated by ÖSPI (the index is constructed from futures-based fictitious procurement —
this proxy choice is R-5 and must be captioned on every S3 output).

- ST-105: Lock rule: the fixed price for delivery year Y uses the ÖSPI values available in
  the LOCK WINDOW = months `Y−1`-07 … `Y−1`-12 (H2 of the prior year, when annual contracts
  are typically closed):
  `p_S3(Y) = p_ref_base × mean(oespi_base over lock window)/oespi_base_ref × (1 − w_peak)
           + p_ref_peak × mean(oespi_peak over lock window)/oespi_peak_ref × w_peak`
  plus a fixed-price service premium `fixed_premium_eur_mwh` (default 5.0, §8) reflecting
  supplier risk margin. Premium value is CALIBRATED; sensitivity at 0 and 10 (ST-303).
- ST-106: `cost_S3(y, m) = volume_mwh(y, m) × p_S3(y)` (same price all 12 months).

### S4 — HYBRID_h (h ∈ {0.30, 0.50, 0.70})

- ST-107: Each month, fraction `h` of the month's volume at the S3 fixed price (same lock
  rule), remainder at spot:
  `cost_S4h(y, m) = h × volume_mwh(y,m) × p_S3(y) + (1−h) × Σ_h load_mwh × spot` where the
  spot leg reuses the S1 hourly computation scaled by `(1−h)` (volume shares apply
  uniformly across hours — documented simplification).

## 4. Calibration anchors

- ST-201 (`p_ref_base`): volume-weighted average spot cost per MWh of the reference
  consumer in calendar 2019: `p_ref_base = cost_S1(2019) / volume(2019)`. CALIBRATED.
- ST-202 (`p_ref_peak`): mean AT hourly price over peak hours of 2019 × (p_ref_base ÷
  mean AT hourly price over all hours of 2019) — i.e., the 2019 peak price rescaled by
  the consumer's realized-vs-base ratio, keeping the base/peak anchor pair internally
  consistent. Formula implemented once, in `calibration.py`, with a docstring repeating
  this sentence.
- ST-203 (`oespi_base_ref`, `oespi_peak_ref`): arithmetic mean of the respective ÖSPI
  series over calendar 2019.
- ST-204: All four anchors are written to the SSOT with tag CALIBRATED and quoted in
  LIMITATIONS.

## 5. Retrospective engine (Q1)

- ST-301: Compute `cost(strategy, year, month)` for all strategies × months 2021-01 …
  2025-12. Aggregate to `strategy_annual_summary`: `year, strategy_id, volume_mwh,
  cost_eur, unit_cost_eur_mwh, delta_vs_min_eur (cost − min cost across strategies that
  year), rank`.
- ST-302: Headline metric `wrong_strategy_cost(Y) = max_strategy cost(Y) − min_strategy
  cost(Y)`, plus the 5-year total. → SSOT (`wrong_strategy_cost_total`, CALIBRATED). This
  is DL-2 and the README's first number.
- ST-303: Sensitivities (each = full rerun with one change, output as one compact table):
  (a) `fixed_premium_eur_mwh ∈ {0, 5, 10}`; (b) load profile = `flat_baseload` (LP-030);
  (c) lock window = full prior year `Y−1`-01…`Y−1`-12. File:
  `reports/strategies/sensitivity_matrix.md`. No further sensitivities (scope guard).
- ST-304: Charts: (1) grouped bar — annual cost per strategy per year 2021–2025
  (`s5_annual_costs.png`); (2) line — cumulative 5-year cost per strategy
  (`s5_cumulative.png`); (3) unit cost EUR/MWh table rendered as markdown. Chart rules
  per SPEC-06 §7.

## 6. Forward risk engine (Q3) — seasonal block bootstrap

Simulates the NEXT 12 calendar months after the latest complete data month.

- ST-401: Price path generation, algorithm (implement verbatim):
  1. Pool: historical months 2019-01 … latest, each month m represented by its vector of
     hourly prices AND its ÖSPI values.
  2. For simulation i (i = 1…N, N = 2000) and each target future month with calendar
     month c: draw uniformly (seeded RNG, `numpy.random.default_rng(seed=42)`; one RNG
     for the whole engine, draws in deterministic loop order) a historical YEAR y′ from
     the pool years for calendar month c; use that month's full hourly price vector and
     its ÖSPI values together (keeps spot/index coherence within the drawn month).
  3. Hour-count alignment: map drawn-month hours to target-month hours by (day-of-month
     index, hour_local); if the target month has more days than the drawn month (e.g., 31
     vs 30), reuse the drawn month's last same-weekday-type day; if fewer, truncate. DST
     mismatches resolved by local-hour alignment with forward fill for the missing hour.
  4. Regime conditioning (secondary output): repeat the whole simulation with the year
     pool RESTRICTED to years whose December HMM regime (AN-302) is `calm`/`elevated`
     (i.e., excluding crisis years). Report both unconditional and no-crisis variants.
- ST-402: For each path: compute cost per strategy using §3 formulas, with S3's lock price
  computed from the REAL (already observed) lock-window ÖSPI where the lock window lies in
  the past; where it lies in the future, from the drawn ÖSPI values. Consumer volumes from
  the SPEC-03 forward-window profile.
- ST-403: Outputs per strategy: mean, std, P5, P50, P95, CVaR95 (mean of the worst 5% =
  highest costs) of annual (12-month) total cost. Table `forward_risk_summary` → exports,
  SSOT (tag SIMULATED), and chart `s5_forward_fan.png` (distribution per strategy —
  horizontal box/violin, P95 marked).
- ST-404: Risk-return frame for Q4: scatter of mean cost (x) vs. P95 (y) per strategy
  (`s5_risk_return.png`); the exec summary reads the efficient frontier off this chart.
- ST-405: Determinism: same seed ⇒ identical SSOT values. `make simulate` twice → diff
  clean (tested).
- ST-406: N=2000 must run in < 10 min on a laptop; if not, vectorize months (precompute
  per-(month, year′) strategy costs once — 12 × ~7 years × 7 strategies ≈ 600 cells —
  then bootstrap over the cost cells, which is mathematically identical because costs are
  additive over months and strategies share drawn months within a path). This
  optimization is the RECOMMENDED implementation.

## 7. Fair-comparison and honesty rules

- ST-501: Identical volumes across strategies per month (see ST-101 drop rule).
- ST-502: Every S2/S3/S4 output caption: "Contract prices proxied via ÖSPI
  (futures-based index); premiums are calibrated assumptions — see LIMITATIONS."
- ST-503: No strategy may peek at future information except S3's documented lock rule.
  Code review checklist item; also a test asserting `p_S3(2022)` uses only 2021-07..12
  index values.

## 8. `config/strategies.yaml` (authoritative copy)

```yaml
retrospective_years: [2021, 2022, 2023, 2024, 2025]
reference_year: 2019
lock_window_months: [7, 8, 9, 10, 11, 12]   # of year Y-1
fixed_premium_eur_mwh: 5.0
hybrid_ratios: [0.30, 0.50, 0.70]
forward:
  n_paths: 2000
  seed: 42
  horizon_months: 12
peak_available: true
```

## 9. Gates (M6 exit)

- ST-601: Golden metrics test: `tests/test_golden_strategies.py` recomputes the annual
  cost matrix and compares to `tests/golden/strategy_annual_summary.json` (written by
  `scripts/generate_golden_metrics.py` once results are first accepted; any legitimate
  change requires regenerating goldens in the same PR with an explanation).
- ST-602: Sanity relations that MUST hold (hard assertions):
  (a) in 2022, `cost_S1 > cost_S3` (spot was catastrophic vs. pre-crisis locks);
  (b) in every year, `min(S1,S3) ≤ cost_S4_50 ≤ max(S1,S3)` (hybrid is between its legs,
  within ±0.5% tolerance for the premium);
  (c) forward risk: `P95(S1) ≥ P95(S3)` (spot has the fattest right tail).
  If (a) fails, the ÖSPI translation is broken — stop and debug; do not rationalize.
- ST-603: ST-405 determinism test green; ST-503 no-lookahead test green.
- ST-604: SSOT regenerated and consistent (SPEC-08 §4 check passes).
