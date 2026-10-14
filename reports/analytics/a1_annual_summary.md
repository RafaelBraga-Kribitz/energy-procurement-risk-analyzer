# A1 — AT day-ahead market: annual summary

> **FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real ENTSO-E data. Every number here exercises the pipeline only and is NOT a result.**

Hourly AT day-ahead prices in EUR/MWh, per local calendar year (VERIFIED). `neg_share_solar_pct` is the share of negative hours falling in Apr-Sep 10:00-16:00 local; years with fewer than 8,700 priced hours are partial.

| year | hours | mean | median | std | min | max | peak | offpeak | peak_minus_offpeak | neg_hours | neg_share_pct | neg_mean_depth | neg_share_solar_pct | hours_above_500 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 8760 | 38.5 | 37.8 | 7.7 | 15.4 | 73.6 | 39.8 | 37.9 | 1.9 | 0 | 0.0 | 0.0 | 0.0 | 0 |
| 2020 | 8784 | 29.9 | 30.4 | 8.3 | 0.4 | 55.8 | 29.1 | 30.3 | -1.2 | 0 | 0.0 | 0.0 | 0.0 | 0 |
| 2021 | 8760 | 52.6 | 47.3 | 23.0 | 0.5 | 147.7 | 52.1 | 52.8 | -0.7 | 0 | 0.0 | 0.0 | 0.0 | 0 |
| 2022 | 8760 | 196.5 | 174.4 | 98.5 | 30.7 | 793.1 | 205.6 | 191.7 | 13.9 | 0 | 0.0 | 0.0 | 0.0 | 104 |
| 2023 | 8760 | 138.2 | 116.9 | 69.9 | 9.8 | 496.8 | 141.3 | 136.6 | 4.8 | 0 | 0.0 | 0.0 | 0.0 | 0 |
| 2024 | 8784 | 65.5 | 68.2 | 23.5 | -19.3 | 150.9 | 61.2 | 67.8 | -6.5 | 93 | 1.1 | 5.4 | 100.0 | 0 |
| 2025 | 8760 | 61.0 | 65.3 | 23.6 | -24.7 | 119.8 | 55.0 | 64.1 | -9.1 | 266 | 3.0 | 8.0 | 100.0 | 0 |
| 2026 | 6551 | 57.8 | 65.0 | 27.7 | -36.3 | 128.7 | 47.3 | 63.3 | -16.0 | 390 | 6.0 | 11.0 | 100.0 | 0 |

## So what for a procurement manager

The Austrian day-ahead market is not one market but several regimes stacked in time. In 2022 the average hour cost 196.5 EUR/MWh, about 5.1 times the 2019 level of 38.5 EUR/MWh, and the price duration curves show that the crisis lifted every hour of the year rather than adding a few extreme spikes. Since then the shape has changed as much as the level: solar generation now hollows out the midday hours from April to September, which is visible in the heatmap as a dark summer band around noon. In 2025 the market saw 266 hours with negative prices, and 100% of them fell in the spring and summer daylight window of 10:00 to 16:00. For a consumer that can move load, those hours are paid consumption; for an inflexible three-shift plant like the reference consumer they are a modest discount that does not offset winter evening peaks. Buying decisions should therefore be judged against the hourly shape the plant actually consumes, not against the headline annual average.
