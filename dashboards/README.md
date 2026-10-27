# Power BI dashboard: PBIP project and HTML twin (SPEC-06 §4, ADR-020 §4, ADR-022)

**Status:** the report is built as a Power BI Project in text form
(`EPRA.pbip`). Every JSON file passes Microsoft's PBIR schemas, and the model ↔
report integrity test passes. Two steps are still human work (AGENTS.md §2
item 5), and both wait for the real-data run:

- opening the project in Power BI Desktop, refreshing it and checking it;
- the RP-406 screenshots.

A static HTML twin of the same five pages is generated from the same CSVs
(`make dashboard-html`).

| Path | What it is |
|---|---|
| `EPRA.pbip` | Open this in Power BI Desktop |
| `EPRA.SemanticModel/` | Semantic model in TMDL: 13 tables, 10 relationships, 40 documented measures |
| `EPRA.Report/` | Report in PBIR: five pages, one JSON file per visual, the theme registered under `StaticResources/` |
| `measures.dax` | Readable mirror of every measure (kept identical to the TMDL by a test) |
| `theme.json` | Report theme: design-system (v2.1, bk-viz) strategy colours identical to the PNG charts (RP-704, tested) |
| `html/index.html` | Generated HTML twin (git-ignored until a real-data build, see §6) |
| `README.md` (this file) | How to open, refresh and check the report; model; page layout; screenshot checklist |

Power BI reads **only** `exports/*.csv` (DM-070), never DuckDB, so anyone can
rebuild the report without the warehouse: `make all` (or `make export` after a
run) writes the CSVs.

> If `exports/provenance.csv` says `is_fixture = True`, the CSVs come from the
> synthetic CI fixture (ADR-018). On fixture data, the `Data Banner` card turns
> red and says so, and the HTML twin shows a sticky FIXTURE banner. Build and
> screenshot the dashboard only on a real-data run.

## 0. Open in Power BI Desktop (checklist)

1. Run the pipeline so that `exports/` holds the CSVs:
   - on real data: `make real-run` (see `docs/REAL_DATA_RUN.md`);
   - to try it offline:
     `uv run python scripts/bootstrap_fixture_warehouse.py --force && make all`.
     The data is then FIXTURE data.
2. Use a current Power BI Desktop (PBIR is its default report format). If your
   version is older, first turn on these three preview features (*File →
   Options → Preview features*), then restart:
   - *Power BI Project (.pbip) save option*;
   - *Store semantic model using TMDL format*;
   - *Store reports using enhanced metadata format (PBIR)*.
3. Open `dashboards/EPRA.pbip`.
4. Point the model at the CSVs. Go to *Transform data → Edit parameters* and
   set **`ExportsPath`** to the absolute path of the repository's `exports/`
   folder (for example `C:\…\energy-procurement-risk-analyzer\exports\`).
   This is the only path in the model.
5. Click *Refresh*. Every table loads through the shared `LoadExport` query
   (UTF-8, comma-separated, header row; empty fields become null; en-US
   locale, as RP-705 requires).
6. Check the numbers before you trust them:
   - the five-year card must equal `wrong_strategy_cost_total` in
     `reports/NUMERIC_SSOT.md` (the card reads that row);
   - the page-1 columns must equal the `wrong_strategy_cost_<year>` rows;
   - the P95 cards must equal `p95_next12m_S1` and `p95_next12m_S3`.
7. Add small multiples to the Risk histogram (RP-404): drag
   `dim_strategy[strategy_label]` to *Small multiples*, then remove the
   S1/S3 visual filter. ADR-022 explains why this step was left for Desktop.
8. Optional: *File → Save as → .pbix* for a single-file copy. Do not commit
   it, because the PBIP is the source.
9. Take the screenshots in §5.

A Desktop save may rewrite some files (for example, it adds a base theme or
`.platform` metadata). After saving, run `make test`: the integrity test
reports any visual that lost its field, alt text or subtitle.

## 1. How the model loads the data (already built in the TMDL)

- `expressions.tmdl` holds the text parameter `ExportsPath` and the function
  `LoadExport(fileName)`.
- Each table partition calls `LoadExport("<file>.csv")`. It then sets explicit
  column types with culture `en-US` and, in every monthly table, adds
  `MonthStart = #date(year, month, 1)`. `strategy_annual_summary` uses
  1 January of its year as `MonthStart`.
- `forward_paths` gets one more column, `Cost Bin EUR million`: the lower edge
  of the path's 0.1 M EUR histogram bin.

| Table | File | Notes |
|---|---|---|
| `procurement_cost_monthly` | procurement_cost_monthly.csv | year_local, month_local: Whole number |
| `strategy_annual_summary` | strategy_annual_summary.csv | year, rank: Whole number |
| `forward_risk_summary` | forward_risk_summary.csv | variant: `unconditional` / `no_crisis` |
| `forward_paths` | forward_paths.csv | path: Whole number; + `Cost Bin EUR million` |
| `price_monthly` | price_monthly.csv | n_negative_hours: Whole number |
| `spread_monthly` | spread_monthly.csv | — |
| `price_daily` | price_daily.csv | date_local: Date (disconnected, drill-through) |
| `generation_monthly` | generation_monthly.csv | — |
| `data_quality_monthly` | data_quality_monthly.csv | counts: Whole number; has_oespi: True/False |
| `dim_strategy` | dim_strategy.csv | `strategy_label` sorted by `sort_order` |
| `ssot` | ssot.csv | **value: Text** (it holds numbers, ids and months) |
| `provenance` | provenance.csv | is_fixture: True/False |

`DimMonth` is a calculated table with one row per **day**, from the first
priced month to 12 months after the last one. It has the columns `Date`,
`MonthStart`, `Year` and `Month`, and it is marked as the date table on
`Date`. A table of month-start dates cannot be marked, because Power BI wants
contiguous days.

## 2. Data model (star schema)

```
                         dim_strategy (strategy_id)
                        /        |            \
 procurement_cost_monthly  strategy_annual_summary  forward_risk_summary / forward_paths
                        \        |
                        DimMonth (Date)
                        /     |        \          \
            price_monthly  spread_monthly  generation_monthly  data_quality_monthly

 disconnected: ssot (cards), provenance (banner), price_daily (drill-through)
```

All relationships are *many-to-one* and *single direction*, toward the
dimension:

- `procurement_cost_monthly[strategy_id]`, `strategy_annual_summary[strategy_id]`,
  `forward_risk_summary[strategy_id]` and `forward_paths[strategy_id]` →
  `dim_strategy[strategy_id]`
- `procurement_cost_monthly[MonthStart]`, `strategy_annual_summary[MonthStart]`,
  `price_monthly[MonthStart]`, `spread_monthly[MonthStart]`,
  `generation_monthly[MonthStart]` and `data_quality_monthly[MonthStart]` →
  `DimMonth[Date]`

Model rules that matter for the numbers:

- **Culture is `en-US`.** `VALUE()` therefore parses the SSOT's dot decimals
  the same way on every machine.
- **Implicit measures are off.** Visuals use the documented measures only.
- **Forward-risk measures read one bootstrap variant:** the one selected on
  `forward_risk_summary[variant]`, or `unconditional` when none is selected.
  An average of the two variants would mean nothing. `Paths` follows the same
  slicer, although `forward_paths` has no relationship to it.
- **Measures that compare strategies ignore strategy filters**
  (`Wrong Strategy Cost EUR`, `Cheapest Strategy`, `Cost vs Cheapest EUR`).
  They iterate `ALL ( dim_strategy )`, so a strategy row or slicer cannot hide
  the comparison.

## 3. Pages (16:9, 1280 × 720)

Every page has the same frame:

- top left: an English heading, with **one German subtitle sentence** under it
  (RP-405);
- top right: the `Data Banner` card. On fixture data it shows a red fixture
  warning (`Data Banner Fill`);
- bottom: the RP-702 source note on the left and the epistemic tag on the
  right (an `Epistemic Note …` measure where CALIBRATED or SIMULATED numbers
  appear).

Every data visual has a title and alt text. Tab order follows the reading
order.

### Page 1 — Headline (Entscheidung, RP-401)
*Untertitel: „Was hat die falsche Beschaffungsstrategie 2021–2025 gekostet, und welches Risiko bleibt?“*

- Card row:
  - `Card Wrong Strategy Cost 5y EUR` (€ millions, 2 decimals);
  - `Card Best Strategy 5y`;
  - `Card P95 Full Spot EUR`;
  - `Card P95 Fixed Annual EUR`.
- Clustered column: X `DimMonth[Year]` (2021–2025), Y
  `Wrong Strategy Cost EUR`. This is the RP-201 equivalent.
- Matrix: rows `dim_strategy[strategy_label]`, columns `DimMonth[Year]`,
  values `Total Cost EUR`.
  - The background shades from the design system's good tint (lowest) to its
    bad tint (highest), following ADR-021's diverging scale.
- Footer: `Epistemic Note Strategies`.

### Page 2 — Market (Markt, RP-402)
*Untertitel: „Der österreichische Day-Ahead-Markt: Preisniveau, negative Stunden und Abstand zu Deutschland.“*

- Line: X `DimMonth[MonthStart]`, Y `Avg Base Price…` and `Avg Peak Price…`.
- Column: X `DimMonth[Year]`, Y `Negative Price Hours`.
- Line: X `DimMonth[MonthStart]`, Y `Avg AT minus DE Spread EUR per MWh`, with
  a constant line at 0.
- Slicer: `DimMonth[Year]`.

### Page 3 — Strategies (Strategien, RP-403)
*Untertitel: „Jährliche Energiekosten je Strategie für einen Verbraucher mit 50 GWh pro Jahr.“*

- Matrix: strategy × year, showing `Total Cost EUR` and
  `Unit Cost EUR per MWh`.
- Line: X `DimMonth[MonthStart]`, Y `Cumulative Cost EUR`, legend
  `strategy_label`.
- Table: `strategy_annual_summary` year, strategy_label, unit_cost_eur_mwh,
  rank.
- Footer: `Epistemic Note Strategies`.

### Page 4 — Risk (Risiko, RP-404)
*Untertitel: „Kostenverteilung der nächsten 12 Monate aus 2.000 simulierten Pfaden – keine Prognose.“*

- Slicer: `forward_risk_summary[variant]`. With nothing selected, the
  measures show *unconditional*.
- Clustered bar: P5 / P50 / P95 per strategy (the `Forward P…` measures).
- Histogram: `Paths` by `forward_paths[Cost Bin EUR million]`, comparing full
  spot and fixed annual. Add small multiples in Desktop (§0 step 7).
- Scatter: X `Forward Mean EUR`, Y `Forward P95 EUR`, details
  `strategy_label` (the ST-404 frontier).
- Cards: `Card Risk Premium EUR`, `Card P95 Reduction EUR`.
- Footer: `Epistemic Note Risk`.

### Page 5 — Data quality (Datenqualität, ADR-020 §3)
*Untertitel: „Vollständigkeit und Qualität der Eingangsdaten je Monat.“*

- Cards: `Price Coverage Pct`, `Months Below Full Coverage`, `DST Days`,
  `Hours From 15min Quarters`, `Months Missing OESPI`.
- Line + column: X `DimMonth[MonthStart]`, line `Price Coverage Pct`,
  column `Hours From 15min Quarters`.
- Table: `data_quality_monthly`, filtered to `coverage_at_pct < 100`
  (empty = good).

## 4. Quality gates (no Desktop needed)

```
make test                                      # includes tests/unit/test_pbip_integrity.py
make pbip-validate PBIP_SCHEMA_DIR=<dir>       # every PBIR/PBIP JSON vs its declared schema
```

`PBIP_SCHEMA_DIR` is a local copy of
`https://developer.microsoft.com/json-schemas/`, the folder that contains
`fabric/item/report/definition/…`. Without it the target skips.

The integrity test checks the following:

- every field referenced by a visual, a visual filter or a formatting rule
  exists in the TMDL;
- relationships join existing columns toward a dimension;
- pages, headings and German subtitles match `epra.report.dashboard_pages`
  and this README;
- every data visual has a title and alt text;
- tab order is unique on each page;
- every measure has a description, a display folder and a format string;
- `measures.dax` equals the TMDL;
- the registered theme is `theme.json` byte for byte.

## 5. Screenshot checklist (RP-406)

Take the screenshots only from a **real-data** run. The `Data Banner` must not
show the fixture warning.

- [ ] `docs/assets/dashboard_p1.png`: Headline
- [ ] `docs/assets/dashboard_p2.png`: Market
- [ ] `docs/assets/dashboard_p3.png`: Strategies
- [ ] `docs/assets/dashboard_p4.png`: Risk
- [ ] `docs/assets/dashboard_p5.png`: Data quality
- [ ] Export at 1600 px width, with no personal data and no visible file paths.
- [ ] Reset `ExportsPath` to the placeholder before committing PBIP changes,
      so no personal path is committed.
- [ ] Add the screenshots to the README "Dashboard" section.

## 6. HTML twin (`make dashboard-html`)

`epra.report.html_dashboard` reads the same `exports/*.csv` and writes
`dashboards/html/index.html`. It is one self-contained file:

- the five pages above as tabs (arrow keys, and a URL hash per page);
- KPI cards that read `ssot.csv`;
- inline-SVG charts with hover and keyboard tooltips;
- a data table under every chart;
- light and dark design-system colours;
- no CDN, no fonts, no network and no backend (ADR-022, Charter O-4).

Two builds on the same exports produce byte-identical files.
`tests/unit/test_html_dashboard.py` reconciles the chart values with the SSOT.

The output folder is git-ignored, so a FIXTURE build cannot be committed.
After `make real-run`, commit the real build on purpose:

```
git add -f dashboards/html/index.html
```
