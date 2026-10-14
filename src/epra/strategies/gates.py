"""ST-602 sanity relations — hard assertions on the simulator outputs (M6 gate).

(a) in 2022, cost_S1 > cost_S3 (spot was catastrophic vs pre-crisis locks);
(b) every year, min(S1, S3) ≤ cost_S4_50 ≤ max(S1, S3) within ±0.5 %;
(c) forward risk, unconditional pool: P95(S1) ≥ P95(S3).

If (a) fails the ÖSPI translation is broken: stop and debug, never rationalize.

Implements: ST-602.
"""

from __future__ import annotations

import pandas as pd

from epra.common.frames import scalar

CRISIS_YEAR = 2022  # ST-602 (a)
HYBRID_TOLERANCE = 0.005  # ST-602 (b): ±0.5 % for the premium


def sanity_failures(annual: pd.DataFrame, forward: pd.DataFrame) -> list[str]:
    """Human-readable ST-602 violations; empty list = gate passes.

    Implements: ST-602.
    """
    failures: list[str] = []
    cost = annual.pivot(index="year", columns="strategy_id", values="cost_eur")
    if CRISIS_YEAR in cost.index and not (
        scalar(cost, CRISIS_YEAR, "S1") > scalar(cost, CRISIS_YEAR, "S3")
    ):
        failures.append("(a) 2022 cost_S1 <= cost_S3 — ÖSPI translation suspect (T-5)")
    for year, row in cost.iterrows():
        low = min(row["S1"], row["S3"]) * (1 - HYBRID_TOLERANCE)
        high = max(row["S1"], row["S3"]) * (1 + HYBRID_TOLERANCE)
        if not low <= row["S4_50"] <= high:
            failures.append(f"(b) {year}: S4_50 outside [min(S1,S3), max(S1,S3)] ±0.5%")
    p95 = forward[forward["variant"] == "unconditional"].set_index("strategy_id")["p95"]
    if not float(p95["S1"]) >= float(p95["S3"]):
        failures.append("(c) forward P95(S1) < P95(S3)")
    return failures
