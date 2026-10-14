"""DM-070 export contract: every exports/*.csv header equals EXPORT_CONTRACT.

The static half always runs; the file half runs wherever `make export` has
produced CSVs (locally, and in CI's dbt-check job after the fixture pipeline).
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from types import ModuleType

import pytest

from epra.common.config import REPO_ROOT, load_settings, resolve_repo_path


def _export_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "export_marts", REPO_ROOT / "scripts" / "export_marts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_marts"] = module
    spec.loader.exec_module(module)
    return module


EXPORTS = _export_module()
SPEC_02_FILES = {
    "price_daily",
    "price_monthly",
    "generation_monthly",
    "procurement_cost_monthly",
    "strategy_annual_summary",
    "forward_risk_summary",
}


def test_contract_covers_spec02_and_every_query() -> None:
    contract = set(EXPORTS.EXPORT_CONTRACT)
    assert contract >= SPEC_02_FILES
    sql_names = set(EXPORTS.export_sql(load_settings()))
    assert sql_names | {"ssot", "provenance"} == contract


@pytest.mark.parametrize("name", sorted(EXPORTS.EXPORT_CONTRACT))
def test_exported_header_matches_contract(name: str) -> None:
    path = resolve_repo_path(load_settings().paths.exports) / f"{name}.csv"
    if not path.exists():
        pytest.skip("run `make export` first")
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == EXPORTS.EXPORT_CONTRACT[name]


def test_powerbi_theme_strategy_colors_match_style() -> None:
    """RP-704: the dashboard keeps the same strategy colours as every PNG."""
    import json

    from epra.report.style import STRATEGY_COLORS

    theme = json.loads((REPO_ROOT / "dashboards" / "theme.json").read_text(encoding="utf-8"))
    assert [c.upper() for c in theme["dataColors"][:6]] == [
        c.upper() for c in STRATEGY_COLORS.values()
    ]
