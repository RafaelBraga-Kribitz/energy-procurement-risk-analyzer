# Forward risk, next 12 months (Q3/Q4)

> **FIXTURE RUN — built on SYNTHETIC CI fixture prices (ADR-018), not on real ENTSO-E data. Every number here exercises the pipeline only and is NOT a result.**

*Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated assumptions — see LIMITATIONS.*

*Reference load profile is constructed (CALIBRATED), not measured; construction rules in SPEC-03.*

Window 2026-10..2027-09; 2,000 seeded bootstrap paths per variant; costs in EUR million (SIMULATED). `no_crisis` limits the pool to years whose December HMM regime is not `crisis` (ST-401 step 4).

| variant | strategy | mean | std | p5 | p50 | p95 | cvar95 |
|---|---|---:|---:|---:|---:|---:|---:|
| unconditional | Full spot | 4.06 | 0.96 | 2.73 | 3.96 | 5.81 | 6.35 |
| unconditional | ÖSPI-indexed | 4.39 | 0.98 | 2.97 | 4.30 | 6.10 | 6.72 |
| unconditional | Fixed annual | 4.12 | 0.75 | 3.25 | 3.90 | 5.68 | 5.98 |
| unconditional | Hybrid 30% fixed | 4.08 | 0.81 | 2.96 | 3.99 | 5.62 | 6.01 |
| unconditional | Hybrid 50% fixed | 4.09 | 0.75 | 3.08 | 4.01 | 5.51 | 5.87 |
| unconditional | Hybrid 70% fixed | 4.10 | 0.72 | 3.18 | 3.93 | 5.52 | 5.85 |
| no_crisis | Full spot | 3.15 | 0.57 | 2.35 | 3.07 | 4.22 | 4.50 |
| no_crisis | ÖSPI-indexed | 3.93 | 0.91 | 2.63 | 3.83 | 5.57 | 5.98 |
| no_crisis | Fixed annual | 3.64 | 0.32 | 3.21 | 3.56 | 4.24 | 4.41 |
| no_crisis | Hybrid 30% fixed | 3.30 | 0.43 | 2.67 | 3.25 | 4.08 | 4.30 |
| no_crisis | Hybrid 50% fixed | 3.40 | 0.36 | 2.87 | 3.36 | 4.03 | 4.21 |
| no_crisis | Hybrid 70% fixed | 3.49 | 0.31 | 3.05 | 3.46 | 4.07 | 4.21 |

## Q4 — what a CFO would choose

A cost-minimizing buyer picks **Full spot** (lowest expected cost). A risk-averse buyer picks **Hybrid 50% fixed** (lowest P95). The tail protection costs €0.03 M in expected cost and lowers the P95 by €0.30 M (SIMULATED).
