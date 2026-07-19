# SPEC-03 — Consumer Load Profile ("StyriaMetal GmbH")

Defines the EXACT deterministic construction of the reference consumer's hourly load.
Requirement IDs: `LP-xxx`. Epistemic tag of all outputs: **CALIBRATED**.

---

## 1. Principles

- LP-001: Deterministic: given `config/consumer_profile.yaml` + the calendar, the output
  is bit-reproducible. No randomness anywhere in this module.
- LP-002: All parameters live in `config/consumer_profile.yaml` (full file listed in §6).
  Code reads the YAML; nothing numeric is hardcoded in Python.
- LP-003: Output: `data/processed/consumer_load_hourly.parquet` with columns
  `ts_utc (TIMESTAMP UTC), load_mwh (double)`, one row per hour of the analysis window
  INCLUDING the forward-risk window (SPEC-05 needs future-year load).
- LP-004: Annual normalization: for each **local calendar year**, the sum of `load_mwh`
  equals exactly `annual_consumption_mwh` (50,000) within ±0.01 MWh. Partial years at the
  window edges are normalized pro-rata against the same year's shape (see LP-034).

## 2. Construction algorithm (implement exactly in this order)

Module: `src/epra/consumer/profile.py`, entrypoint `build_profile(calendar_df, cfg) -> df`.

Step 1 — Base weight per hour. Each hour h (local time) gets a raw weight
`w(h) = day_shape[day_type(h)][hour_local(h)] × seasonal_factor(month_local(h)) × special_factor(date_local(h))`

Step 2 — `day_type` decision (first match wins):
1. `date_local` in a shutdown window (§3.3) → `shutdown`
2. `is_holiday_at` → `weekend`
3. `dow_local` in (5, 6) (Sat, Sun) → `weekend`
4. else → `weekday`

Step 3 — `special_factor` (§3.3): `shutdown_factor` for shutdown dates,
`maintenance_factor` for maintenance dates, else 1.0. (Maintenance days keep their
weekday/weekend day_type; shutdown overrides day_type per Step 2.)

Step 4 — Seasonal factor (§3.2) by `month_local`.

Step 5 — Normalize per local year: `load_mwh(h) = annual_consumption_mwh × w(h) / Σ w(h′)`
over all hours h′ with the same `year_local`. For a partial final year (forward window),
normalize against the annual sum THE SHAPE WOULD HAVE (i.e., compute Σ w over the full
hypothetical year using the same calendar rules) so that the partial year's monthly
volumes are consistent with a full-year 50 GWh consumer (LP-034).

## 3. Parameters (the values; also encoded in §6 YAML — YAML wins if they ever diverge)

### 3.1 Day shapes (24 values each, index = hour_local 0–23)

`weekday` (3-shift with day-shift emphasis):
`[0.65, 0.65, 0.65, 0.65, 0.65, 0.75, 0.95, 1.00, 1.00, 1.00, 1.00, 1.00,
  0.95, 1.00, 1.00, 1.00, 1.00, 0.95, 0.85, 0.80, 0.75, 0.70, 0.65, 0.65]`

`weekend` (skeleton crew + base processes):
`[0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.32, 0.35, 0.35, 0.35, 0.35, 0.35,
  0.35, 0.35, 0.35, 0.35, 0.35, 0.33, 0.32, 0.30, 0.30, 0.30, 0.30, 0.30]`

`shutdown` (flat technical minimum): all 24 values = `0.18`.

### 3.2 Seasonal factors by month (mild winter uplift — process heat + lighting)

| Month | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|-------|---|---|---|---|---|---|---|---|---|----|----|----|
| Factor | 1.06 | 1.05 | 1.02 | 1.00 | 0.98 | 0.96 | 0.95 | 0.95 | 0.98 | 1.01 | 1.04 | 1.05 |

### 3.3 Special windows (recur every year)

- Maintenance: the FIRST full Mon–Sun week of August (the first Monday of August through
  the following Sunday), `maintenance_factor = 0.60`.
- Christmas shutdown: Dec 24 through Jan 1 inclusive (spans year boundary; Jan 1 belongs
  to the following local year for normalization), treated as `shutdown` day_type with
  `shutdown_factor = 1.0` applied on top of the flat 0.18 shape (i.e., no double dampening).

## 4. Derived facts the rest of the project relies on

- LP-020: Peak share: fraction of annual volume in peak hours (Mon–Fri 08–20 local,
  non-holiday). With the parameters above this lands near ~0.42–0.48; the EXACT value is
  computed and written to the SSOT as `consumer_peak_share` (CALIBRATED) and reused by
  SPEC-05 §4.3. Never retype it manually.
- LP-021: Monthly volumes `volume_mwh(year, month)` are exported to
  `data/processed/consumer_load_monthly.parquet` (`year_local, month_local, volume_mwh`).

## 5. Sensitivity variant (cheap, mandatory)

- LP-030: A second profile `flat_baseload`: identical annual volume, identical calendar,
  all weights = 1.0 (pure baseload consumer). Built by the same function with
  `profile_name: flat_baseload` config. SPEC-05 recomputes the retrospective strategy
  matrix for this variant once, reported as a sensitivity table (shows the reader how much
  the load *shape* matters vs. the strategy choice).
- LP-034: Partial-year normalization rule (from LP-004) is unit-tested with a 6-month
  window fixture: monthly volumes must match the corresponding months of a full-year run.

## 6. `config/consumer_profile.yaml` (authoritative copy — create verbatim)

```yaml
profile_name: styriametal_v1
annual_consumption_mwh: 50000.0
timezone: Europe/Vienna
day_shapes:
  weekday: [0.65,0.65,0.65,0.65,0.65,0.75,0.95,1.00,1.00,1.00,1.00,1.00,
            0.95,1.00,1.00,1.00,1.00,0.95,0.85,0.80,0.75,0.70,0.65,0.65]
  weekend: [0.30,0.30,0.30,0.30,0.30,0.30,0.32,0.35,0.35,0.35,0.35,0.35,
            0.35,0.35,0.35,0.35,0.35,0.33,0.32,0.30,0.30,0.30,0.30,0.30]
  shutdown: [0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,
             0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18,0.18]
seasonal_factors: {1: 1.06, 2: 1.05, 3: 1.02, 4: 1.00, 5: 0.98, 6: 0.96,
                   7: 0.95, 8: 0.95, 9: 0.98, 10: 1.01, 11: 1.04, 12: 1.05}
maintenance:
  rule: first_full_week_august   # first Monday of August .. following Sunday
  factor: 0.60
christmas_shutdown:
  start: "12-24"
  end: "01-01"
```

## 7. Tests (golden + property)

- LP-040 Golden test: for local year 2023, after building with the exact config above,
  assert (a) annual sum = 50,000.00 ± 0.01 MWh; (b) the ratio
  `mean weekday-14:00 load ÷ mean Sunday-03:00 load` ∈ [2.8, 3.6]; (c) August total <
  July total; (d) December 25 hourly load = December 26 hourly load (both shutdown).
  Additionally, on first successful run, persist the sha256 of the 2023 slice
  (`tests/golden/consumer_load_2023.sha256`) and assert it thereafter (bit-stability).
- LP-041 Property tests: no negative loads; no NULLs; every hour of the calendar present
  exactly once; DST days sum to 23/25 hourly rows.
- LP-042: Changing any YAML value must break LP-040's checksum (meta-test: build with
  `annual_consumption_mwh: 50001` and assert checksum differs).

## 8. Honesty requirements

- LP-050: Every artifact (charts, tables, README) that uses consumer-load-derived numbers
  states: "Reference load profile is constructed (CALIBRATED), not measured; construction
  rules in SPEC-03." One sentence, verbatim allowed.
- LP-051: LIMITATIONS.md must include: real industrial RLM load data would change levels
  but not the ordinal ranking logic of strategies; the flat_baseload sensitivity (LP-030)
  bounds the shape effect.
