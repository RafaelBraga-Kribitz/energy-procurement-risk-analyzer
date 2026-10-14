# A3 — Volatility regimes

> **FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real ENTSO-E data. Every number here exercises the pipeline only and is NOT a result.**

Basis: daily arithmetic change of the AT base price, d_t in EUR/MWh (not log returns — prices can be ≤ 0). HMM fitted on z-scored d_t.

| regime | days | occupancy_pct | mean_abs_d_t_eur_mwh | mean_price_eur_mwh |
|---|---:|---:|---:|---:|
| calm | 908 | 32.1 | 2.2 | 34.8 |
| elevated | 1300 | 46.0 | 4.4 | 65.4 |
| crisis | 621 | 22.0 | 27.8 | 179.7 |

GARCH(1,1): α = 0.0537, β = 0.9463, persistence α+β = 1.0000.

**AN-304 sanity gate: PASS** — top-2 share 2021-09..2023-06 = 100.0% (≥ 70%); calm share 2019 = 100.0% (≥ 60%).

## Interpretation

The three-state model assigns 100% of the days between September 2021 and June 2023 to the elevated or crisis state and 100% of 2019 to the calm state, so the regimes line up with what market participants lived through. Crisis days averaged a base price of 179.7 EUR/MWh against 34.8 EUR/MWh in calm days: in this market high prices and high volatility arrive together. The GARCH persistence α+β is 1.000, at or above one, i.e. near-integrated: shocks effectively do not decay. For procurement this means risk is clustered: a buyer exposed to spot does not face independent good and bad days but long stretches of turbulence, which is why the forward-risk simulation draws whole historical months together and reports a no-crisis variant alongside the unconditional one.
