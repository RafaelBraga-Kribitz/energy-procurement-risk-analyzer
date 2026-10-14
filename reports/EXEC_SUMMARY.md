# Executive summary — electricity procurement risk, StyriaMetal GmbH (reference)

> **FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real ENTSO-E data. Every number here exercises the pipeline only and is NOT a result.**

*For: CFO / Head of Procurement. Energy cost only (no grid fees, taxes or levies). Data through 2026-09.*

## 1. The answer

Buying electricity with the wrong strategy cost the 50 GWh reference consumer €16.59 M (CALIBRATED) over 2021-2025, the sum of each year's gap between the dearest and the cheapest of four strategies. Over the five years **Fixed annual** was the cheapest strategy at €25.93 M (CALIBRATED) in total. For the next 12 months Full spot has the lowest expected cost, €4.06 M (SIMULATED), and Hybrid 50% fixed the lowest P95 exposure: €5.51 M (SIMULATED) against €5.81 M (SIMULATED).

## 2. How to read this

Market prices are **VERIFIED**: computed from ENTSO-E day-ahead data without modelling. Strategy costs are **CALIBRATED**: the 50 GWh load profile is constructed, not metered, and contract prices are translated from the ÖSPI index. Forward risk is **SIMULATED**: 2000 seeded resamples of historical months; it is not a price forecast.

## 3. The market you are buying in

The Austrian day-ahead price averaged 196.5 EUR/MWh in 2022 against 38.5 EUR/MWh in 2019 (VERIFIED). Volatility clusters: the GARCH persistence of daily price changes is 1.00 (VERIFIED), so turbulent periods last for months. 2025 had 266 hours with negative prices (VERIFIED). Chart: `reports/executive_charts/04_market_context.png`.

## 4. Strategy comparison 2021-2025 (EUR million, CALIBRATED)

| Strategy | 2021 | 2022 | 2023 | 2024 | 2025 | 2021-2025 |
|---|---:|---:|---:|---:|---:|---:|
| Full spot | 2.63 | 9.89 | 7.10 | 3.29 | 3.04 | 25.95 |
| ÖSPI-indexed | 2.08 | 7.08 | 10.64 | 4.19 | 3.47 | 27.45 |
| Fixed annual | 1.89 | 2.67 | 9.95 | 7.67 | 3.75 | 25.93 |
| Hybrid 30% fixed | 2.40 | 7.73 | 7.95 | 4.61 | 3.25 | 25.94 |
| Hybrid 50% fixed | 2.26 | 6.28 | 8.53 | 5.48 | 3.39 | 25.94 |
| Hybrid 70% fixed | 2.11 | 4.84 | 9.10 | 6.35 | 3.53 | 25.93 |

*Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated assumptions — see LIMITATIONS. Reference load profile is constructed (CALIBRATED), not measured; construction rules in SPEC-03.*

Cheapest strategy per year — 2021: Fixed annual; 2022: Fixed annual; 2023: Full spot; 2024: Full spot; 2025: Full spot. 2 different strategies were cheapest in at least one year, so no single choice wins every year; the budget question is how much year-to-year variation the company can absorb.

## 5. Forward risk and recommendation (2026-10..2027-09, EUR million, SIMULATED)

| Strategy | Mean | P5 | P50 | P95 | CVaR95 |
|---|---:|---:|---:|---:|---:|
| Full spot | 4.06 | 2.73 | 3.96 | 5.81 | 6.35 |
| ÖSPI-indexed | 4.39 | 2.97 | 4.30 | 6.10 | 6.72 |
| Fixed annual | 4.12 | 3.25 | 3.90 | 5.68 | 5.98 |
| Hybrid 30% fixed | 4.08 | 2.96 | 3.99 | 5.62 | 6.01 |
| Hybrid 50% fixed | 4.09 | 3.08 | 4.01 | 5.51 | 5.87 |
| Hybrid 70% fixed | 4.10 | 3.18 | 3.93 | 5.52 | 5.85 |

A **cost-minimizing CFO** chooses Full spot: the lowest expected 12-month cost, €4.06 M (SIMULATED), with a P95 of €5.81 M (SIMULATED). A **risk-averse CFO** chooses Hybrid 50% fixed: it lowers the P95 by €0.30 M (SIMULATED) and costs €0.03 M (SIMULATED) more in expectation. That premium is the price of the risk reduction.

## 6. What would change this analysis

- Metered (RLM) load data instead of the constructed profile would change the cost levels, not the logic of the comparison (LIMITATIONS §1).
- Real supplier offers can differ from the ÖSPI proxy by margin, credit and flexibility terms; the direction of that bias is unknown (§2, §3).
- A crisis without historical precedent lies outside the bootstrap; the P95 would understate it (§4).
