"""ST-601: recompute synthetic annual matrix vs committed golden JSON.

The golden is an engine regression contract (D-19), not Austrian market evidence.

Implements: ST-601, D-19.
"""

from __future__ import annotations

import json
from pathlib import Path

from epra.strategies._golden import synthetic_annual_payload

GOLDEN = Path(__file__).resolve().parent / "golden" / "strategy_annual_summary.json"


def test_st601_annual_matrix_matches_golden() -> None:
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    actual = synthetic_annual_payload()
    assert "Not Austrian market evidence" in str(expected["disclaimer"])
    assert actual["disclaimer"] == expected["disclaimer"]
    assert actual["rows"] == expected["rows"]
    by_id = {row["strategy_id"]: row for row in actual["rows"]}
    assert by_id["S1"]["cost_eur"] == 120.0
    assert by_id["S3"]["cost_eur"] == 100.0
    assert by_id["S3"]["rank"] == 1
    assert by_id["S1"]["delta_vs_min_eur"] == 20.0
