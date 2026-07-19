"""Retrospective engine — what each strategy actually cost, 2021-2025 (M6, Q1).

Not yet implemented. Binding contract: SPEC-05 §3 (strategy formulas S1-S4),
§5 (ST-301..304). Non-negotiables:

- S1 hourly join on ts_utc; NULL-price hours dropped from ALL strategies'
  volume identically for fair comparison (ST-101, ST-501).
- S2 monthly ÖSPI-indexed blend with w_peak = consumer_peak_share read from
  SSOT inputs, never retyped (ST-102..104).
- S3 lock rule: H2 of year Y−1 ÖSPI means + fixed premium; NO other lookahead
  (ST-105..106, ST-503 has a dedicated no-lookahead test).
- S4 hybrids reuse S1's spot leg scaled by (1−h) (ST-107).
- Headline: wrong_strategy_cost per year and 5-year total → SSOT (ST-302).
- Sensitivities EXACTLY three: premium {0,5,10}, flat_baseload profile, full
  prior-year lock window (ST-303 — scope guard, no more).
- Output parquet ``data/processed/strategy_costs_monthly.parquet`` re-exposed
  by dbt as ``fct_procurement_cost_monthly`` (ST-001); dbt never computes costs.
- Gate ST-602(a): if 2022 cost_S1 ≤ cost_S3, the ÖSPI translation is broken —
  stop and debug, do not rationalize.

Every S2/S3/S4 output caption carries the ST-502 proxy sentence.

Implements (when built): ST-101..107, ST-301..304, ST-501..503, ST-601..602.
"""

from __future__ import annotations

from collections.abc import Sequence

from epra.common.config import Settings

_MSG = "M6 not implemented yet — build per SPEC-05 §§3-5 (see module docstring)"


def run(settings: Settings) -> None:
    """Compute cost(strategy, year, month) for 2021-2025 + sensitivities."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.retrospective`` (ST-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
