"""The Markdown dead-link checker finds missing files and anchors."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from epra.common.config import REPO_ROOT

_SPEC = importlib.util.spec_from_file_location(
    "check_links", REPO_ROOT / "scripts" / "check_links.py"
)
assert _SPEC is not None and _SPEC.loader is not None
LINKS = importlib.util.module_from_spec(_SPEC)
sys.modules["check_links"] = LINKS
_SPEC.loader.exec_module(LINKS)


def test_detects_missing_file_and_anchor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(LINKS, "REPO_ROOT", tmp_path)
    (tmp_path / "ok.md").write_text("# Title\n", encoding="utf-8")
    doc = tmp_path / "doc.md"
    doc.write_text(
        "# Project status\n[a](ok.md) [b](gone.md) [c](#project-status) [d](#nope) "
        "[e](https://example.com)\n```\n[f](inside-code.md)\n```\n",
        encoding="utf-8",
    )
    problems = LINKS.broken_links(doc)
    assert problems == ["doc.md: missing target gone.md", "doc.md: missing anchor #nope"]
