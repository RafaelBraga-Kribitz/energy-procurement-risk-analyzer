# Forward risk, next 12 months (Q3/Q4)

*Contract prices proxied via ÖSPI (futures-based index); premiums are calibrated assumptions — see LIMITATIONS.*

*Reference load profile is constructed (CALIBRATED), not measured; construction rules in SPEC-03.*

Window 2026-10..2027-09; 2,000 seeded bootstrap paths per variant; costs in EUR million (SIMULATED). `no_crisis` limits the pool to years whose December HMM regime is not `crisis` (ST-401 step 4).

| variant | strategy | mean | std | p5 | p50 | p95 | cvar95 |
|---|---|---:|---:|---:|---:|---:|---:|
| unconditional | Full spot | 5.36 | 1.18 | 3.65 | 5.25 | 7.56 | 8.24 |
| unconditional | ÖSPI-indexed | 5.15 | 1.16 | 3.47 | 5.03 | 7.16 | 7.88 |
| unconditional | Fixed annual | 4.77 | 0.88 | 3.75 | 4.51 | 6.61 | 6.96 |
| unconditional | Hybrid 30% fixed | 5.18 | 0.93 | 3.80 | 5.07 | 6.85 | 7.37 |
| unconditional | Hybrid 50% fixed | 5.06 | 0.82 | 3.84 | 4.98 | 6.61 | 6.97 |
| unconditional | Hybrid 70% fixed | 4.95 | 0.78 | 3.88 | 4.82 | 6.44 | 6.80 |
| no_crisis | Full spot | 3.83 | 0.49 | 3.03 | 3.82 | 4.64 | 4.80 |
| no_crisis | ÖSPI-indexed | 4.98 | 1.08 | 3.38 | 4.87 | 6.96 | 7.52 |
| no_crisis | Fixed annual | 4.26 | 0.40 | 3.64 | 4.24 | 5.01 | 5.17 |
| no_crisis | Hybrid 30% fixed | 3.96 | 0.39 | 3.30 | 3.95 | 4.61 | 4.73 |
| no_crisis | Hybrid 50% fixed | 4.04 | 0.35 | 3.47 | 4.05 | 4.65 | 4.76 |
| no_crisis | Hybrid 70% fixed | 4.13 | 0.35 | 3.57 | 4.14 | 4.71 | 4.86 |

## Q4 — what a CFO would choose

A cost-minimizing buyer picks **Fixed annual** (lowest expected cost). A risk-averse buyer picks **Hybrid 70% fixed** (lowest P95). The tail protection costs €0.18 M in expected cost and lowers the P95 by €0.17 M (SIMULATED).
