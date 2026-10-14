# Power BI dashboard — build kit (SPEC-06 §4, ADR-020 §4)

**Status:** build kit complete; `epra.pbix` and the screenshots are a **human
step** (AGENTS.md §2 item 5). Everything needed to build the report in under
an hour is in this folder:

| File | What it is |
|---|---|
| `README.md` (this file) | Data model, Power Query load steps, page-by-page layout, screenshot checklist |
| `measures.dax` | Every DAX measure, grouped by home table |
| `theme.json` | Report theme: Okabe-Ito strategy colours identical to the PNG charts (RP-704, tested) |

Power BI reads **only** `exports/*.csv` (DM-070), never DuckDB, so anyone can
rebuild the report without the warehouse: `make all` (or `make export` after a
run) writes the CSVs.

> If `exports/provenance.csv` says `is_fixture = True`, the CSVs come from the
> synthetic CI fixture (ADR-018). Build and screenshot the dashboard only on a
> real-data run; the `Data Banner` measure shows a red fixture warning otherwise.

## 1. Load the data (Power Query)

1. **Get data → Folder** → select the repository's `exports/` folder → *Transform data*.
   (A folder source keeps the paths relative to one parameter, `ExportsPath`; to
   re-point the report, change only that parameter.)
2. For each file below, filter the folder query on `Name`, expand the binary
   with *CSV, UTF-8, comma delimiter, first row as headers*, and name the query
   exactly as in the table. Locale: **English (United States)** (dot decimal,
   ISO dates, RP-705).
3. Set types as listed; everything not listed stays *Decimal number* (numbers)
   or *Text*.

| Query / table | File | Key types |
|---|---|---|
| `procurement_cost_monthly` | procurement_cost_monthly.csv | year_local, month_local: Whole number |
| `strategy_annual_summary` | strategy_annual_summary.csv | year, rank: Whole number |
| `forward_risk_summary` | forward_risk_summary.csv | — |
| `forward_paths` | forward_paths.csv | path: Whole number |
| `price_monthly` | price_monthly.csv | year_local, month_local, n_negative_hours: Whole number |
| `spread_monthly` | spread_monthly.csv | year_local, month_local: Whole number |
| `price_daily` | price_daily.csv | date_local: Date |
| `generation_monthly` | generation_monthly.csv | year_local, month_local: Whole number |
| `data_quality_monthly` | data_quality_monthly.csv | counts: Whole number; has_oespi: True/False |
| `dim_strategy` | dim_strategy.csv | sort_order: Whole number |
| `ssot` | ssot.csv | **value: Text** (it holds numbers, ids and months) |
| `provenance` | provenance.csv | is_fixture: True/False |

4. In every monthly table add a column `MonthStart = #date([year_local], [month_local], 1)`
   (Date type). In `strategy_annual_summary` add `MonthStart = #date([year], 1, 1)`.
5. Create `DimMonth` (*Modeling → New table*):

```DAX
DimMonth =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2019, 1, 1 ), EOMONTH ( MAX ( price_monthly[MonthStart] ), 12 ) ),
    "MonthStart", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ),
    "Year", YEAR ( [Date] ),
    "Month", MONTH ( [Date] )
)
```

   Then keep one row per month: in Power Query, or by using
   `SUMMARIZE ( …, [MonthStart], [Year], [Month] )` around the expression above.
   Mark it as a date table on `MonthStart`.
6. Sort `dim_strategy[strategy_label]` by `dim_strategy[sort_order]`.

## 2. Data model (star schema)

```
                         dim_strategy (strategy_id)
                        /        |            \
 procurement_cost_monthly  strategy_annual_summary  forward_risk_summary / forward_paths
                        \        |
                        DimMonth (MonthStart)
                        /     |        \          \
            price_monthly  spread_monthly  generation_monthly  data_quality_monthly

 disconnected: ssot (cards), provenance (banner), price_daily (drill-through)
```

Relationships (all *many-to-one, single direction* toward the dimension):

- `procurement_cost_monthly[strategy_id]`, `strategy_annual_summary[strategy_id]`,
  `forward_risk_summary[strategy_id]`, `forward_paths[strategy_id]` → `dim_strategy[strategy_id]`
- `procurement_cost_monthly[MonthStart]`, `strategy_annual_summary[MonthStart]`,
  `price_monthly[MonthStart]`, `spread_monthly[MonthStart]`,
  `generation_monthly[MonthStart]`, `data_quality_monthly[MonthStart]` → `DimMonth[MonthStart]`

Then paste the measures from `measures.dax` and import `theme.json`
(*View → Themes → Browse for themes*).

## 3. Pages (16:9, 1280 × 720)

Every page: title top-left, **one German subtitle sentence** under it (RP-405),
`Data Banner` card top-right, and the epistemic note (`Epistemic Note …`
measure) as a footer text box where CALIBRATED/SIMULATED numbers appear (RP-702).

### Page 1 — Entscheidung / Decision (RP-401)
*Untertitel: „Was hat die falsche Beschaffungsstrategie 2021–2025 gekostet, und welches Risiko bleibt?“*

- Card row: `Card Wrong Strategy Cost 5y EUR` (format € millions, 2 decimals),
  `Card Best Strategy 5y`, `Card P95 Full Spot EUR`, `Card P95 Fixed Annual EUR`.
- Clustered column: X `DimMonth[Year]` (2021–2025), Y `Wrong Strategy Cost EUR`
  — the RP-201 equivalent.
- Matrix: rows `dim_strategy[strategy_label]`, columns `DimMonth[Year]`, values
  `Total Cost EUR`; conditional formatting background, lowest = blue, highest = red.
- Footer: `Epistemic Note Strategies`.

### Page 2 — Markt / Market drivers (RP-402)
*Untertitel: „Der österreichische Day-Ahead-Markt: Preisniveau, negative Stunden und Abstand zu Deutschland.“*

- Line: X `DimMonth[MonthStart]`, Y `Avg Base Price…`, `Avg Peak Price…`.
- Column: X `DimMonth[Year]`, Y `Negative Price Hours`.
- Line: X `DimMonth[MonthStart]`, Y `Avg AT minus DE Spread EUR per MWh`, constant line at 0.
- Slicer: `DimMonth[Year]`.

### Page 3 — Strategien / Strategies (RP-403)
*Untertitel: „Jährliche Energiekosten je Strategie für einen Verbraucher mit 50 GWh pro Jahr.“*

- Matrix: strategy × year, `Total Cost EUR` and `Unit Cost EUR per MWh`.
- Line: X `DimMonth[MonthStart]`, Y `Cumulative Cost EUR`, legend `strategy_label`.
- Table: `strategy_annual_summary` year, strategy_label, unit_cost_eur_mwh, rank.
- Footer: `Epistemic Note Strategies`.

### Page 4 — Risiko / Forward risk (RP-404)
*Untertitel: „Kostenverteilung der nächsten 12 Monate aus 2.000 simulierten Pfaden – keine Prognose.“*

- Slicer: `forward_risk_summary[variant]` (default *unconditional*).
- Box-and-whisker or clustered bar: per strategy P5 / P50 / P95 (`Forward P…` measures).
- Histogram: `forward_paths[cost_eur]` binned at 0.1 M, small multiples by `strategy_label`.
- Scatter: X `Forward Mean EUR`, Y `Forward P95 EUR`, details `strategy_label` (ST-404 frontier).
- Cards: `Card Risk Premium EUR`, `Card P95 Reduction EUR`.
- Footer: `Epistemic Note Risk`.

### Page 5 — Datenqualität / Data quality (ADR-020 §3)
*Untertitel: „Vollständigkeit und Qualität der Eingangsdaten je Monat.“*

- Cards: `Price Coverage Pct`, `Months Below Full Coverage`, `DST Days`,
  `Hours From 15min Quarters`, `Months Missing OESPI`.
- Line + column: X `DimMonth[MonthStart]`, line `Price Coverage Pct`, column
  `Hours From 15min Quarters`.
- Table: `data_quality_monthly` filtered to `coverage_at_pct < 100` (empty = good).

## 4. Screenshot checklist (RP-406)

Only from a **real-data** run (`Data Banner` must not show the fixture warning):

- [ ] `docs/assets/dashboard_p1.png` — Decision
- [ ] `docs/assets/dashboard_p2.png` — Market
- [ ] `docs/assets/dashboard_p3.png` — Strategies
- [ ] `docs/assets/dashboard_p4.png` — Risk
- [ ] `docs/assets/dashboard_p5.png` — Data quality
- [ ] Export at 1600 px width, no personal data, no visible file paths.
- [ ] Commit `dashboards/epra.pbix` (CSV paths relative via `ExportsPath`).
- [ ] Add the screenshots to the README "Dashboard" section.

Cross-check before publishing: the five-year card must equal
`wrong_strategy_cost_total` in `reports/NUMERIC_SSOT.md` (it reads that row),
and the page-1 bars must equal the `wrong_strategy_cost_<year>` rows.
