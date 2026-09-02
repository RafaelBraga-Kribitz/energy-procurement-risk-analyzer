# Phase 6: M5 Analytics - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning
**Mode:** Interactive discuss — spec-supremacy project. `docs/SPEC-04_analytics.md` (AN-xxx) locks *what* to build (A1–A4 artifacts, HMM/GARCH pins, AN-304 gate, §6 file list, AN-701..705). WBS §M5 (T5.01–T5.07) locks order **A1→A2→A4→A3**. This discussion captures the **operational / HOW decisions the spec leaves open** — mart vs synthetic tests, AN-304 in CI (fixture has no 2019), SSOT producer path, heatmap years with incomplete 2025, chart/LP-050 stamping, HMM thread pinning, and whether to commit PNGs without a real warehouse.

<domain>
## Phase Boundary

Build market-structure analytics answering Charter Q2 (REQ-ANA-01, REQ-Q2). One milestone.

- **Modules:** `src/epra/analytics/{descriptive,spread,weather,regimes}.py` — replace `NotImplementedError` stubs. Public pins in `docs/EXECUTION_BLUEPRINT/03_MODULES.md`: `annual_summary`, `spread_stats`, `fit_hmm` → `HmmFit`, `december_regime`, `fit_load_hdd`.
- **Inputs:** DuckDB **marts only** (`db.connect(..., read_only=True)`). Never `data/raw`, never staging. Degree-days come from `dim_calendar` (SPEC-04 §5); analytics never recompute HDD/CDD.
- **Outputs:** exactly the 12 SPEC-04 §6 files under `reports/analytics/` plus `data/processed/ssot_inputs_analytics.parquet` (VERIFIED rows). Chart style SPEC-06 §7 (RP-701..705) is mandatory.
- **Order:** A1 → A2 → A4 → A3 (regimes last). GARCH (T5.06) shares A3's `d_t` builder.
- **Gates:** AN-304 (hard), AN-701..705. Arithmetic diffs on base price, **not** log returns (T-3).
- **Honesty:** A4 must say the *reference consumer* profile is weather-invariant; system load is not. Do not invent prices, temperatures, or SSOT euros (A-2).

**Exit gate (SC):** (1) §6 artifacts exist and regenerate from `make analyze`; (2) AN-304 passes on real 2021–2023 data; (3) charts carry required notes/tags and captions obey SPEC-06 §7.

**Out of this phase:**
- Strategy simulator / `generate_ssot.py` markdown (M6 concatenates `ssot_inputs_*.parquet`).
- Executive charts, exports, Power BI, README euro headlines (M7).
- Fifth analytics block (Charter §4.2).
- Widening AN-304 without an ADR.
- TP.02 GitHub required-check; EN-072 consumer golden regen.
- Committing fixture-warehouse PNGs as if they were Austrian market evidence.

</domain>

<decisions>
## Implementation Decisions

### Mart access & shared kit (Area A — AN preamble, T5.01)
- **D-01:** `run(settings)` in each module reads **only** `marts.*` via `epra.common.db.connect(settings, read_only=True)`. Empty/missing mart → raise naming the SQL (03_MODULES failure mode). Pure computation functions take DataFrames so unit tests never need DuckDB.
- **D-02:** Shared writers live in `src/epra/analytics/_kit.py` (name pinned at plan time if a better module name is greppable): markdown table + AN-704 prose section, PNG save applying RP-701 figsize/dpi + RP-702 source note (`epra.report.style.SOURCE_NOTE`) + epistemic tag when CALIBRATED/SIMULATED, SSOT-row emitter. Charts are object-inspected in tests (title, axis units, source note), **not** image-diffed.
- **D-03:** SSOT producer file is `data/processed/ssot_inputs_analytics.parquet` with the same columns as the profile producer (`key, value, unit, tag, produced_by`). `tag="VERIFIED"`. Keys at minimum: `neg_hours_<year>` (AN-104), `spread_mean_<year>` (AN-202), `garch_persistence` (AN-303), and `annual_mean_price_<year>` (already named in the A1 stub docstring). `produced_by` is the module path (e.g. `epra.analytics.descriptive`). M6 concatenates; this phase does not write `NUMERIC_SSOT.md`.

### Operator interface (Area B — AN-701, EN-050)
- **D-04:** `python -m epra.analytics` runs **A1 → A2 → A4 → A3**. `make analyze` is that command only — **does not** invoke dbt. Missing warehouse → exit 1 with `make warehouse` hint. `all:` already has `analyze` after `transform`.
- **D-05:** Artifacts write to `settings.paths.reports / "analytics"`. Unit/CLI tests redirect via `tmp_settings`. Do **not** commit `reports/analytics/*` generated from the CI fixture warehouse (synthetic prices are not market evidence). Operator `make warehouse && make analyze` on real marts produces the DL-3 files; this cloud checkout has no `data/raw` backfill (A-2).

### AN-304 vs CI fixture window (Area C — AN-304, ADR-010)
- **D-06:** The CI/bootstrap warehouse is **2022–2024** (ADR-010) and **has no 2019**. AN-304's 2019-calm clause therefore **cannot** run honestly on fixtures. Implementation: `check_an304(...)` is a hard fail when the required local-date coverage exists; pytest **skips** (does not pass) when 2019 or 2021-09-01..2023-06-30 is incomplete; `make analyze` on a real warehouse **exits non-zero** if the gate fails. Do **not** extend the fixture to 2019 just to green a gate. Do **not** widen 70%/60%. Do **not** invent 2019 prices. Widening still requires an ADR (spec).

### Incomplete heatmap years (Area D — AN-102)
- **D-07:** AN-102 asks for **five panels 2021–2025**. If a year has no complete `year_local` in the marts, draw the panel with title `{year} — no complete data` and empty axes. Shared color scale from whatever years *are* present. Never synthesize a price heatmap (A-2).

### Duration-curve crisis styling (Area E — AN-103, AN-105)
- **D-08:** Plot one line per available year 2019→latest. Style **2022** as the crisis year (Okabe-Ito vermillion, higher zorder). Other years use other Okabe-Ito colors from `epra.report.style`. Prose (AN-105) must mention solar-driven midday depression in recent years, the 2022 crisis level, and what negative hours mean for a flexible consumer — **written in code as a checked template/constants**, not hand-typed into a committed markdown file with invented EUR figures. Numbers in the paragraph are formatted from the computed table (RP-703).

### HMM / GARCH determinism (Area F — AN-302, AN-303, AN-705, RB-11)
- **D-09:** `fit_hmm` uses spec pins exactly: `GaussianHMM(n_components=3, covariance_type="full", n_iter=500)`, restarts `random_state=42..51`, keep max log-likelihood; labels remapped by ascending state std → `calm`, `elevated`, `crisis`. Before fit, pin BLAS to one thread (`OMP_NUM_THREADS`/`MKL_NUM_THREADS`/`OPENBLAS_NUM_THREADS`/`NUMEXPR_NUM_THREADS` = `1`) so AN-705 is bit-stable. Tie-break: if two restarts share LL, keep the **lower** `random_state`. `HmmFit` frozen dataclass as 03_MODULES.
- **D-10:** `december_regime(year)` = majority HMM state among that December's days (03_MODULES pin; feeds ST-401 in M6). Implement in T5.05 with a synthetic test; M6 only consumes it.
- **D-11:** GARCH(1,1) constant mean on `d_t` via `arch`. Try unscaled first; if the optimizer warns about scale, divide `d_t` by 10, document the rescale in the GARCH artifact, still emit `garch_persistence` = α+β (VERIFIED). If α+β ≥ 1, report near-integrated — never clamp. Two-run persistence identity is the AC.
- **D-12:** Do **not** pre-write an HMM-platform ADR. If T5.05 AN-705 fails after thread pinning, stop (AGENTS: 2 focused attempts) — RB-11 last resort (commit regime parquet) needs a human-approved ADR-014.

### Chart tags & LP-050 (Area G — RP-702, LP-050, AN-402)
- **D-13:** A1–A3 charts show VERIFIED market series — RP-702 source note; epistemic tag **VERIFIED** (not CALIBRATED). A4 scatter is system load vs HDD (VERIFIED). A4 markdown **must** contain the weather-invariance sentence for the constructed consumer (AN-402). LP-050 verbatim sentence is required on artifacts that use *consumer-load-derived* numbers; A1–A3 do not use the StyriaMetal profile. Do not stamp CALIBRATED on ENTSO-E prices.

### ADR governance (Area H)
- **D-14:** No new ADR unless AN-304 fails on real data or HMM remains nondeterministic after D-09. Next free number is **ADR-014**. SPEC-04 pins are not "gaps" needing SG rows.

### Claude's Discretion
- Internal helpers under 03_MODULES names; functions ~60 lines (W-3); vectorized pandas/numpy.
- Whether `_kit.py` vs `analytics/io.py` — one shared module, no copy-paste writers.
- Heatmap implementation (imshow vs pcolormesh) provided shared scale + 5 panels.
- OLS formula API (`statsmodels.formula.api` vs `OLS`) as long as month FE + HC1.
- Whether `make analyze` deletes prior `reports/analytics/` before write (AN-701 "from a clean state") — planner should prefer wipe-then-write of the 12 known filenames only, not `rm -rf` the whole reports tree.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Binding spec (authority)
- `docs/SPEC-04_analytics.md` — whole file.
- `docs/SPEC-06_reporting_dashboard.md` §7 (RP-701..705).
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M5 T5.01–T5.07.
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` analytics section (function pins, HmmFit, december_regime).
- `docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md` §6.7 M5 row.
- `docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md` RB-11 (HMM/BLAS).
- Trap T-3: arithmetic diffs, never log returns.

### Upstream already shipped
- `epra.common.db.connect` read-only; `marts.fct_price_hourly` / `fct_price_daily` / `dim_calendar`.
- `epra.report.style` (FIGSIZE, DPI, SOURCE_NOTE, OKABE_ITO) and `epra.report.format`.
- `scripts/bootstrap_fixture_warehouse.py` 2022–2024 window (ADR-010) — not a 2019 source.
- Analytics stubs: `descriptive.run` / `spread.run` / `weather.run` / `regimes.run`.
- `hmmlearn` and `arch` already pinned in `pyproject.toml`.

### Governance
- Charter Q2 / REQ-ANA-01 / REQ-Q2.
- A-2 no invented market facts; A-3 no fifth module; A-4 determinism.
- AN-304 widening = ADR; golden/HMM parquet commit = human.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Four analytics modules are loud stubs (`NotImplementedError` matching `test_stubs_fail_loudly.py` M5 rows). Delete those stub rows in the commit that un-stubs each `run()`.
- Warehouse report still flags `fct_procurement_cost_monthly` as M6 stand-in — leave it.
- `tmp_settings` already redirects `reports` and `warehouse`.
- Chart constants exist; analytics must **call** them, not duplicate hex colors.

### Established Patterns
- `python -m epra.<module>` + Makefile target (calendar, profile, warehouse.report).
- SSOT producer parquet (`ssot_inputs_profile.parquet`) — copy schema, not path.
- Isolated `--data-root` bootstrap + `dbt build` for warehouse-backed checks.
- Docstrings `Implements: AN-xxx`.

### Integration Points
- New: `_kit.py`, `epra.analytics.__main__`, tests per module, `ssot_inputs_analytics.parquet` writer.
- Modified: four analytics modules, Makefile `analyze:`, stub tests, BUILD_LOG.
- Unchanged: dbt models, consumer profile, strategy stubs, SPEC-04 text, fixture window years.

</code_context>

<specifics>
## Specific Ideas

- **AN-704:** test finds ≥400 characters of prose after the last markdown table in each `.md` artifact.
- **AN-101 columns:** mean/median/std/min/max hourly, base, peak, off-peak, peak−off-peak spread, negative-hour count + share, hours > 500 EUR/MWh — per `year_local`.
- **A4 OLS:** daily mean AT load (MW) vs `hdd_18`, weekend color, month FE, HC1; assert HDD coefficient **positive** (load rises with heating demand) on synthetic linear data and on real data when present.
- **`d_t`:** daily `price_base_eur_mwh` first difference; drop the first day; do not log.
- **AN-701:** existence of the 12 filenames after `run` from a wiped analytics output dir.

</specifics>

<deferred>
## Deferred Ideas

- `generate_ssot.py` / `NUMERIC_SSOT.md` concatenation — M6.
- Executive charts / README euros — M7.
- `december_regime` **consumers** (ST-401 no-crisis variant) — M6; the function itself is T5.05.
- Power BI / refresh.yml — M7.
- TP.02, EN-072 — still human.
- Committing real `reports/analytics/` PNGs — operator machine with a real warehouse (same class as M3's committed dbt_build report).

</deferred>
