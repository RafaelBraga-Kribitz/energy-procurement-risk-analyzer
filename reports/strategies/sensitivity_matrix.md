# Sensitivity matrix (ST-303)

*Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated assumptions — see LIMITATIONS.*

*Reference load profile is constructed (CALIBRATED), not measured; construction rules in SPEC-03.*

Five-year (2021-2025) energy cost per strategy in EUR million; each scenario changes exactly one input versus `base`: fixed-price premium, load shape (flat baseload), or S3 lock window (full prior year).

| scenario | S1 | S2 | S3 | S4_30 | S4_50 | S4_70 | best | wrong_strategy_cost_total_m |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| base | 34.61 | 32.18 | 30.17 | 33.28 | 32.39 | 31.50 | S3 | 27.04 |
| premium_0 | 34.61 | 32.18 | 28.92 | 32.90 | 31.77 | 30.63 | S3 | 27.29 |
| premium_10 | 34.61 | 32.18 | 31.42 | 33.65 | 33.02 | 32.38 | S3 | 26.79 |
| flat_baseload | 32.54 | 29.37 | 27.68 | 31.09 | 30.11 | 29.14 | S3 | 24.96 |
| lock_full_prior_year | 34.61 | 32.18 | 31.42 | 33.65 | 33.01 | 32.38 | S3 | 30.99 |
