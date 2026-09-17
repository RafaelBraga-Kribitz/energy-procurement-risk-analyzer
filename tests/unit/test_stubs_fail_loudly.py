"""Every unimplemented module fails LOUDLY with its milestone (AGENTS.md M0 rule).

When a milestone gets implemented, delete its rows here — this file should be
empty by M7.
"""

from collections.abc import Callable
from typing import Any

import pytest

from epra.common.config import load_settings
from epra.report import charts

SETTINGS = load_settings()

STUBS: list[tuple[str, Callable[..., Any], tuple[Any, ...]]] = [
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
