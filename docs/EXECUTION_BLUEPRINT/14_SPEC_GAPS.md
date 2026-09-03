# 14 — SPECIFICATION GAPS & AMBIGUITY RESOLUTIONS

Every place a SPEC leaves interpretation room, contradicts itself, or omits a
needed decision. Each entry proposes a decision; a proposal becomes **binding
only via ADR** (GV-201..203) merged in the implementing PR — never by silent
adoption. Status values: `proposed` → `adopted (ADR-NNN)` / `rejected`.

| ID | Gap / ambiguity | Affected REQ | Proposed decision | Adopt at | Status |
|----|-----------------|--------------|-------------------|----------|--------|
| SG-01 | ING-009 mandates caching **raw HTTP responses**, but ING-022 mandates `entsoe-py`, whose PandasClient hides raw XML, resolution, curveType, currency fields | ING-009, ING-022, ING-050, ING-060 | Use `EntsoeRawClient` as URL-builder/transport (still "entsoe-py" per ING-022); own Appendix-A parser owns the §7 contracts; PandasClient never used for persistence. Chunk month-by-month (90-day bound trivially satisfied; leap-quarter edge avoided) | T1.02 ADR | adopted (ADR-003) |
| SG-02 | ING-042 "latest complete month" defined on "price data" — which zone(s)? | ING-042 | min(latest complete month of AT prices, of DE-LU prices) — spread analysis (AN-2xx) needs both; load/gen completeness checked by gates but not part of this definition | T1.08 ADR | adopted (ADR-005) |
| SG-03 | LP-020/ST-102: `consumer_peak_share` is a single SSOT value but peak share varies slightly per calendar year | LP-020, ST-102 | Compute per local year; publish the **reference-year 2019** value to SSOT (consistent with all other anchors); add test asserting max yearly deviation < 1 pp, else escalate | T4.03 ADR | adopted (ADR-013) |
| SG-04 | "First full Mon–Sun week of August": edge when Aug 1 is a Monday; "full week within August"? | LP §3.3 | first Monday m with m ≥ Aug 1; maintenance window = [m, m+6]. If Aug 1 is Monday → Aug 1–7. (m ≤ Aug 7 always ⇒ window ends ≤ Aug 13, always inside August) | T4.01 ADR | adopted (ADR-012) |
| SG-05 | `fct_price_hourly` column list says "+ all dim_calendar attributes" — enumerate | SPEC-02 §5 | Exactly: ING-110 list (`date_local, year_local, month_local, hour_local, dow_local, is_weekend, is_holiday_at, is_peak_hour`) + `season, hdd_18, cdd_22`; contract YAML is the frozen enumeration | T3.04 (contract YAML review = adoption) | proposed |
| SG-06 | M3 must build `fct_consumer_load_hourly`/`fct_procurement_cost_monthly` before M4/M6 produce their parquet inputs | SPEC-02 §5, Charter §7 order | Fixture bootstrap provides tiny stand-in parquet so `dbt build` is always green; real files replace stand-ins locally at M4/M6. No model disabling, no build-order forks | T3.06 ADR | proposed |
| SG-07 | ST-401 step 3 day-mapping: "reuse the drawn month's last same-weekday-type day" — precise algorithm | ST-401 | Map by (day_index, hour_local). Target day d > drawn month length: use drawn month's last day whose `is_weekend` equals target day's; DST-missing hour: forward-fill from previous local hour; DST-extra hour: reuse drawn 02:00 value. Deterministic, documented in module docstring | T6.07 ADR | adopted (ADR-014) |
| SG-08 | P95/CVaR numerical method unspecified | ST-403 | P-quantiles: `numpy.quantile(method="linear")`; CVaR95 = mean of the `ceil(0.05·N)` highest annual costs (N=2000 → 100 paths). Pin in one `summarize()` function | T6.07 ADR | adopted (ADR-015) |
| SG-09 | GV-303 "within rounding documented in the script" — define the rule; SSOT `updated_at` vs determinism | GV-301, GV-303, ST-405 | Match rule: README literal with d displayed decimals matches SSOT value iff |literal − round_half_up(value, d)| = 0. `updated_at` = max(mtime) of input artifacts rendered ISO-8601 — reruns without input changes leave the file byte-identical | T6.08/09 ADR | proposed |
| SG-10 | `holidays` Styria subdivision code ("6" vs future rename) | ING-110 | Assert working code in a test at T2.01; expected `subdiv="6"`; deviation → ADR documenting the package's current code | T2.01 (test = adoption; ADR only on deviation) | proposed |
| SG-11 | ING-082's 2025 range (40–140) set at charter time; SDAC 15-min may shift statistics | ING-082, R-8 | Treat as binding gate; failure follows guide §5.1 protocol ending in evidence-backed ADR — never a pre-emptive widening | only if triggered | proposed |
| SG-12 | EXEC_SUMMARY is hand-written but CI checks numbers — ordering of writing vs generation | RP §5, GV-303 | SSOT generated first (M6); EXEC written at M7 quoting SSOT; GV-303 runs on both docs from the M6 CI job onward (README until M7 contains no result numerals — current state satisfies this) | T7.03 (no ADR needed; process note) | proposed |
| SG-13 | dbt default `generate_schema_name` prefixes target schema → schemas would be `main_staging`, breaking DM-003 naming | DM-003 | Standard override macro returning the custom schema literally; committed at T3.01 | T3.01 ADR | proposed |
| SG-14 | Peak definition: Charter glossary (Mon–Fri 08–20) omits holidays; ING-110 excludes them. Which applies to `price_peak_eur_mwh` and anchors? | glossary, ING-110, DM §5, ST-202 | One internal definition everywhere: `is_peak_hour` (holiday-aware, ING-110). Note in LIMITATIONS §2 that ÖSPI's own peak convention may treat holidays differently; anchor ratios absorb level offsets by construction | T3.04 ADR + LIMITATIONS | proposed |
| SG-15 | Calendar/profile forward-window end is dynamic (latest month + 12) but calendar is built at M2 before M1's `latest_complete_month` exists | ING-110, LP-003, ST-401 | `build_calendar(end=...)`: explicit `--end` pre-M1; after M1, `make ingest` regenerates calendar to `latest_complete_month + horizon + 1 month` margin. Profile always rebuilt after calendar (Make dependency order) | T2.01 ADR | proposed |
| SG-16 | Raw-layer duplicates: ING-003 atomic overwrite makes dupes near-impossible, yet DM-020 dedups in staging | ING-003, DM-020 | Both stand: staging dedup is defense-in-depth with a warn-count test; no raw-layer dedup logic beyond monthly overwrite. No action needed — rationale recorded here | — | resolved (rationale) |
| SG-17 | Generation `kind='consumption'` rows: persisted but unused by marts | ING-032, DM §3 | Persist both kinds (raw is raw); `stg_gen_at_hourly` filters `aggregated` (already in spec). No SSOT value derives from consumption rows | — | resolved (spec-consistent) |
| SG-18 | refresh.yml behavior when a month produces zero report changes | EN-082 | Detect empty diff → skip PR creation, log in run summary. Avoids noise PRs | T7.05 (implementation detail; no ADR) | proposed |

**Contradictions found:** none that survive close reading — the two apparent
ones (SG-01 cache-vs-library, SG-14 peak definitions) are resolvable without
violating any REQ's output contract, which is exactly what A-1 requires.

**Missing specifications identified:** numerical method pins (SG-08), schema
enumeration (SG-05), dynamic-window mechanics (SG-15) — all now covered above.
Anything newly discovered during implementation gets an SG row **before** code
is written against an interpretation (session protocol §0.8).
