# Sensitivity matrix (ST-303)

> **FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real ENTSO-E data. Every number here exercises the pipeline only and is NOT a result.**

*Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated assumptions — see LIMITATIONS.*

*Reference load profile is constructed (CALIBRATED), not measured; construction rules in SPEC-03.*

Five-year (2021-2025) energy cost per strategy in EUR million; each scenario changes exactly one input versus `base`: fixed-price premium, load shape (flat baseload), or S3 lock window (full prior year).

| scenario | S1 | S2 | S3 | S4_30 | S4_50 | S4_70 | best | wrong_strategy_cost_total_m |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| base | 25.95 | 27.45 | 25.93 | 25.94 | 25.94 | 25.93 | S3 | 16.59 |
| premium_0 | 25.95 | 27.45 | 24.68 | 25.57 | 25.31 | 25.06 | S3 | 16.59 |
| premium_10 | 25.95 | 27.45 | 27.18 | 26.32 | 26.56 | 26.81 | S1 | 16.65 |
| flat_baseload | 25.69 | 26.88 | 25.44 | 25.61 | 25.56 | 25.51 | S3 | 16.20 |
| lock_full_prior_year | 25.95 | 27.45 | 26.98 | 26.26 | 26.46 | 26.67 | S1 | 20.61 |
