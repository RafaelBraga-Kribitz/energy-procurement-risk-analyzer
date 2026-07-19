"""Forward risk engine — seasonal block bootstrap, next 12 months (M6, Q3).

Not yet implemented. Binding contract: SPEC-05 §6 (ST-401..406). The algorithm
is spelled out verbatim in ST-401 — implement it EXACTLY. Critical points:

- One seeded RNG for the whole engine: ``numpy.random.default_rng(seed=42)``,
  draws in deterministic loop order (seed from config, ST-405 determinism test).
- Trap T-6: a drawn month brings its hourly PRICES and its ÖSPI values
  TOGETHER — drawing them independently destroys the spot/contract correlation
  the whole comparison rests on.
- Implement the VECTORIZED design directly (ST-406): precompute per-(calendar
  month, historical year) strategy cost cells (~600), then bootstrap over cost
  cells — mathematically identical because costs are additive over months.
- Secondary output: no-crisis conditional variant (year pool restricted via
  the A3 HMM December regime, ST-401 step 4). Report both.
- Outputs (tag SIMULATED): mean/std/P5/P50/P95/CVaR95 per strategy →
  forward_risk_summary (exports + SSOT), ``s5_forward_fan.png``,
  ``s5_risk_return.png`` (ST-403..404). CVaR95 = mean of the HIGHEST-cost 5%.

Implements (when built): ST-401..406, ST-603.
"""

from __future__ import annotations

from collections.abc import Sequence

from epra.common.config import Settings

_MSG = "M6 not implemented yet — build per SPEC-05 §6 (see module docstring)"


def run(settings: Settings) -> None:
    """Simulate N seeded paths; write forward_risk_summary + charts."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.strategies.forward_risk`` (ST-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
