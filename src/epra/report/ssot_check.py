"""GV-303 checker: README/EXEC_SUMMARY literals must match SSOT (ADR-016).

Uses ``decimal.Decimal`` ``ROUND_HALF_UP`` — never Python ``round``.
Missing ``NUMERIC_SSOT.md`` skips GV-302 completeness and still scans docs.

Implements: GV-303, ADR-016, D-17, D-18, EN-080.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from epra.common.config import REPO_ROOT
from epra.report.ssot import missing_gv302_keys

logger = logging.getLogger(__name__)

UNITS = ("EUR/MWh", "hours", "EUR", "%", "M")
TOKEN_RE = re.compile(
    r"€?\s*(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)\s*"
    rf"({'|'.join(UNITS)})(?![\w/])"
)
WHITELIST_NAME = "ssot_whitelist.txt"
SSOT_REL = Path("reports") / "NUMERIC_SSOT.md"
README_REL = Path("README.md")
EXEC_REL = Path("reports") / "EXEC_SUMMARY.md"


@dataclass(frozen=True)
class DocToken:
    """One number+unit bigram from a scanned document."""

    literal: str
    unit: str
    source: str


@dataclass(frozen=True)
class SSotRow:
    """One NUMERIC_SSOT markdown row (numeric ``value`` when parseable)."""

    key: str
    value: Decimal | None
    unit: str
    raw: str


def round_half_up(value: Decimal, decimals: int) -> Decimal:
    """Half-up quantize to ``decimals`` places (ADR-016).

    Implements: GV-303, ADR-016.
    """
    quant = Decimal("1").scaleb(-decimals)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def displayed_decimals(literal: str) -> int:
    if "." in literal:
        return len(literal.split(".", 1)[1])
    return 0


def parse_whitelist(path: Path) -> dict[str, str]:
    """Require ``token # reason`` on every data line.

    Implements: GV-303.
    """
    mapping: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "#" not in stripped:
            raise ValueError(f"{path}:{i} whitelist entry missing # reason")
        token, reason = stripped.split("#", 1)
        token, reason = token.strip(), reason.strip()
        if not token or not reason:
            raise ValueError(f"{path}:{i} whitelist token and reason are required")
        mapping[token] = reason
    return mapping


def tokenize(text: str, source: str) -> list[DocToken]:
    """Number + unit bigrams (EUR, EUR/MWh, %, hours, M)."""
    found: list[DocToken] = []
    for match in TOKEN_RE.finditer(text):
        literal = match.group(1).replace(",", "")
        found.append(DocToken(literal=literal, unit=match.group(2), source=source))
    return found


def is_whitelisted(token: DocToken, whitelist: dict[str, str]) -> bool:
    candidates = (
        token.literal,
        f"{token.literal} {token.unit}",
        f"{token.literal}{token.unit}",
    )
    return any(item in whitelist for item in candidates)


def parse_ssot_markdown(text: str) -> list[SSotRow]:
    """Parse the GV-301 pipe table. Non-numeric values stay ``value=None``."""
    rows: list[SSotRow] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"key", "---"} or set(cells[0]) <= {"-"}:
            continue
        raw = cells[1]
        unit = cells[2] if len(cells) > 2 else ""
        number: Decimal | None
        try:
            number = Decimal(raw.replace(",", ""))
        except InvalidOperation:
            number = None
        rows.append(SSotRow(key=cells[0], value=number, unit=unit, raw=raw))
    return rows


def _comparable(ssot: SSotRow, unit: str) -> Decimal | None:
    if ssot.value is None:
        return None
    if unit == ssot.unit:
        return ssot.value
    if unit == "M" and ssot.unit == "EUR":
        return ssot.value / Decimal("1000000")
    if unit == "%" and ssot.unit in {"share", "1"}:
        return ssot.value * Decimal(100)
    return None


def match_token(token: DocToken, rows: Sequence[SSotRow]) -> SSotRow | None:
    """Return the first SSOT row whose half-up rounding equals the literal."""
    lit = Decimal(token.literal)
    decimals = displayed_decimals(token.literal)
    for row in rows:
        comparable = _comparable(row, token.unit)
        if comparable is None:
            continue
        if lit == round_half_up(comparable, decimals):
            return row
    return None


def _candidates(token: DocToken, rows: Sequence[SSotRow]) -> list[str]:
    names: list[str] = []
    for row in rows:
        if _comparable(row, token.unit) is not None:
            names.append(f"{row.key}={row.raw} {row.unit}")
    return names[:8]


def scan_docs(
    tokens: Sequence[DocToken],
    rows: Sequence[SSotRow],
    whitelist: dict[str, str],
    *,
    ssot_present: bool,
) -> list[str]:
    errors: list[str] = []
    for token in tokens:
        if is_whitelisted(token, whitelist):
            continue
        if not ssot_present:
            errors.append(
                f"{token.source}: unmatched {token.literal} {token.unit} "
                "(NUMERIC_SSOT.md missing; token not on whitelist)"
            )
            continue
        hit = match_token(token, rows)
        if hit is None:
            cand = ", ".join(_candidates(token, rows)) or "(no same-unit SSOT rows)"
            errors.append(
                f"{token.source}: unmatched {token.literal} {token.unit}; "
                f"candidates: {cand}"
            )
    return errors


def _read_optional(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def check(
    *,
    repo_root: Path | None = None,
    readme_path: Path | None = None,
    exec_path: Path | None = None,
    ssot_path: Path | None = None,
    whitelist_path: Path | None = None,
    check_gv302: bool | None = None,
) -> int:
    """Return 0 if docs match SSOT / whitelist. Implements: GV-303, D-18."""
    root = repo_root or REPO_ROOT
    readme_path = readme_path or root / README_REL
    exec_path = exec_path or root / EXEC_REL
    ssot_path = ssot_path or root / SSOT_REL
    whitelist_path = whitelist_path or root / "scripts" / WHITELIST_NAME
    whitelist = parse_whitelist(whitelist_path)
    tokens: list[DocToken] = []
    if readme_path.is_file():
        tokens.extend(tokenize(readme_path.read_text(encoding="utf-8"), str(readme_path)))
    exec_text = _read_optional(exec_path)
    if exec_text is not None:
        tokens.extend(tokenize(exec_text, str(exec_path)))
    ssot_text = _read_optional(ssot_path)
    rows: list[SSotRow] = parse_ssot_markdown(ssot_text) if ssot_text is not None else []
    ssot_present = ssot_text is not None
    if not ssot_present:
        logger.info("GV-302 completeness skipped: %s missing", ssot_path)
    if check_gv302 is None:
        check_gv302 = ssot_present
    errors: list[str] = []
    if check_gv302 and ssot_present:
        missing = missing_gv302_keys(row.key for row in rows)
        if missing:
            errors.append(f"GV-302 missing keys: {missing}")
    errors.extend(scan_docs(tokens, rows, whitelist, ssot_present=ssot_present))
    for err in errors:
        print(err, file=sys.stderr)
    return 1 if errors else 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI used by ``scripts/check_ssot_consistency.py``."""
    from epra.common.logging import setup

    parser = argparse.ArgumentParser(prog="python -m epra.report.ssot_check")
    parser.parse_args(argv)
    setup()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
