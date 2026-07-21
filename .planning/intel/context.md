# Synthesized Context (DOC)

## Specification gaps tracker (14_SPEC_GAPS)
- source: docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md

Tracks SPEC ambiguities and proposed resolutions. Proposals become binding only via ADR adoption (GV-201..203); status values: `proposed` → `adopted (ADR-NNN)` / `rejected`. Subordinate to Charter and SPEC-01..08 per project authority hierarchy.

### SG-01 (proposed)
- Gap: ING-009 mandates caching raw HTTP responses; ING-022 mandates `entsoe-py` whose PandasClient hides raw XML, resolution, curveType, currency fields.
- Proposed: Use `EntsoeRawClient` as URL-builder/transport; own Appendix-A parser owns §7 contracts; PandasClient never used for persistence. Chunk month-by-month.
- Adopt at: T1.02 ADR

### SG-02 (proposed)
- Gap: ING-042 "latest complete month" defined on "price data" — which zone(s)?
- Proposed: min(latest complete month of AT prices, of DE-LU prices).
- Adopt at: T1.08 ADR

### SG-03 (proposed)
- Gap: LP-020/ST-102: `consumer_peak_share` is a single SSOT value but peak share varies slightly per calendar year.
- Proposed: Compute per local year; publish reference-year 2019 value to SSOT; test max yearly deviation < 1 pp.
- Adopt at: T4.03 ADR

### SG-04 (proposed)
- Gap: "First full Mon–Sun week of August" edge when Aug 1 is a Monday.
- Proposed: first Monday m with m ≥ Aug 1; maintenance window = [m, m+6].
- Adopt at: T4.01 ADR

### SG-05 (proposed)
- Gap: `fct_price_hourly` column list says "+ all dim_calendar attributes" — enumerate.
- Proposed: ING-110 list + `season, hdd_18, cdd_22`; contract YAML is frozen enumeration.
- Adopt at: T3.04 (contract YAML review = adoption)

### SG-06 (proposed)
- Gap: M3 must build consumer/cost marts before M4/M6 produce parquet inputs.
- Proposed: Fixture bootstrap provides tiny stand-in parquet so `dbt build` is always green; real files replace stand-ins at M4/M6.
- Adopt at: T3.06 ADR

### SG-07 (proposed)
- Gap: ST-401 step 3 day-mapping algorithm unspecified.
- Proposed: Map by (day_index, hour_local); weekend-type fallback; DST forward-fill / reuse 02:00 rules.
- Adopt at: T6.07 ADR

### SG-08 (proposed)
- Gap: P95/CVaR numerical method unspecified.
- Proposed: `numpy.quantile(method="linear")`; CVaR95 = mean of `ceil(0.05·N)` highest annual costs.
- Adopt at: T6.07 ADR

### SG-09 (proposed)
- Gap: GV-303 "within rounding documented in the script" — define rule; SSOT `updated_at` vs determinism.
- Proposed: round_half_up match rule; `updated_at` = max(mtime) of input artifacts ISO-8601.
- Adopt at: T6.08/09 ADR

### SG-10 (proposed)
- Gap: `holidays` Styria subdivision code ("6" vs future rename).
- Proposed: Assert `subdiv="6"` in test at T2.01; ADR only on deviation.
- Adopt at: T2.01 (test = adoption)

### SG-11 (proposed)
- Gap: ING-082's 2025 range (40–140) may shift with SDAC 15-min.
- Proposed: Treat as binding gate; failure → evidence-backed ADR, never pre-emptive widening.
- Adopt at: only if triggered

### SG-12 (proposed)
- Gap: EXEC_SUMMARY hand-written but CI checks numbers — ordering.
- Proposed: SSOT generated first (M6); EXEC at M7 quoting SSOT; GV-303 from M6 CI onward.
- Adopt at: T7.03 (process note; no ADR needed)

### SG-13 (proposed)
- Gap: dbt default `generate_schema_name` prefixes target schema → `main_staging`, breaking DM-003.
- Proposed: Standard override macro returning custom schema literally.
- Adopt at: T3.01 ADR

### SG-14 (proposed)
- Gap: Charter glossary peak (Mon–Fri 08–20) omits holidays; ING-110 excludes them.
- Proposed: One internal definition everywhere: `is_peak_hour` (holiday-aware, ING-110); note ÖSPI convention in LIMITATIONS §2.
- Adopt at: T3.04 ADR + LIMITATIONS

### SG-15 (proposed)
- Gap: Calendar/profile forward-window end dynamic but calendar built at M2 before M1's `latest_complete_month`.
- Proposed: `build_calendar(end=...)`: explicit `--end` pre-M1; after M1 regenerate to `latest_complete_month + horizon + 1 month`; profile rebuilt after calendar.
- Adopt at: T2.01 ADR

### SG-16 (resolved — rationale)
- Gap: Raw-layer duplicates vs DM-020 staging dedup.
- Resolution: Both stand; staging dedup is defense-in-depth; no raw-layer dedup beyond monthly overwrite.

### SG-17 (resolved — spec-consistent)
- Gap: Generation `kind='consumption'` rows persisted but unused by marts.
- Resolution: Persist both kinds; `stg_gen_at_hourly` filters `aggregated` per spec.

### SG-18 (proposed)
- Gap: refresh.yml behavior when a month produces zero report changes.
- Proposed: Detect empty diff → skip PR creation, log in run summary.
- Adopt at: T7.05 (implementation detail; no ADR)

### Authority note
- source: user-confirmed ingest prompt
- PROJECT_CHARTER.md and docs/SPEC-01..08 are project authority.
- docs/EXECUTION_BLUEPRINT/ is subordinate to Charter and SPECs.
- docs/EXECUTION_BLUEPRINT/14_SPEC_GAPS.md proposals are non-binding unless adopted via ADR per GV-201..203.
