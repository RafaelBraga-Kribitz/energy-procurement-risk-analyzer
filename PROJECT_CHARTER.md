# PROJECT CHARTER — Energy Procurement Risk Analyzer (EPRA)

**Repo name:** `energy-procurement-risk-analyzer`
**Author:** Rafael Braga-Kribitz, Seiersberg-Pirka, Austria
**Status:** Charter v1.0 — 2026-07-18
**Authority:** This document is the Single Source of Truth for goals, scope, and acceptance.
Where any other document conflicts with this Charter, the Charter wins. Where this Charter
is silent, the relevant SPEC document wins. Changes to this Charter require an ADR
(see `docs/SPEC-08_governance_quality.md`).

---

## 1. The business problem (read this first)

After the 2021–2023 European energy crisis, electricity procurement stopped being a
back-office task for Austrian industry and became a board-level risk. A mid-size Styrian
manufacturer consuming ~50 GWh/year faces a difference of **millions of euros** between
procurement strategies (full spot exposure vs. indexed contract vs. fixed annual price vs.
partial hedge) — yet most Mittelstand companies still decide this by gut feeling or by
whatever their supplier offers.

**Headline question (the project exists to answer exactly this):**

> *How much did buying electricity the wrong way cost a 50 GWh/year Styrian manufacturer
> in 2021–2025 — and what is the P95 cost exposure for the next 12 months under each
> procurement strategy?*

Everything in this repository serves that sentence. Any work that does not serve it is
out of scope.

### 1.1 The four analytical questions (Q1–Q4)

| ID | Question | Answered by |
|----|----------|-------------|
| Q1 | What did each procurement strategy actually cost, per calendar year 2021–2025, in EUR and EUR/MWh, for the reference consumer? | SPEC-05 retrospective engine |
| Q2 | What structural features of the Austrian day-ahead market drive that difference (seasonality, hour-of-day shape, negative price hours, volatility regimes, AT–DE spread)? | SPEC-04 analytics |
| Q3 | What is the distribution of next-12-month procurement cost per strategy (mean, P5, P50, P95, CVaR95)? | SPEC-05 forward risk engine |
| Q4 | Which strategy would a risk-averse vs. a cost-minimizing CFO choose, and what is the price of that risk reduction in EUR? | SPEC-05 + SPEC-06 executive report |

### 1.2 The audience

1. **Primary:** hiring managers and senior analysts at Austrian energy companies
   (Energie Steiermark, Energie Graz, Verbund, Wien Energie, EVN), industrial procurement
   teams (voestalpine, Andritz, AVL, Magna), and consultancies with energy practices.
2. **Secondary:** any technical reviewer opening the GitHub repo.

The primary audience reads business documents first. Therefore: every headline output is
denominated in **euros**, and the README leads with the answer, not the stack.

---

## 2. The reference consumer ("StyriaMetal GmbH")

A fictional but rigorously constructed reference consumer. It is **CALIBRATED**, not
measured (see epistemic framework, §5). Its full construction is micro-specified in
`docs/SPEC-03_consumer_load_profile.md`. Summary:

| Attribute | Value | Rationale |
|----------|-------|-----------|
| Sector | Metal processing (Styrian archetype) | Region-credible, energy-intensive |
| Annual consumption | 50,000 MWh (50 GWh) per calendar year, exact after normalization | Mid-size industrial; large enough that strategy deltas are material |
| Operating pattern | 3-shift Mon–Fri, reduced weekend load, August maintenance week, Christmas shutdown | Defined precisely in SPEC-03 |
| Grid situation | Consumer buys energy only; grid fees, taxes, levies are **out of scope** | Isolates the procurement decision (the only lever being analyzed) |
| Load profile resolution | Hourly, deterministic given config + calendar | Reproducibility |

**Hard rule:** the load profile parameters live in ONE file
(`config/consumer_profile.yaml`) and are never hardcoded anywhere else.

---

## 3. Data sources (all real; no synthetic market data — ever)

| # | Source | What | Access | Epistemic tag |
|---|--------|------|--------|---------------|
| D1 | ENTSO-E Transparency Platform REST API | AT day-ahead prices (hourly / 15-min), AT actual load, AT generation per type, DE-LU day-ahead prices | Free API token (registration required) | VERIFIED |
| D2 | Austrian Energy Agency — ÖSPI (Österreichischer Strompreisindex) | Monthly wholesale price index (Base + Peak), since 2006 | Public PDF, transcribed to a hand-curated CSV with double-entry validation | VERIFIED (values) |
| D3 | GeoSphere Austria Data Hub API | Daily mean temperature, Graz station | Free, no auth | VERIFIED |
| D4 | `holidays` Python package | Austrian national + Styrian holidays | pip | VERIFIED |
| D5 | Consumer load profile | Constructed per SPEC-03 | Generated | CALIBRATED |

**Prohibitions (non-negotiable):**

- P-1: No synthetic prices. If a price cell cannot be filled from D1/D2, it stays NULL and
  the affected period is excluded with a documented note.
- P-2: No scraping of paywalled sources (EEX futures etc.). Forward prices are proxied via
  ÖSPI per SPEC-05, with the approximation documented in `LIMITATIONS.md`.
- P-3: No manual edits to raw data files. Corrections happen in staging with a documented rule.

---

## 4. Scope

### 4.1 In scope

1. Ingestion pipelines for D1–D4 with retries, caching, validation (SPEC-01).
2. A DuckDB + dbt analytical warehouse with staging and mart layers, tested (SPEC-02).
3. Deterministic consumer load profile module (SPEC-03).
4. Market analytics: descriptive statistics, seasonality, negative-price analysis, AT–DE
   spread, volatility regime detection (SPEC-04).
5. Procurement strategy simulator: retrospective 2021–2025 cost per strategy + forward
   12-month cost distribution via block bootstrap (SPEC-05).
6. Reporting: executive summary, executive charts, Power BI dashboard from exported marts,
   auto-generated `reports/NUMERIC_SSOT.md` (SPEC-06).
7. Engineering: uv-managed Python 3.12 project, Makefile, pytest, ruff, pre-commit,
   GitHub Actions CI + monthly data-refresh cron (SPEC-07).
8. Light governance: epistemic tags, SSOT numeric table gated by CI, append-only ADRs,
   `LIMITATIONS.md` (SPEC-08).

### 4.2 Explicitly OUT of scope (do not build these, even if tempting)

- O-1: Price *forecasting* models. This project evaluates strategies against **realized**
  prices and bootstrap resampling of realized prices. No claim of forecast skill is made.
- O-2: Intraday, balancing, or futures market microstructure.
- O-3: Grid fees, taxes, levies, PPAs, on-site generation, battery optimization, demand
  response. (Each may be listed under "future work" in the README; none is built.)
- O-4: A FastAPI service, Streamlit app, or any hosted backend. The interactive deliverable
  is Power BI on exported CSVs. (The previous portfolio projects already prove app-building.)
- O-5: Heavy governance machinery (audit-finding registry, session handouts, agent gate
  ceremony beyond what SPEC-08 defines). Governance weight is capped at ~30% of the
  `decision-analytics-reconstruction` repo, by design.
- O-6: Gas, heat, or any commodity other than electricity.
- O-7: More than the 4 strategy families defined in SPEC-05.

### 4.3 Analysis window

- Prices/load/generation: **2019-01-01 → latest complete month** (AT–DE bidding zone split
  became effective 2018-10-01; 2019 is the first clean full year).
- Retrospective strategy comparison: calendar years **2021, 2022, 2023, 2024, 2025**.
- Reference/calibration year for contract pricing: **2019** (pre-crisis; defined in SPEC-05).
- Forward risk window: **the 12 calendar months following the latest complete data month.**

---

## 5. Epistemic framework (carried over from prior portfolio work, simplified)

Every published number carries exactly one tag:

| Tag | Meaning | Examples |
|-----|---------|----------|
| VERIFIED | Directly computed from real external data with no modeling assumptions beyond unit conversion/aggregation | Annual mean spot price; negative price hour counts; AT–DE spread |
| CALIBRATED | Derived using documented assumptions anchored to real data | Consumer load profile; ÖSPI→EUR/MWh translation; fixed-price proxy |
| SIMULATED | Output of a stochastic procedure with a fixed seed | Bootstrap cost distributions, P95, CVaR95 |

Rules:

- E-1: The README and executive summary must state the tag next to every headline number.
- E-2: A VERIFIED number may never depend on a CALIBRATED input. (Strategy costs are
  therefore CALIBRATED, because they use the CALIBRATED load profile — this is correct
  and must be stated.)
- E-3: `reports/NUMERIC_SSOT.md` is auto-generated by `scripts/generate_ssot.py` and is
  the only permitted source for numbers quoted in README/exec summary. CI fails if a
  quoted number is not in the SSOT (see SPEC-08 §4).

---

## 6. Deliverables & Definition of Done

The project is DONE when all of the following are true:

| # | Deliverable | Acceptance criterion |
|---|-------------|----------------------|
| DL-1 | Reproducible pipeline | Fresh clone + `make setup && make all` (with `ENTSOE_API_TOKEN` set) completes without manual intervention and produces every artifact below |
| DL-2 | Answer to Q1 | `reports/NUMERIC_SSOT.md` contains the 5-year × 4-strategy cost matrix in EUR and EUR/MWh, and the "cost of the wrong strategy" headline (max − min per year) |
| DL-3 | Answer to Q2 | `reports/analytics/` contains the artifacts enumerated in SPEC-04 §6, each passing its plausibility gate |
| DL-4 | Answer to Q3 | SSOT contains the forward-risk table (mean/P5/P50/P95/CVaR95 per strategy), seed-reproducible |
| DL-5 | Answer to Q4 | `reports/EXEC_SUMMARY.md` (≤ 2 pages) delivers the CFO recommendation per SPEC-06 §5 |
| DL-6 | Dashboard | Power BI file `dashboards/epra.pbix` built on `exports/` CSVs, pages per SPEC-06 §4, plus screenshots committed under `docs/assets/` |
| DL-7 | Quality | `make test` green; dbt tests green; ruff clean; CI green on main; test coverage of `src/` ≥ 80% lines |
| DL-8 | Refresh | Monthly GitHub Actions cron ingests the latest month and rebuilds marts + SSOT without human action |
| DL-9 | Honesty | `LIMITATIONS.md` covers at minimum the items in SPEC-08 §6 |
| DL-10 | README | Leads with the euro answer; structured per SPEC-06 §6; all numbers traceable to SSOT |

---

## 7. Milestones (build order is mandatory; see AGENTS.md for gates)

| Milestone | Content | Exit gate (all must pass) |
|-----------|---------|---------------------------|
| M0 | Repo bootstrap: uv project, layout per SPEC-07 §2, Makefile skeleton, ruff/pre-commit, pytest smoke test, CI workflow | `make setup && make test && make lint` green locally and in CI |
| M1 | ENTSO-E ingestion (prices AT + DE-LU, load AT, generation AT) with caching, retry, validation | SPEC-01 §8 validation suite passes; row-count and plausibility gates green for 2019→latest |
| M2 | Auxiliary data: GeoSphere daily temperature, ÖSPI manual CSV (double-entry validated), calendar/holidays | SPEC-01 §§9–11 gates green |
| M3 | dbt project on DuckDB: staging + marts + tests | `dbt build` green; mart schemas match SPEC-02 §5 exactly |
| M4 | Consumer load profile module | Deterministic golden test (SPEC-03 §7) passes; annual sum = 50,000.00 MWh ± 0.01 |
| M5 | Analytics A1–A4 + chart generation | SPEC-04 §7 gates pass (incl. crisis-regime sanity gate) |
| M6 | Strategy simulator: retrospective + forward risk + SSOT generator | SPEC-05 §9 gates pass; golden metrics test green |
| M7 | Reporting: exports, Power BI, EXEC_SUMMARY, README, LIMITATIONS, refresh cron live | DL-1…DL-10 all green |

Effort budget (guidance, not a gate): M0 ≈ 0.5 day, M1 ≈ 2 days, M2 ≈ 1 day, M3 ≈ 1.5 days,
M4 ≈ 0.5 day, M5 ≈ 2 days, M6 ≈ 2 days, M7 ≈ 2 days. If any milestone exceeds 2× its
budget, stop and write an ADR describing the blocker before continuing.

---

## 8. Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | ENTSO-E API token approval delays | Medium | Blocks M1 | Request token on day 0 (SPEC-01 §2). Until it arrives, build M0 and M2 |
| R-2 | Day-ahead market moved to 15-min MTU (SDAC, from late 2025); mixed PT60M/PT15M resolutions in responses | High | Parser breakage / silent unit errors | SPEC-01 §6 mandates resolution-aware parsing and a canonical hourly layer; tests include a 15-min fixture |
| R-3 | ENTSO-E omits repeated points under curveType A03 | Medium | Silent gaps | SPEC-01 §6.4 forward-fill rule + gap accounting test |
| R-4 | ÖSPI transcription errors | Medium | Wrong contract prices | Double-entry procedure + plausibility gates (SPEC-01 §10) |
| R-5 | ÖSPI-as-forward-proxy is an approximation of real fixed-price offers | Certain | Interpretation risk | Not a bug — a documented modeling choice. Stated in LIMITATIONS.md and in every strategy output caption |
| R-6 | Scope creep toward forecasting / apps / more strategies | High | Project never ships | §4.2 prohibitions; AGENTS.md rule A-3 |
| R-7 | GeoSphere station ID or dataset naming differs from spec | Low | Small rework | SPEC-01 §9 includes a discovery procedure, not just a hardcoded ID |
| R-8 | 2025 contains data-quality anomalies unknown at charter time | Medium | Gates fail incorrectly | Plausibility gates use ranges; out-of-range triggers investigation, not automatic “fix” |

---

## 9. Document map (read order for builders)

| Order | File | Contents |
|-------|------|----------|
| 1 | `PROJECT_CHARTER.md` | This file. Goals, scope, acceptance |
| 2 | `AGENTS.md` | How AI agents must build this project: rules, gates, workflow |
| 3 | `docs/SPEC-01_data_ingestion.md` | Every API call, parameter, retry rule, storage path, validation gate |
| 4 | `docs/SPEC-02_data_model.md` | DuckDB/dbt layers, every table, every column, every test |
| 5 | `docs/SPEC-03_consumer_load_profile.md` | Exact load profile construction algorithm + golden values |
| 6 | `docs/SPEC-04_analytics.md` | Analytics modules A1–A4: formulas, outputs, plausibility gates |
| 7 | `docs/SPEC-05_strategy_simulator.md` | Strategy definitions S1–S4, all cost formulas, bootstrap algorithm, risk metrics |
| 8 | `docs/SPEC-06_reporting_dashboard.md` | Exports, Power BI pages, exec summary, README structure, chart standards |
| 9 | `docs/SPEC-07_engineering.md` | Repo layout, dependencies (pinned), Makefile, config, logging, CI/CD |
| 10 | `docs/SPEC-08_governance_quality.md` | Epistemic tags, SSOT mechanism, ADRs, LIMITATIONS.md, testing policy |

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| Day-ahead price | Hourly (or 15-min) price from the coupled European day-ahead auction for the AT bidding zone, EUR/MWh |
| Baseload (Base) | Average across all hours of a period |
| Peakload (Peak) | Average across peak hours: Mon–Fri 08:00–20:00 **Europe/Vienna local time** |
| MTU | Market Time Unit — 60 min historically, 15 min after SDAC switch |
| ÖSPI | Österreichischer Strompreisindex, monthly wholesale index (Base/Peak), base 2006 = 100, published by the Austrian Energy Agency |
| SDAC | Single Day-Ahead Coupling (European market coupling) |
| HDD/CDD | Heating/Cooling Degree Days, base 18 °C / 22 °C variant defined in SPEC-04 §5 |
| VaR / CVaR | Value at Risk (quantile of the cost distribution) / Conditional VaR (mean beyond the quantile). Costs, not returns: higher = worse |
| P_ref | Reference energy price anchoring ÖSPI translation, defined in SPEC-05 §4.2 |
| SSOT | Single Source of Truth — `reports/NUMERIC_SSOT.md` |

---

## 11. Charter change log

| Date | Version | Change |
|------|---------|--------|
| 2026-07-18 | 1.0 | Initial charter |
