"""Dead-link check for tracked Markdown: relative paths and in-page anchors.

External http(s) links are listed but not fetched (CI stays network-free,
EN-070). Exit 1 on any relative link to a missing file or a missing heading
anchor in the same document.

Usage: ``uv run python scripts/check_links.py``  (``make linkcheck``)
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)|src=\"([^\"]+)\"")
SKIP_PREFIXES = ("http://", "https://", "mailto:")
#: Planning/history trees reference files from other sessions and machines.
SKIP_DIRS = (".planning/",)


def anchors(text: str) -> set[str]:
    """GitHub-style anchors of every heading in ``text``."""
    out = set()
    for line in text.splitlines():
        if line.startswith("#"):
            title = line.lstrip("#").strip().lower()
            slug = re.sub(r"[^\w\- ]", "", title).replace(" ", "-")
            out.add(slug)
    return out


def broken_links(path: Path) -> list[str]:
    """Problems in one Markdown file."""
    text = path.read_text(encoding="utf-8")
    problems = []
    in_code = False
    lines = []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            lines.append(line)
    for match in LINK.finditer("\n".join(lines)):
        target = next(g for g in match.groups() if g)
        if target.startswith(SKIP_PREFIXES):
            continue
        file_part, _, anchor = target.partition("#")
        if not file_part:
            if anchor and anchor not in anchors(text):
                problems.append(f"{path.relative_to(REPO_ROOT)}: missing anchor #{anchor}")
            continue
        resolved = (path.parent / file_part).resolve()
        if not resolved.exists():
            problems.append(f"{path.relative_to(REPO_ROOT)}: missing target {target}")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Check every tracked .md file."""
    del argv
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.split()
    files = [REPO_ROOT / f for f in tracked if not f.startswith(SKIP_DIRS)]
    problems = [p for f in files for p in broken_links(f)]
    for problem in problems:
        print(f"ERROR: {problem}", file=sys.stderr)
    print(f"checked {len(files)} markdown files; {len(problems)} broken links")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
