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

import pytest

from epra.common.config import REPO_ROOT, load_settings
from epra.report import charts


def _script(name: str) -> ModuleType:
    """Import `scripts/<name>.py` (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(name, Path(REPO_ROOT, "scripts", f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STUBS: list[tuple[str, str, Callable[[], Any]]] = [
    (
        "M7",
        "charts.render_executive_charts",
        lambda: charts.render_executive_charts(load_settings()),
    ),
    ("M7", "scripts/export_marts.py", lambda: _script("export_marts").main([])),
]


@pytest.mark.parametrize(("milestone", "name", "call"), STUBS, ids=[n for _, n, _ in STUBS])
def test_stub_raises_not_implemented_naming_its_milestone(
    milestone: str, name: str, call: Callable[[], Any]
) -> None:
    with pytest.raises(NotImplementedError, match=milestone):
        call()
