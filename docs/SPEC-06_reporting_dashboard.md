# SPEC-06 — Reporting, Dashboard, README

Turns computed results into artifacts the primary audience (Austrian business readers)
actually consumes. Requirement IDs: `RP-xxx`.

---

## 1. Artifact inventory

| Artifact | Path | Produced by |
|----------|------|-------------|
| Executive summary | `reports/EXEC_SUMMARY.md` | hand-written, numbers from SSOT only |
| Executive charts | `reports/executive_charts/*.png` | `make report` |
| Numeric SSOT | `reports/NUMERIC_SSOT.md` | `scripts/generate_ssot.py` |
| BI exports | `exports/*.csv` | `scripts/export_marts.py` |
| Power BI file | `dashboards/epra.pbix` | manual build on exports (human task) |
| Dashboard screenshots | `docs/assets/dashboard_*.png` | manual |
| README | `README.md` | hand-written per §6 |
| Limitations | `LIMITATIONS.md` | hand-written per SPEC-08 §6 |

## 2. Executive charts (exactly these four, in `reports/executive_charts/`)

- RP-201 `01_wrong_strategy_cost.png` — THE money chart. Bar per year 2021–2025: cost gap
  between worst and best strategy (EUR, millions), annotated with the worst strategy's
  name. Title: "What the wrong electricity procurement strategy cost a 50 GWh Styrian
  manufacturer". Subtitle carries the CALIBRATED tag sentence (LP-050).
- RP-202 `02_annual_costs_by_strategy.png` — grouped bars (reuse ST-304 #1 styling).
- RP-203 `03_forward_risk.png` — reuse `s5_forward_fan.png` content, executive styling.
- RP-204 `04_market_context.png` — AT monthly base price line 2019→latest with regime
  bands (A3) and ÖSPI overlay, indexed right axis.

## 3. Chart data flow

- RP-301: Executive charts read ONLY marts/SSOT-backed dataframes; every number visible
  on a chart must be reproducible from `exports/` CSVs (a reviewer test: recompute chart
  #1's bar values from `strategy_annual_summary.csv` — a pytest does exactly this).

## 4. Power BI dashboard (manual step, precisely specified)

Data source: the six CSVs in `exports/` (DM-070). Relationships: `procurement_cost_monthly`
↔ `dim strategy` (import dim from the CSV column pairs), date table built in Power BI from
`price_monthly`. Four report pages:

- RP-401 Page 1 "Headline": card visuals — 5-year wrong-strategy cost (EUR), best
  strategy 2021–2025, P95 next-12-months for S1 vs S3; bar chart = RP-201 equivalent.
- RP-402 Page 2 "Market": monthly base/peak price lines, negative-hours column chart,
  AT–DE spread line; year slicer.
- RP-403 Page 3 "Strategies": annual cost matrix (matrix visual, strategy × year,
  conditional formatting), cumulative cost line, unit-cost table.
- RP-404 Page 4 "Risk": forward distribution visual (box or percentile lines from
  `forward_risk_summary.csv`), mean-vs-P95 scatter, note block with SIMULATED tag text.
- RP-405: German subtitle line on each page (one sentence) — signals AT-market fluency.
- RP-406: Screenshots of all four pages → `docs/assets/dashboard_p1.png` … `p4.png`,
  embedded in README. The `.pbix` is committed (small; CSVs re-linkable via relative
  paths documented in `dashboards/README.md`).

## 5. `reports/EXEC_SUMMARY.md` (≤ 2 pages, structure mandatory)

1. **The answer** (3 sentences max): the 5-year wrong-strategy cost in EUR; which strategy
   won 2021–2025; what it costs to insure via fixed/hybrid going forward (P95 deltas).
2. **How to read this** (1 short paragraph): CALIBRATED consumer, VERIFIED prices,
   SIMULATED risk — one sentence each.
3. **The market you are buying in** (1 paragraph + RP-204 chart reference).
4. **Strategy comparison** (table from SSOT + 1 paragraph).
5. **Forward risk & recommendation** (Q4): one paragraph naming the recommendation for a
   cost-minimizing CFO and for a risk-averse CFO, each with its euro trade-off, sourced
   from ST-404. No hedging language like "it depends" without a number attached.
6. **What would change this analysis** (3 bullets max, from LIMITATIONS).

## 6. README.md structure (order mandatory)

1. H1 + one-sentence project definition containing "Austrian day-ahead market (ENTSO-E)"
   and "50 GWh Styrian industrial consumer".
2. The headline question as a blockquote, then the answer paragraph with the top-3 SSOT
   numbers (each with epistemic tag).
3. RP-201 chart embedded.
4. "What is real vs. modeled" table (VERIFIED / CALIBRATED / SIMULATED, one row each).
5. Results tables (annual matrix + forward risk).
6. Dashboard screenshots.
7. How to reproduce (5 commands max: clone, token, `make setup`, `make backfill`,
   `make all`).
8. Architecture sketch (one diagram or ASCII: ingest → DuckDB/dbt → analytics/strategies
   → SSOT/exports → Power BI).
9. Data sources with links; limitations link; license; author block (same format as
   prior repos).
- RP-601: The README contains NO number that is absent from `NUMERIC_SSOT.md` (CI-checked,
  SPEC-08 §4). The README does NOT lead with tooling. Stack names appear first in §8 of
  the README, not before.

## 7. Chart standards (apply to every PNG in the repo)

- RP-701: matplotlib ≥ 3.8, default backend Agg; figure size 12×6 in, dpi 150; no
  seaborn dependency for exec charts (keep style deterministic).
- RP-702: Every chart has: title (plain English business phrasing), axis labels WITH
  units, source note bottom-left ("Source: ENTSO-E Transparency / AEA ÖSPI / own
  calculations"), epistemic tag bottom-right when CALIBRATED/SIMULATED data is shown.
- RP-703: Euro formatting: thousands separator, "€1.42 M" style for millions, EUR/MWh
  with 1 decimal. One shared formatter module `src/epra/report/format.py` — tested.
- RP-704: Color constants defined once in `src/epra/report/style.py`; strategies keep
  the same color across ALL charts (S1 red family, S3 blue family, hybrids interpolated,
  S2 orange). Colorblind-safe palette (Okabe-Ito).
- RP-705: German date/number conventions are NOT used inside charts (English, dot
  decimal) — consistency with CSV exports; German appears only in Power BI subtitles
  (RP-405).
