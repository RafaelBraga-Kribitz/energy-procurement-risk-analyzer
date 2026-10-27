# A4 — Weather and system-load sensitivity

OLS of daily mean AT load (MW) on HDD_18, a weekend/holiday dummy and month fixed effects; HC1 robust standard errors; n = 2830 days, R² = 0.835.

| term | estimate | ci_low | ci_high |
|---|---:|---:|---:|
| hdd_18 (MW per K·day) | 76.5 | 70.9 | 82.2 |
| weekend (MW) | -1268.5 | -1299.6 | -1237.3 |

## Interpretation

Holding month and day type fixed, one additional heating degree day raises the Austrian system load by about 77 MW (95% interval 71 to 82 MW, HC1 robust), while weekends and holidays sit about 1268 MW below working days. This is a property of the SYSTEM: cold spells raise demand across the country and tend to lift prices in exactly the winter hours a manufacturer cannot avoid. It is not a property of the reference consumer, whose load profile is weather-invariant by construction (SPEC-03 uses calendar rules and fixed seasonal factors only), so temperature reaches the procurement result only through the price, never through the plant's own volume. Reviewers should not read the A4 slope as a statement about StyriaMetal's consumption.
