"""M0 smoke test (AGENTS.md M0)."""

import epra


def test_package_imports_and_has_version() -> None:
    assert epra.__version__
