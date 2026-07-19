"""Pre-commit guard: no ENTSO-E token literal anywhere in the repo (EN-003, A-7).

Flags ``securityToken=`` followed by a literal value (anything that is not an
env-var/format placeholder). The token must exist ONLY as the ENTSOE_API_TOKEN
environment variable (ING-021).

Usage: ``python scripts/check_no_token_in_code.py <file> [<file> ...]``
Exit 1 if any file contains a violation.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

# A literal token after securityToken= — but NOT ${...}, {placeholder}, os.environ, etc.
_TOKEN_LITERAL = re.compile(r"securityToken=(?![{$*<%])[A-Za-z0-9][A-Za-z0-9\-]{7,}")


def check_file(path: Path) -> list[str]:
    """Return violation descriptions ('file:line') for one file."""
    if path.name == Path(__file__).name:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return [
        f"{path}:{lineno}"
        for lineno, line in enumerate(text.splitlines(), start=1)
        if _TOKEN_LITERAL.search(line)
    ]


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    violations: list[str] = []
    for name in args:
        violations.extend(check_file(Path(name)))
    if violations:
        print("ERROR: possible ENTSO-E token literal found (A-7 — rotate the token!):")
        for v in violations:
            print(f"  {v}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
