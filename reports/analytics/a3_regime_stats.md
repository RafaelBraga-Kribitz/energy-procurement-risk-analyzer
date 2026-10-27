# A3 — Volatility regimes

Basis: daily arithmetic change of the AT base price, d_t in EUR/MWh (not log returns — prices can be ≤ 0). HMM fitted on z-scored d_t.

| regime | days | occupancy_pct | mean_abs_d_t_eur_mwh | mean_price_eur_mwh |
|---|---:|---:|---:|---:|
| calm | 968 | 34.2 | 6.0 | 46.3 |
| elevated | 1523 | 53.8 | 17.6 | 107.6 |
| crisis | 338 | 11.9 | 47.4 | 262.9 |

GARCH(1,1): α = 0.1007, β = 0.8993, persistence α+β = 1.0000.

**AN-304 sanity gate: PASS** — top-2 share 2021-09..2023-06 = 100.0% (≥ 70%); calm share 2019 = 98.6% (≥ 60%).

## Interpretation

The three-state model assigns 100% of the days between September 2021 and June 2023 to the elevated or crisis state and 99% of 2019 to the calm state, so the regimes line up with what market participants lived through. Crisis days averaged a base price of 262.9 EUR/MWh against 46.3 EUR/MWh in calm days: in this market high prices and high volatility arrive together. The GARCH persistence α+β is 1.000, close to one, so a volatility shock decays only slowly. For procurement this means risk is clustered: a buyer exposed to spot does not face independent good and bad days but long stretches of turbulence, which is why the forward-risk simulation draws whole historical months together and reports a no-crisis variant alongside the unconditional one.
