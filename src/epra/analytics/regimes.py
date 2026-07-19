"""A3 — Volatility regimes: HMM + GARCH complement (M5, build LAST).

Not yet implemented. Binding contract: SPEC-04 A3 (AN-301..304). Critical
choices already made by the spec — do not re-litigate:

- Basis series: DAILY arithmetic differences of base price (NOT log returns —
  prices can be ≤ 0; trap T-3).
- HMM: ``hmmlearn`` GaussianHMM(n_components=3, covariance_type='full',
  n_iter=500), 10 seeded restarts random_state=42..51, keep best
  log-likelihood; label states by ascending std: calm/elevated/crisis.
  Determinism (AN-705) depends on the fixed restart seeds.
- GARCH(1,1) on d_t via ``arch``; report persistence α+β to SSOT
  (``garch_persistence``, VERIFIED); α+β ≥ 1 is REPORTED, not "fixed".
- SANITY GATE AN-304 (M5 exit): ≥ 70% of 2021-09..2023-06 days in top-2 vol
  states; ≥ 60% of 2019 days calm. Widening requires an ADR.

Implements (when built): AN-301..304.
"""

from __future__ import annotations

from epra.common.config import Settings

_MSG = "M5 not implemented yet — build per SPEC-04 A3 (see module docstring)"


def run(settings: Settings) -> None:
    """Produce all A3 artifacts from marts; seeded, deterministic (AN-705)."""
    raise NotImplementedError(_MSG)
