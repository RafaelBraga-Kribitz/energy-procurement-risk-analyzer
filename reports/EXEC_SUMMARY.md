# Executive summary — electricity procurement risk, StyriaMetal GmbH (reference)

*For: CFO / Head of Procurement. Energy cost only (no grid fees, taxes or levies). Data through 2026-09.*

## 1. The answer

Buying electricity with the wrong strategy cost the 50 GWh reference consumer €27.04 M (CALIBRATED) over 2021-2025, the sum of each year's gap between the dearest and the cheapest of four strategies. Over the five years **Fixed annual** was the cheapest strategy at €30.17 M (CALIBRATED) in total. For the next 12 months Fixed annual has the lowest expected cost, €4.77 M (SIMULATED), and Hybrid 70% fixed the lowest P95 exposure: €6.44 M (SIMULATED) against €6.61 M (SIMULATED).

## 2. How to read this

Market prices are **VERIFIED**: computed from ENTSO-E day-ahead data without modelling. Strategy costs are **CALIBRATED**: the 50 GWh load profile is constructed, not metered, and contract prices are translated from the ÖSPI index. Forward risk is **SIMULATED**: 2000 seeded resamples of historical months; it is not a price forecast.

## 3. The market you are buying in

The Austrian day-ahead price averaged 261.4 EUR/MWh in 2022 against 40.1 EUR/MWh in 2019 (VERIFIED). Volatility clusters: the GARCH persistence of daily price changes is 1.00 (VERIFIED), so turbulent periods last for months. 2025 had 378 hours with negative prices (VERIFIED). Chart: `reports/executive_charts/04_market_context.png`.

## 4. Strategy comparison 2021-2025 (EUR million, CALIBRATED)

| Strategy | 2021 | 2022 | 2023 | 2024 | 2025 | 2021-2025 |
|---|---:|---:|---:|---:|---:|---:|
| Full spot | 5.70 | 13.84 | 5.51 | 4.34 | 5.22 | 34.61 |
| ÖSPI-indexed | 2.43 | 8.30 | 12.50 | 4.90 | 4.05 | 32.18 |
| Fixed annual | 2.17 | 3.08 | 11.64 | 8.95 | 4.34 | 30.17 |
| Hybrid 30% fixed | 4.64 | 10.61 | 7.35 | 5.72 | 4.95 | 33.28 |
| Hybrid 50% fixed | 3.93 | 8.46 | 8.58 | 6.64 | 4.78 | 32.39 |
| Hybrid 70% fixed | 3.23 | 6.31 | 9.80 | 7.56 | 4.60 | 31.50 |

*Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated assumptions — see LIMITATIONS. Reference load profile is constructed (CALIBRATED), not measured; construction rules in SPEC-03.*

Cheapest strategy per year — 2021: Fixed annual; 2022: Fixed annual; 2023: Full spot; 2024: Full spot; 2025: ÖSPI-indexed. 3 different strategies were cheapest in at least one year, so no single choice wins every year; the budget question is how much year-to-year variation the company can absorb.

## 5. Forward risk and recommendation (2026-10..2027-09, EUR million, SIMULATED)

| Strategy | Mean | P5 | P50 | P95 | CVaR95 |
|---|---:|---:|---:|---:|---:|
| Full spot | 5.36 | 3.65 | 5.25 | 7.56 | 8.24 |
| ÖSPI-indexed | 5.15 | 3.47 | 5.03 | 7.16 | 7.88 |
| Fixed annual | 4.77 | 3.75 | 4.51 | 6.61 | 6.96 |
| Hybrid 30% fixed | 5.18 | 3.80 | 5.07 | 6.85 | 7.37 |
| Hybrid 50% fixed | 5.06 | 3.84 | 4.98 | 6.61 | 6.97 |
| Hybrid 70% fixed | 4.95 | 3.88 | 4.82 | 6.44 | 6.80 |

A **cost-minimizing CFO** chooses Fixed annual: the lowest expected 12-month cost, €4.77 M (SIMULATED), with a P95 of €6.61 M (SIMULATED). A **risk-averse CFO** chooses Hybrid 70% fixed: it lowers the P95 by €0.17 M (SIMULATED) and costs €0.18 M (SIMULATED) more in expectation. That premium is the price of the risk reduction.

## 6. What would change this analysis

- Metered (RLM) load data instead of the constructed profile would change the cost levels, not the logic of the comparison (LIMITATIONS §1).
- Real supplier offers can differ from the ÖSPI proxy by margin, credit and flexibility terms; the direction of that bias is unknown (§2, §3).
- A crisis without historical precedent lies outside the bootstrap; the P95 would understate it (§4).
