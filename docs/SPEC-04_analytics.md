# SPEC-04 — Market Analytics (modules A1–A4)

Answers Q2. All computations read from DuckDB marts (SPEC-02), never from raw files.
Code in `src/epra/analytics/`, one module per block. Outputs land in `reports/analytics/`
(markdown + PNG) and feed the SSOT. Requirement IDs: `AN-xxx`.
Chart style rules are in SPEC-06 §7 and are mandatory here.

---

## A1 — Descriptive market structure (`analytics/descriptive.py`)

- AN-101: Annual summary table (per year_local 2019→latest, AT):
  mean/median/std/min/max of hourly price, base price, peak price, off-peak price,
  peak−off-peak spread, count + share of negative hours, count of hours > 500 EUR/MWh.
  Output: `reports/analytics/a1_annual_summary.md` (markdown table) + CSV alongside.
- AN-102: Hour-of-day × month heatmap of mean price, one panel per year 2021–2025
  (5 panels, shared color scale, EUR/MWh). File: `a1_heatmap_hour_month.png`.
- AN-103: Price duration curves: for each year 2019→latest, sorted hourly prices vs.
  fraction of hours (x: 0–100%, y: EUR/MWh, log-free). One figure, one line per year,
  crisis years visually distinguishable. File: `a1_duration_curves.png`.
- AN-104: Negative-price analysis: per year — count of negative hours, mean depth
  (EUR/MWh below zero), distribution across hour_local (bar chart), share occurring in
  Apr–Sep daylight hours (10–16 local). Files: `a1_negative_hours.png` + rows in SSOT
  (`neg_hours_<year>`, VERIFIED).
- AN-105: Written interpretation: `a1_annual_summary.md` ends with a "So what for a
  procurement manager" paragraph of 5–10 sentences (plain prose, no bullets) explaining
  the shape findings. Content requirements: must mention solar-driven midday depression
  in recent years, the 2022 crisis level, and what negative hours mean for a flexible
  consumer.

## A2 — AT–DE-LU spread (`analytics/spread.py`)

- AN-201: Monthly mean spread (AT − DE_LU) line chart 2019→latest with zero line.
  File: `a2_spread_monthly.png`.
- AN-202: Spread statistics table per year: mean, median, std, share of hours AT > DE,
  mean spread within peak vs. off-peak hours. Output: `a2_spread_summary.md` + SSOT rows
  (`spread_mean_<year>`, VERIFIED).
- AN-203: Interpretation paragraph: what a persistent positive AT premium implies for an
  Austrian consumer benchmarking against German price reporting (the "you are not in
  Germany" localization point).

## A3 — Volatility regimes (`analytics/regimes.py`)

Basis series: DAILY series `d_t = price_base_eur_mwh(t) − price_base_eur_mwh(t−1)`
(EUR/MWh, arithmetic differences — NOT log returns, because prices can be ≤ 0).

- AN-301: Realized volatility: rolling 30-day std of `d_t`, plotted with the base price
  (twin axis, labeled). File: `a3_realized_vol.png`.
- AN-302: HMM regimes: Gaussian HMM on `d_t` standardized (z-score using full-sample
  mean/std). Library: `hmmlearn`, `GaussianHMM(n_components=3, covariance_type='full',
  n_iter=500, random_state=42)`. Fit 10 restarts (`random_state=42..51`), keep the
  highest log-likelihood. Label states by ascending state std: `calm`, `elevated`,
  `crisis`. Output: regime timeline chart (`a3_regimes.png`, colored bands under the
  price line) + per-regime stats table (`a3_regime_stats.md`: occupancy %, mean |d_t|,
  mean price level).
- AN-303: GARCH complement: `arch` package, GARCH(1,1) with constant mean on `d_t`
  (rescale by 1/10 if the optimizer warns about scale; document the rescale in the
  output). Report conditional volatility plot overlaid with the 30-day realized vol
  (`a3_garch_vs_realized.png`) and the persistence α+β in SSOT (`garch_persistence`,
  VERIFIED). If α+β ≥ 1, report it and note near-integrated volatility — do not "fix" it.
- AN-304: SANITY GATE (M5 exit): ≥ 70% of days in 2021-09-01 → 2023-06-30 must be
  classified in the top-2 volatility states, and ≥ 60% of days in 2019 in the calm state.
  Failure ⇒ investigate standardization or restarts; widening the gate requires an ADR.

## A4 — Weather & load sensitivity (`analytics/weather.py`, deliberately small)

- AN-401: Scatter + OLS fit: daily AT load (mean MW) vs. HDD_18, colored by weekend flag,
  with month fixed effects OLS summary (statsmodels, HC1 robust SE) written to
  `a4_load_weather.md`. File: `a4_load_vs_hdd.png`.
- AN-402: One paragraph interpretation: temperature sensitivity of the SYSTEM (not the
  reference consumer — its profile is weather-invariant by construction; say so
  explicitly to preempt reviewer confusion).

## §5 Degree-day definitions

HDD_18(d) = max(0, 18 − tavg_c(d)); CDD_22(d) = max(0, tavg_c(d) − 22). Computed in
`dim_calendar` (SPEC-02 §4); analytics never recompute them.

## §6 Deliverables checklist for M5 (all must exist)

```
reports/analytics/a1_annual_summary.md      reports/analytics/a1_heatmap_hour_month.png
reports/analytics/a1_duration_curves.png    reports/analytics/a1_negative_hours.png
reports/analytics/a2_spread_monthly.png     reports/analytics/a2_spread_summary.md
reports/analytics/a3_realized_vol.png       reports/analytics/a3_regimes.png
reports/analytics/a3_regime_stats.md        reports/analytics/a3_garch_vs_realized.png
reports/analytics/a4_load_vs_hdd.png        reports/analytics/a4_load_weather.md
```

## §7 Gates (M5 exit)

- AN-701: All §6 artifacts exist and are regenerated by `make analyze` from a clean state.
- AN-702: AN-304 regime sanity gate passes.
- AN-703: Every SSOT value emitted by analytics is produced by code (no manual numbers)
  and tagged VERIFIED.
- AN-704: Each .md artifact contains its interpretation paragraph (checked by a test that
  asserts ≥ 400 characters of prose after the last table).
- AN-705: Determinism: running `make analyze` twice yields identical SSOT values
  (seeded HMM restarts make this exact, not approximate).
