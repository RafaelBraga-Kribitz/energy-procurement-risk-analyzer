# A1 — AT day-ahead market: annual summary

Hourly AT day-ahead prices in EUR/MWh, per local calendar year (VERIFIED). `neg_share_solar_pct` is the share of negative hours falling in Apr-Sep 10:00-16:00 local; years with fewer than 8,700 priced hours are partial.

| year | hours | mean | median | std | min | max | peak | offpeak | peak_minus_offpeak | neg_hours | neg_share_pct | neg_mean_depth | neg_share_solar_pct | hours_above_500 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 8760 | 40.1 | 39.2 | 13.1 | -59.8 | 121.5 | 47.3 | 36.2 | 11.1 | 68 | 0.8 | 11.0 | 33.8 | 0 |
| 2020 | 8784 | 33.1 | 33.1 | 15.9 | -77.7 | 200.0 | 40.5 | 29.3 | 11.2 | 111 | 1.3 | 16.7 | 43.2 | 0 |
| 2021 | 8760 | 106.9 | 79.0 | 77.6 | -66.2 | 620.0 | 128.3 | 95.5 | 32.8 | 64 | 0.7 | 11.7 | 67.2 | 14 |
| 2022 | 8760 | 261.4 | 224.0 | 138.5 | 0.0 | 919.6 | 305.8 | 238.3 | 67.5 | 0 | 0.0 | 0.0 | 0.0 | 580 |
| 2023 | 8760 | 102.1 | 101.9 | 44.4 | -500.0 | 437.5 | 117.8 | 94.1 | 23.8 | 111 | 1.3 | 15.5 | 58.6 | 0 |
| 2024 | 8784 | 81.5 | 80.5 | 49.5 | -126.4 | 850.0 | 93.6 | 75.2 | 18.4 | 296 | 3.4 | 15.8 | 81.8 | 10 |
| 2025 | 8760 | 98.9 | 101.3 | 49.7 | -252.6 | 561.8 | 104.9 | 95.8 | 9.1 | 378 | 4.3 | 16.5 | 93.9 | 1 |
| 2026 | 6551 | 121.8 | 127.0 | 64.3 | -496.9 | 592.8 | 122.7 | 121.4 | 1.3 | 260 | 4.0 | 25.3 | 86.9 | 4 |

## So what for a procurement manager

The Austrian day-ahead market is not one market but several regimes stacked in time. In 2022 the average hour cost 261.4 EUR/MWh, about 6.5 times the 2019 level of 40.1 EUR/MWh, and the price duration curves show that the crisis lifted every hour of the year rather than adding a few extreme spikes. Since then the shape has changed as much as the level: solar generation now hollows out the midday hours from April to September, which is visible in the heatmap as a dark summer band around noon. In 2025 the market saw 378 hours with negative prices, and 94% of them fell in the spring and summer daylight window of 10:00 to 16:00. For a consumer that can move load, those hours are paid consumption; for an inflexible three-shift plant like the reference consumer they are a modest discount that does not offset winter evening peaks. Buying decisions should therefore be judged against the hourly shape the plant actually consumes, not against the headline annual average.
