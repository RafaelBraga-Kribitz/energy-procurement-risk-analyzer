"""Every unimplemented module fails LOUDLY with its milestone (AGENTS.md M0 rule).

When a milestone gets implemented, delete its rows here — this file should be
empty by M7.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

import pandas as pd
import pytest

from epra.analytics import descriptive, regimes, spread, weather
from epra.common.config import load_consumer_profile, load_settings, load_strategy_config
from epra.consumer import profile
from epra.ingest import calendar as cal
from epra.ingest import geosphere, oespi, validate
from epra.report import charts
from epra.strategies import calibration, forward_risk, retrospective

SETTINGS = load_settings()

STUBS: list[tuple[str, Callable[..., Any], tuple[Any, ...]]] = [
    ("M1", validate.run_gates, (SETTINGS,)),
    ("M1", validate.main, ([],)),
    ("M2", geosphere.discover_station, (SETTINGS,)),
    ("M2", geosphere.ingest, (SETTINGS, date(2019, 1, 1), date(2019, 2, 1))),
    ("M2", geosphere.main, ([],)),
    ("M2", oespi.load_oespi, (SETTINGS,)),
    ("M2", oespi.main, ([],)),
    ("M2", cal.build_calendar, (SETTINGS,)),
    ("M2", cal.main, ([],)),
    ("M4", profile.build_profile, (pd.DataFrame(), load_consumer_profile())),
    ("M4", profile.monthly_volumes, (pd.DataFrame(),)),
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
