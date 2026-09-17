"""Every unimplemented module fails LOUDLY with its milestone (AGENTS.md M0 rule).

When a milestone gets implemented, delete its rows here — this file should be
empty by M7.
"""

from collections.abc import Callable
from typing import Any

import pytest

from epra.analytics import descriptive, regimes, spread, weather
from epra.common.config import load_settings, load_strategy_config
from epra.report import charts
from epra.strategies import calibration, forward_risk, retrospective

SETTINGS = load_settings()

STUBS: list[tuple[str, Callable[..., Any], tuple[Any, ...]]] = [
    ("M5", descriptive.run, (SETTINGS,)),
    ("M5", spread.run, (SETTINGS,)),
    ("M5", regimes.run, (SETTINGS,)),
    ("M5", weather.run, (SETTINGS,)),
    ("M6", calibration.compute_anchors, (SETTINGS, load_strategy_config())),
    ("M6", retrospective.run, (SETTINGS,)),
    ("M6", retrospective.main, ([],)),
    ("M6", forward_risk.run, (SETTINGS,)),
    ("M6", forward_risk.main, ([],)),
    ("M7", charts.render_executive_charts, (SETTINGS,)),
]


@pytest.mark.parametrize(
    ("milestone", "func", "args"),
    STUBS,
    ids=[f"{m}-{f.__module__}.{f.__name__}" for m, f, _ in STUBS],
)
def test_stub_raises_not_implemented_naming_its_milestone(
    milestone: str, func: Callable[..., Any], args: tuple[Any, ...]
) -> None:
    with pytest.raises(NotImplementedError, match=milestone):
        func(*args)
