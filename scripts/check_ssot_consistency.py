"""CI gate GV-303: README/EXEC_SUMMARY numbers must match the SSOT.

Scans README.md and reports/EXEC_SUMMARY.md for numeric literals adjacent to
SSOT units and requires each to equal some SSOT row of the same unit within
the literal's own rounding:

=====================  ===========================  ==========================
written as             compared with SSOT unit      tolerance
=====================  ===========================  ==========================
``€16.59 M``           EUR (value × 1,000,000)      half a unit of the last
``€1,234,567`` /       EUR                          written decimal place
``1,234 EUR``
``52.5 EUR/MWh``       EUR/MWh
``42.3%``              share (× 100) or ``%``
``266 hours``          hours
=====================  ===========================  ==========================

README may round; the SSOT keeps full precision. Non-result numerics with a
unit go in ``scripts/ssot_whitelist.txt`` (one literal per line, each with an
inline ``# why`` comment). Freshness (SPEC-08 §4): the results digest embedded
by ``generate_ssot.py`` must match the committed results CSVs.

Implements: GV-303, E-3, SPEC-08 §4.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SSOT_PATH = REPO_ROOT / "reports" / "NUMERIC_SSOT.md"
DOCS = (REPO_ROOT / "README.md", REPO_ROOT / "reports" / "EXEC_SUMMARY.md")
WHITELIST = REPO_ROOT / "scripts" / "ssot_whitelist.txt"
NUM = r"(-?\d[\d,]*(?:\.\d+)?)"
PATTERNS: tuple[tuple[str, str, float], ...] = (
    (rf"€\s?{NUM}\s?M\b", "EUR", 1e6),
    (rf"{NUM}\s?EUR/MWh", "EUR/MWh", 1.0),
    (rf"€\s?{NUM}(?!\s?M\b)(?![\d,.])", "EUR", 1.0),
    (rf"{NUM}\s?EUR\b(?!/)", "EUR", 1.0),
    (rf"{NUM}\s?%", "%", 1.0),
    (rf"{NUM}\s?hours\b", "hours", 1.0),
)


@dataclass(frozen=True)
class Literal:
    """One unit-bearing number found in a document."""

    text: str
    value: float
    unit: str
    tolerance: float
    where: str


def _decimals(number: str) -> int:
    return len(number.split(".")[1]) if "." in number else 0


def find_literals(text: str, where: str) -> list[Literal]:
    """All unit-bearing numbers in ``text`` (first matching pattern wins per span)."""
    found: list[Literal] = []
    taken: list[tuple[int, int]] = []
    for pattern, unit, scale in PATTERNS:
        for match in re.finditer(pattern, text):
            span = match.span()
            if any(s < span[1] and span[0] < e for s, e in taken):
                continue
            taken.append(span)
            raw = match.group(1)
            value = float(raw.replace(",", "")) * scale
            tolerance = 0.5 * 10 ** (-_decimals(raw)) * scale + 1e-9
            found.append(Literal(match.group(0), value, unit, tolerance, where))
    return found


def load_ssot(path: Path = SSOT_PATH) -> dict[str, list[float]]:
    """unit → numeric SSOT values (shares also offered as percent)."""
    values: dict[str, list[float]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6 or cells[0] in ("key", "---"):
            continue
        try:
            number = float(cells[1])
        except ValueError:
            continue
        unit = cells[2]
        values.setdefault(unit, []).append(number)
        if unit == "share":
            values.setdefault("%", []).append(number * 100)
    return values


def load_whitelist(path: Path = WHITELIST) -> set[str]:
    """Whitelisted literals; every entry must carry an inline ``# why`` comment."""
    if not path.exists():
        return set()
    entries = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "#" not in raw:
            raise ValueError(f"whitelist entry without a '# why' comment: {raw!r}")
        entries.add(raw.split("#", 1)[0].strip())
    return entries


def mismatches(
    literals: list[Literal], ssot: dict[str, list[float]], whitelist: set[str]
) -> list[Literal]:
    """Literals with no SSOT value of their unit within tolerance."""
    return [
        lit
        for lit in literals
        if lit.text not in whitelist
        and not any(abs(v - lit.value) <= lit.tolerance for v in ssot.get(lit.unit, []))
    ]


def digest_is_fresh(ssot_path: Path = SSOT_PATH) -> bool:
    """True when the SSOT's embedded results digest matches the committed CSVs."""
    spec = importlib.util.spec_from_file_location(
        "generate_ssot", REPO_ROOT / "scripts" / "generate_ssot.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = ssot_path.read_text(encoding="utf-8")
    match = re.search(re.escape(module.DIGEST_PREFIX) + r"([0-9a-f]{64})", text)
    return match is not None and match.group(1) == module.results_digest(REPO_ROOT)


def main(argv: Sequence[str] | None = None) -> int:
    """Exit 1 on any unmatched number or a stale SSOT.

    Implements: GV-303.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docs", nargs="*", type=Path, default=list(DOCS))
    parser.add_argument("--ssot", type=Path, default=SSOT_PATH)
    parser.add_argument("--skip-freshness", action="store_true")
    args = parser.parse_args(argv)
    if not args.ssot.exists():
        print(f"ERROR: {args.ssot} missing — run `make ssot`", file=sys.stderr)
        return 1
    ssot, whitelist = load_ssot(args.ssot), load_whitelist()
    literals = [
        lit
        for doc in args.docs
        if doc.exists()
        for lit in find_literals(doc.read_text(encoding="utf-8"), doc.name)
    ]
    bad = mismatches(literals, ssot, whitelist)
    for lit in bad:
        print(f"ERROR: {lit.where}: '{lit.text}' matches no SSOT {lit.unit} value", file=sys.stderr)
    fresh = args.skip_freshness or digest_is_fresh(args.ssot)
    if not fresh:
        print(
            "ERROR: NUMERIC_SSOT.md is stale vs committed results — run `make ssot`",
            file=sys.stderr,
        )
    print(f"checked {len(literals)} numbers in {len(args.docs)} docs; {len(bad)} unmatched")
    return 0 if not bad and fresh else 1


if __name__ == "__main__":
    raise SystemExit(main())
