# Economic evaluation: Energy Procurement Risk Analyzer

Pre-build scenario exercise · evaluation date 2026-07-18 · method v2.0 · cost basis v1.1 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

The CFO of a Styrian manufacturer decides each year how much electricity to lock at a fixed price; the study is valued as information: premium saved when the plant can carry spot exposure, loss avoided when it cannot.

## Scale, baseline and horizon

- Reference consumer: 50 GWh a year, three-shift metal processing, energy only [sourced: `PROJECT_CHARTER.md` §2 at `c043933`].
- Strategies: spot, index-linked, fixed annual (locked in the prior year's second half), 30, 50 or 70 % fixed. Fixed-price premium €5/MWh, tested at €0 and €10 [sourced: `docs/SPEC-05_strategy_simulator.md` §3, §8 at `c043933`].
- Stakes: the Austrian day-ahead annual mean rose from €107/MWh in 2021 to €261/MWh in 2022 [sourced: [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)]; energy spend €5M to €13M a year [estimate].
- Baseline: "gut feeling or whatever their supplier offers" (charter §1); here, the supplier's fixed offer for all volume [assumption].
- Horizon: 3 yearly lock decisions, discounted at 5 %.
- Committed forecasts: "millions of euros" between strategies (charter §1); effort budget 11.5 days (§7).

## Scenarios

Action: lock 50 % instead of 100 %. Value per year against the baseline.

| State | Value per year | Probability |
|---|---|---|
| Premium €10/MWh; the 50 % share's 95th-percentile cost (P95) fits the cap | +€0.25M (25 GWh × €10) | 0.15 [assumption: offers rarely itemise the premium] |
| Premium €5/MWh; P95 fits the cap | +€0.125M | 0.35 [assumption: SPEC-05 default] |
| Premium near €0; no usable benefit | €0 | 0.20 [assumption] |
| Adverse: P95 breaches the cap; a spike forces a mid-year re-hedge of 25 GWh at €20/MWh above the lock | +€0.125M − €0.50M = −€0.375M | 0.30 [assumption: tight caps after 2022] |

## Expected value and cost

- EV(lock 50 %) = 0.15 × 0.25 + 0.35 × 0.125 + 0 − 0.30 × 0.375 = −€0.031M a year, so the uninformed CFO locks everything.
- With perfect information the CFO cuts the fixed share except in the adverse state: €0.0375M + €0.04375M = €81k a year. Expected value of perfect information (EVPI) = **€81k a year**; over 3 years at 5 % (factor 2.72), **€221k**.
- Realistic fraction f = 0.35 [assumption, sensitivity parameter: the P95 per fixed share targets the adverse state; constructed load, the index standing in for real offers (charter risk R-5, "Certain") and non-use pull it down]. Expected gross value = 0.35 × €221k = **€77k**.

Rate: €47 per active hour, the market cost of the role this work needs (data analytics · senior, advertised minimum, ADJMI snapshot 2026-10-18; ADJMI = Austria Data-Job Market Intelligence), €44 loaded plus €3 AI and equipment. Maintenance: 10 % of build hours a year, 3 years. Implementation: 16 h for metered load and real offers [assumption]. Hosting €0.

| Case | Build | Maintenance | Implementation | Total cost | Multiple |
|---|---|---|---|---|---|
| Central, 60 h | €2,820 | €846 | €752 | €4,418 | 17.5× |
| 0.5×, 30 h | €1,410 | €423 | €752 | €2,585 | 30× |
| 1.5×, 90 h | €4,230 | €1,269 | €752 | €6,251 | 12× |

## Verdict

**Passes financial hurdle**: 17.5× central; 13.7× at a rate 30 % higher (€60.2 all-in; the inputs are floors). Maximum affordable cost: €77k ÷ 4 = **€19k**.

Break-even driver: the fraction f. 1× at f = 0.020; 4× at f = 0.080.

Reversing assumptions:

1. Real offers carry almost no premium. EVPI is €16,250 a year per €1/MWh of default premium; 4× needs a premium of about €1.1/MWh instead of €5.
2. A written hedging policy already settles whether the cap binds.

## Recommendation

**Build.** Measure: hours; whether the CFO states a cap and uses the P95 table at the lock window; the share chosen; realised cost against full fixed per delivery year.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
