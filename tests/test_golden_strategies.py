"""ST-601 golden metrics test: the annual cost matrix of the closed-form golden
inputs must equal ``tests/golden/strategy_annual_summary.json``.

A legitimate formula change regenerates the golden in the same PR via
``scripts/generate_golden_metrics.py --target strategies`` with an explanation
(AGENTS.md §2 item 6).

Implements tests for: ST-601.
"""

from __future__ import annotations

import importlib.util
import json
from types import ModuleType

import pandas as pd

from epra.common.config import REPO_ROOT


def _golden_script() -> ModuleType:
    path = REPO_ROOT / "scripts" / "generate_golden_metrics.py"
    spec = importlib.util.spec_from_file_location("generate_golden_metrics", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_st601_annual_matrix_matches_golden() -> None:
    script = _golden_script()
    expected = pd.DataFrame(json.loads(script.STRATEGY_GOLDEN.read_text(encoding="utf-8")))
    actual = script.golden_annual_summary()
    pd.testing.assert_frame_equal(
        actual.reset_index(drop=True), expected, check_dtype=False, rtol=1e-9
    )


def test_st601_golden_respects_st602_relations() -> None:
    from epra.strategies.gates import sanity_failures

    annual = _golden_script().golden_annual_summary()
    forward = pd.DataFrame(
        {"variant": "unconditional", "strategy_id": ["S1", "S3"], "p95": [2.0, 1.0]}
    )
    assert sanity_failures(annual, forward) == []
