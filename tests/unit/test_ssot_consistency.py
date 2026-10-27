"""GV-303 consistency gate: literal parsing, rounding tolerance, whitelist,
freshness digest (SPEC-08 §3/§4)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from epra.common.config import REPO_ROOT


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their module via sys.modules
    spec.loader.exec_module(module)
    return module


CHECK = _script("check_ssot_consistency")

SSOT = """| key | value | unit | tag | produced_by | updated_at |
|---|---:|---|---|---|---|
| wrong_strategy_cost_total | 16594321.4 | EUR | CALIBRATED | x | 2026-10-14 |
| unit_cost_S1_2022 | 197.9123 | EUR/MWh | CALIBRATED | x | 2026-10-14 |
| consumer_peak_share | 0.485342 | share | CALIBRATED | x | 2026-10-14 |
| neg_hours_2025 | 266 | hours | VERIFIED | analytics/x | 2026-10-14 |
| best_strategy_5yr | S3 | strategy_id | CALIBRATED | x | 2026-10-14 |
"""


@pytest.fixture
def ssot(tmp_path: Path) -> dict[str, list[float]]:
    path = tmp_path / "NUMERIC_SSOT.md"
    path.write_text(SSOT, encoding="utf-8")
    values: dict[str, list[float]] = CHECK.load_ssot(path)
    return values


@pytest.mark.parametrize(
    "text",
    [
        "cost €16.59 M",
        "€16.6 M total",
        "197.9 EUR/MWh",
        "48.5% of volume",
        "266 hours",
        "€16,594,321 in five years",
    ],
)
def test_matching_literals_pass(ssot: dict[str, list[float]], text: str) -> None:
    literals = CHECK.find_literals(text, "README.md")
    assert len(literals) == 1
    assert CHECK.mismatches(literals, ssot, set()) == []


@pytest.mark.parametrize("text", ["€16.70 M", "198.4 EUR/MWh", "47% share", "300 hours"])
def test_unmatched_literals_fail(ssot: dict[str, list[float]], text: str) -> None:
    literals = CHECK.find_literals(text, "README.md")
    assert len(CHECK.mismatches(literals, ssot, set())) == 1


def test_whitelist_requires_reason(tmp_path: Path, ssot: dict[str, list[float]]) -> None:
    good = tmp_path / "ok.txt"
    good.write_text("5.0 EUR/MWh  # config echo\n", encoding="utf-8")
    allowed = CHECK.load_whitelist(good)
    assert CHECK.mismatches(CHECK.find_literals("5.0 EUR/MWh", "x"), ssot, allowed) == []
    bad = tmp_path / "bad.txt"
    bad.write_text("5.0 EUR/MWh\n", encoding="utf-8")
    with pytest.raises(ValueError, match="why"):
        CHECK.load_whitelist(bad)


def test_main_reports_missing_ssot(tmp_path: Path) -> None:
    assert CHECK.main(["--ssot", str(tmp_path / "nope.md")]) == 1


def test_main_passes_and_fails_on_docs(tmp_path: Path) -> None:
    ssot = tmp_path / "NUMERIC_SSOT.md"
    ssot.write_text(SSOT, encoding="utf-8")
    doc = tmp_path / "README.md"
    doc.write_text("The wrong strategy cost €16.59 M (CALIBRATED).", encoding="utf-8")
    assert CHECK.main([str(doc), "--ssot", str(ssot), "--skip-freshness"]) == 0
    doc.write_text("The wrong strategy cost €17.00 M.", encoding="utf-8")
    assert CHECK.main([str(doc), "--ssot", str(ssot), "--skip-freshness"]) == 1


def test_freshness_digest_detects_stale_ssot(tmp_path: Path) -> None:
    ssot = tmp_path / "NUMERIC_SSOT.md"
    ssot.write_text(SSOT + "<!-- results-digest " + "0" * 64 + " -->\n", encoding="utf-8")
    assert not CHECK.digest_is_fresh(ssot)


def test_results_digest_ignores_crlf_line_endings(tmp_path: Path) -> None:
    gen = _script("generate_ssot")
    lf, crlf = tmp_path / "lf", tmp_path / "crlf"
    for root, eol in ((lf, "\n"), (crlf, "\r\n")):
        (root / "reports" / "strategies").mkdir(parents=True)
        text = eol.join(["year,cost_eur", "2021,1.5", "2022,2.5", ""])
        (root / "reports" / "strategies" / "s.csv").write_bytes(text.encode())
    assert gen.results_digest(lf) == gen.results_digest(crlf)


@pytest.mark.parametrize(
    "text", ["window 2026-10..2027-09, EUR million", "badge%20complete%20%C2", "v1.2 EUR"]
)
def test_dates_versions_and_url_encoding_are_not_numbers(text: str) -> None:
    assert CHECK.find_literals(text, "README.md") == []


def test_regex_whitelist_uses_context(ssot: dict[str, list[float]]) -> None:
    literals = CHECK.find_literals("chooses Hybrid 50% fixed today", "README.md")
    assert CHECK.mismatches(literals, ssot, {r"re:Hybrid \d+% fixed"}) == []
    assert len(CHECK.mismatches(literals, ssot, set())) == 1
