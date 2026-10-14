# Strategy comparison 2021-2025 (Q1)

> **FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real ENTSO-E data. Every number here exercises the pipeline only and is NOT a result.**

*Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated assumptions — see LIMITATIONS.*

*Reference load profile is constructed (CALIBRATED), not measured; construction rules in SPEC-03.*

## Annual energy cost (EUR million, CALIBRATED)

| strategy | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| Full spot | 2.63 | 9.89 | 7.10 | 3.29 | 3.04 |
| ÖSPI-indexed | 2.08 | 7.08 | 10.64 | 4.19 | 3.47 |
| Fixed annual | 1.89 | 2.67 | 9.95 | 7.67 | 3.75 |
| Hybrid 30% fixed | 2.40 | 7.73 | 7.95 | 4.61 | 3.25 |
| Hybrid 50% fixed | 2.26 | 6.28 | 8.53 | 5.48 | 3.39 |
| Hybrid 70% fixed | 2.11 | 4.84 | 9.10 | 6.35 | 3.53 |

## Unit cost (EUR/MWh, CALIBRATED)

| strategy | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| Full spot | 52.5 | 197.9 | 141.9 | 65.9 | 60.8 |
| ÖSPI-indexed | 41.6 | 141.6 | 212.9 | 83.7 | 69.3 |
| Fixed annual | 37.8 | 53.4 | 199.1 | 153.3 | 75.0 |
| Hybrid 30% fixed | 48.1 | 154.5 | 159.1 | 92.1 | 65.0 |
| Hybrid 50% fixed | 45.1 | 125.7 | 170.5 | 109.6 | 67.9 |
| Hybrid 70% fixed | 42.2 | 96.8 | 181.9 | 127.1 | 70.7 |

## Cost of the wrong strategy (max − min per year, CALIBRATED)

| year | wrong_strategy_cost |
|---|---|
| 2021 | €0.74 M |
| 2022 | €7.22 M |
| 2023 | €3.55 M |
| 2024 | €4.37 M |
| 2025 | €0.71 M |

## Calibration anchors (CALIBRATED, ST-201..204)

p_ref_base = 39.06 EUR/MWh; p_ref_peak = 40.34 EUR/MWh; ÖSPI base ref = 103.54; ÖSPI peak ref = 89.05 (index points).
