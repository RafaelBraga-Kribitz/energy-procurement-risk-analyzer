# Headline queries in plain SQL

The answers to Q1 and Q3, written as readable DuckDB SQL over the warehouse
marts and the simulator's processed outputs. They are not a second engine:
`tests/unit/test_strategies.py::test_sql_headline_queries_match_python` runs
each file and asserts it reproduces the Python results exactly.

| File | Answers |
|---|---|
| `q1_annual_strategy_cost_matrix.sql` | Q1: annual energy cost and EUR/MWh per strategy, 2021-2025 |
| `q1_wrong_strategy_cost.sql` | Q1 headline: yearly gap between dearest and cheapest strategy + 5-year total |
| `q3_forward_risk_p95_cvar95.sql` | Q3: mean, P5, P50, P95, CVaR95 of the next-12-month cost per strategy |
| `dq_coverage_by_year.sql` | Data quality: coverage, DST days, PT15M hours, negative hours per year |

Run one against your warehouse (after `make all`):

```bash
uv run python scripts/run_sql.py sql/q1_wrong_strategy_cost.sql
```

`{processed}` is replaced by the absolute `data/processed` path.
