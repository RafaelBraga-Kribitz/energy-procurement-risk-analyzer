# A2 — AT vs DE-LU day-ahead spread

> **FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real ENTSO-E data. Every number here exercises the pipeline only and is NOT a result.**

Hourly spread = AT price − DE-LU price, EUR/MWh, per local year (VERIFIED). Peak = Mon-Fri 08-20 local, non-holiday.

| year | hours | mean | median | std | share_at_above_de_pct | mean_peak | mean_offpeak |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 8760 | 5.8 | 5.8 | 7.2 | 79.2 | 5.9 | 5.8 |
| 2020 | 8784 | 4.8 | 4.7 | 6.0 | 79.0 | 4.8 | 4.8 |
| 2021 | 8760 | 4.3 | 5.4 | 10.6 | 71.3 | 4.5 | 4.2 |
| 2022 | 8760 | -1.5 | -5.3 | 89.5 | 47.3 | -0.4 | -2.1 |
| 2023 | 8760 | 3.7 | 2.7 | 53.1 | 53.4 | 4.2 | 3.4 |
| 2024 | 8784 | 6.2 | 6.3 | 11.6 | 70.6 | 6.3 | 6.1 |
| 2025 | 8760 | 5.0 | 5.3 | 12.1 | 66.5 | 5.5 | 4.8 |
| 2026 | 6551 | 3.7 | 4.1 | 11.7 | 62.6 | 3.5 | 3.9 |

## Interpretation — you are not in Germany

Across the complete years in the window the Austrian price sat above the German one in 67% of hours on average, and the annual mean spread was widest in 2024 at 6.2 EUR/MWh. Since the 2018 bidding-zone split, cross-border capacity is limited, so when it binds the Austrian zone clears on its own, typically at a premium to Germany. For an Austrian buyer this means that German price reporting, German index products and German benchmarks systematically misstate what an Austrian plant pays: a supplier quote that looks cheap against a German reference can still be expensive for Austria, and a hedge bought on a German product leaves the spread unhedged. Procurement benchmarks and contract indexation for this consumer should therefore reference the Austrian zone, and the spread itself is a risk that needs to be budgeted.
