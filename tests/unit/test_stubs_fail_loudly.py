"""Every unimplemented module fails LOUDLY with its milestone (AGENTS.md M0 rule).

When a milestone gets implemented, delete its rows here — this file should be
empty by M7. Arguments are built lazily inside the test so importing this
module never reads config (collection stays side-effect free).
"""

import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pandas as pd
import pytest

from epra.analytics import descriptive, regimes, spread, weather
from epra.common.config import (
    REPO_ROOT,
    load_consumer_profile,
    load_settings,
    load_strategy_config,
)
from epra.consumer import profile
from epra.report import charts
from epra.strategies import calibration, forward_risk, retrospective


def _script(name: str) -> ModuleType:
    """Import `scripts/<name>.py` (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(name, Path(REPO_ROOT, "scripts", f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STUBS: list[tuple[str, str, Callable[[], Any]]] = [
    (
        "M4",
        "profile.build_profile",
        lambda: profile.build_profile(pd.DataFrame(), load_consumer_profile()),
    ),
    ("M4", "profile.monthly_volumes", lambda: profile.monthly_volumes(pd.DataFrame())),
    ("M5", "descriptive.run", lambda: descriptive.run(load_settings())),
    ("M5", "spread.run", lambda: spread.run(load_settings())),
    ("M5", "regimes.run", lambda: regimes.run(load_settings())),
    ("M5", "weather.run", lambda: weather.run(load_settings())),
    (
        "M6",
        "calibration.compute_anchors",
        lambda: calibration.compute_anchors(load_settings(), load_strategy_config()),
    ),
    ("M6", "retrospective.run", lambda: retrospective.run(load_settings())),
    ("M6", "retrospective.main", lambda: retrospective.main([])),
    ("M6", "forward_risk.run", lambda: forward_risk.run(load_settings())),
    ("M6", "forward_risk.main", lambda: forward_risk.main([])),
    (
        "M7",
        "charts.render_executive_charts",
        lambda: charts.render_executive_charts(load_settings()),
    ),
    ("M6", "scripts/generate_ssot.py", lambda: _script("generate_ssot").main([])),
    ("M6", "scripts/check_ssot_consistency.py", lambda: _script("check_ssot_consistency").main([])),
    (
        "M4",
        "scripts/generate_golden_metrics.py",
        lambda: _script("generate_golden_metrics").main([]),
    ),
    ("M7", "scripts/export_marts.py", lambda: _script("export_marts").main([])),
]


@pytest.mark.parametrize(("milestone", "name", "call"), STUBS, ids=[n for _, n, _ in STUBS])
def test_stub_raises_not_implemented_naming_its_milestone(
    milestone: str, name: str, call: Callable[[], Any]
) -> None:
    with pytest.raises(NotImplementedError, match=milestone):
        call()
