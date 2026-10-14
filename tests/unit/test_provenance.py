"""Fixture-run marker and banner (ADR-018 safeguard for A-2)."""

from __future__ import annotations

from epra.common.config import Settings
from epra.common.provenance import (
    FIXTURE_BANNER,
    banner_lines,
    fixture_marker_path,
    is_fixture_run,
)


def test_banner_only_on_fixture_runs(tmp_settings: Settings) -> None:
    assert not is_fixture_run(tmp_settings)
    assert banner_lines(tmp_settings) == []
    marker = fixture_marker_path(tmp_settings)
    marker.parent.mkdir(parents=True)
    marker.write_text("synthetic", encoding="utf-8")
    assert is_fixture_run(tmp_settings)
    assert FIXTURE_BANNER in banner_lines(tmp_settings)[0]
