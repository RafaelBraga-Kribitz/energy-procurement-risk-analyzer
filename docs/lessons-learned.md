# Lessons learned: Energy Procurement Risk Analyzer

Evaluation: [economic-evaluation.md](economic-evaluation.md).

## Expectations against actuals (as of 2026-10-30)

| Item | Expected (evaluation) | Actual | Evidence |
|---|---|---|---|
| Effort | 92 h central (46 to 138 h), the charter's 11.5-day budget | Unmeasured: no time log. Commit days × 4 h gives 60 h; the session-span check gives 32 h | cost basis v1.2, hours table; `PROJECT_CHARTER.md` §7 |
| Total cost | €6,373 central, with 3 years of maintenance and 16 h implementation | Unmeasured; maintenance and implementation not yet incurred | same |
| Technical performance | A P95 per fixed share that separates the adverse state | First real-data run on 2026-10-28. Next 12 months: Fixed annual has the lowest mean, €4.77M; Hybrid 70 % fixed the lowest P95, €6.44M against €6.61M (SIMULATED) | `reports/NUMERIC_SSOT.md`; merge of `data/first-real-data-run` |
| Adoption | Inside f = 0.35 | Unmeasured: the consumer is a reference case; no buyer on record | `README.md` |
| Operational outcome | A fixed share chosen against a stated cap | Unmeasured | none |
| Attributable value | €77k gross expected over 3 years | Unmeasured | none |

## Lessons

**L-EPRA-1. Check the sign of the expected-cost gap on a quick backtest before valuing a hedge cut.** Scope: procurement evaluations. The evaluation valued cutting the fixed share as premium saved. On real data, full spot has a higher expected cost than Fixed annual (€5.36M against €4.77M, SIMULATED), so that saving did not appear. Evidence: `reports/NUMERIC_SSOT.md`, `mean_next12m_S1` and `mean_next12m_S3`. Date: 2026-10-30.

**L-EPRA-2. Ask for the buyer's tail cap before modelling.** Scope: risk-trade-off tools. Hybrid 70 % fixed costs €0.18M more in expectation for a €0.17M lower P95, so the choice turns on the CFO's cap, not on the model. Evidence: `reports/NUMERIC_SSOT.md`, `mean_next12m_S4_70`, `p95_next12m_S4_70`, `p95_next12m_S3`. Date: 2026-10-30.

**L-EPRA-3. Run the real data first when the decision has a deadline.** Scope: decisions tied to a lock window. The first real-data result came 101 days after the first commit; fixed prices lock in the year's second half. Evidence: `git log`, first commit 2026-07-19, real-data merge 2026-10-28. Date: 2026-10-30.
