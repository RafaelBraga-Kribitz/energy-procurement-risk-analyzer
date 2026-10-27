"""Model ↔ report integrity of the Power BI project (ADR-022, RP-401..RP-406).

A PBIP is text, so the report cannot silently drift from its semantic model:
every field a visual (or a visual filter, or a formatting rule) references must
exist in the TMDL, every relationship must join existing columns toward a
dimension, pages and German subtitles must match the shared page registry and
the build kit, every data visual must carry alt text, and the registered theme
must keep the RP-704 strategy colours. Pure file parsing — no Power BI, no
network; JSON-schema validation against Microsoft's schemas is the separate
``scripts/validate_pbip.py`` gate.

Implements: ADR-022, RP-401..RP-405, RP-702, RP-704; supports DM-070.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from epra.common.config import REPO_ROOT
from epra.report import dashboard_pages as dp
from epra.report.style import STRATEGY_COLORS

DASH = REPO_ROOT / "dashboards"
MODEL = DASH / "EPRA.SemanticModel" / "definition"
REPORT = DASH / "EPRA.Report"
PAGES_DIR = REPORT / "definition" / "pages"
DECORATIVE = {"shape", "basicShape", "image"}
#: Text/boolean measures need no number format; every other measure must have one.
TEXT_FOLDER = "Labels & notes"
DIMENSIONS = {"dim_strategy", "DimMonth"}


@dataclass
class Table:
    """What the test needs from one ``tables/*.tmdl`` file."""

    columns: set[str] = field(default_factory=set)
    measures: dict[str, dict[str, str]] = field(default_factory=dict)


def _unquote(name: str) -> str:
    return name[1:-1] if name.startswith("'") and name.endswith("'") else name


def parse_tmdl(path: Path) -> tuple[str, Table]:
    """Table name, columns and measures (expression, properties, description)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    table_name, table = "", Table()
    doc: list[str] = []
    current: dict[str, str] | None = None
    for line in lines:
        stripped = line.strip()
        if line.startswith("table "):
            table_name = _unquote(line[len("table ") :].strip())
        elif line.startswith("\t///"):
            doc.append(stripped[3:].strip())
            continue
        elif line.startswith("\tmeasure "):
            name, _, expr = line[len("\tmeasure ") :].partition("=")
            current = {"expression": expr.strip(), "description": " ".join(doc)}
            table.measures[_unquote(name.strip())] = current
        elif line.startswith("\tcolumn "):
            table.columns.add(_unquote(line[len("\tcolumn ") :].strip()))
            current = None
        elif line.startswith("\t") and not line.startswith("\t\t"):
            current = None
        elif current is not None and line.startswith("\t\t\t"):
            current["expression"] = (current["expression"] + "\n" + line[3:]).strip()
        elif current is not None and line.startswith("\t\t") and ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip()
        doc = []
    return table_name, table


@pytest.fixture(scope="module")
def model() -> dict[str, Table]:
    tables = dict(parse_tmdl(p) for p in sorted((MODEL / "tables").glob("*.tmdl")))
    assert tables, "no TMDL tables found"
    return tables


def visual_files() -> list[Path]:
    return sorted(PAGES_DIR.glob("*/visuals/*/visual.json"))


def load(path: Path) -> Any:
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), f"{path}: UTF-8 BOM breaks Power BI Desktop"
    return json.loads(raw.decode("utf-8"))


def field_refs(node: Any, aliases: dict[str, str] | None = None) -> Iterator[tuple[str, str]]:
    """Every (table, property) a Measure/Column expression points at, filters included."""
    aliases = dict(aliases or {})
    if isinstance(node, dict):
        for source in node.get("From", []) if isinstance(node.get("From"), list) else []:
            aliases[source["Name"]] = source["Entity"]
        for kind in ("Measure", "Column"):
            ref = node.get(kind)
            if isinstance(ref, dict) and "Property" in ref:
                src = ref["Expression"]["SourceRef"]
                table = src.get("Entity") or aliases[src["Source"]]
                yield table, ref["Property"]
        for value in node.values():
            yield from field_refs(value, aliases)
    elif isinstance(node, list):
        for value in node:
            yield from field_refs(value, aliases)


def literal_text(prop: dict[str, Any]) -> str:
    """Text of a PBIR string literal property: ``{"expr": {"Literal": {"Value": "'x'"}}}``."""
    value: str = prop["expr"]["Literal"]["Value"]
    return value[1:-1].replace("''", "'")


def textbox_text(visual: dict[str, Any]) -> str:
    paragraphs = visual["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    return " ".join(run["value"] for p in paragraphs for run in p["textRuns"])


# --------------------------------------------------------------------------- the model


def test_every_json_parses_without_bom() -> None:
    files = [*DASH.glob("*.pbip"), *REPORT.rglob("*.json"), *REPORT.glob("*.pbir")]
    files += [DASH / "EPRA.SemanticModel" / "definition.pbism"]
    assert len(files) > 20
    for path in files:
        load(path)


def test_model_lists_every_table_file(model: dict[str, Table]) -> None:
    refs = re.findall(
        r"^ref table (\S+)$", (MODEL / "model.tmdl").read_text(encoding="utf-8"), re.M
    )
    assert sorted(refs) == sorted(model)
    assert "culture: en-US" in (MODEL / "model.tmdl").read_text(encoding="utf-8")


def test_every_export_has_a_table_with_its_contract_columns(model: dict[str, Table]) -> None:
    """DM-070: the model loads every export file, with the exact exported columns."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "export_marts", REPO_ROOT / "scripts" / "export_marts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_marts"] = module
    spec.loader.exec_module(module)
    for name, columns in module.EXPORT_CONTRACT.items():
        assert name in model, f"export {name} has no table"
        assert set(columns) <= model[name].columns, f"{name}: missing columns"
        tmdl = (MODEL / "tables" / f"{name}.tmdl").read_text(encoding="utf-8")
        assert f'LoadExport("{name}.csv")' in tmdl


def test_exports_path_is_the_single_parameter() -> None:
    text = (MODEL / "expressions.tmdl").read_text(encoding="utf-8")
    assert re.search(r"^expression ExportsPath = .*IsParameterQuery = true", text, re.M)
    tables = "".join(p.read_text(encoding="utf-8") for p in (MODEL / "tables").glob("*.tmdl"))
    assert "File.Contents" not in tables, "tables must load through LoadExport/ExportsPath"


def test_relationships_join_existing_columns_toward_dimensions(model: dict[str, Table]) -> None:
    text = (MODEL / "relationships.tmdl").read_text(encoding="utf-8")
    pairs = re.findall(r"fromColumn: (\w+)\.(\w+)\s+toColumn: (\w+)\.(\w+)", text)
    assert len(pairs) == 10
    for from_t, from_c, to_t, to_c in pairs:
        assert from_c in model[from_t].columns
        assert to_c in model[to_t].columns
        assert to_t in DIMENSIONS and from_t not in DIMENSIONS
    assert "crossFilteringBehavior" not in text, "relationships stay single-direction"


def test_date_table_is_marked(model: dict[str, Table]) -> None:
    text = (MODEL / "tables" / "DimMonth.tmdl").read_text(encoding="utf-8")
    assert "dataCategory: Time" in text
    assert re.search(r"column Date\n\t\tdataType: dateTime\n\t\tisKey", text)


def test_every_measure_documented_and_formatted(model: dict[str, Table]) -> None:
    measures = {n: m for t in model.values() for n, m in t.measures.items()}
    assert len(measures) >= 40
    for name, props in measures.items():
        assert len(props["description"]) > 20, f"{name}: /// description missing"
        assert props.get("displayFolder"), f"{name}: displayFolder missing"
        if props.get("displayFolder") != TEXT_FOLDER:
            assert props.get("formatString"), f"{name}: formatString missing"


def test_measures_dax_mirrors_the_tmdl(model: dict[str, Table]) -> None:
    """dashboards/measures.dax keeps every measure name AND expression of the model."""
    text = (DASH / "measures.dax").read_text(encoding="utf-8")
    body = re.sub(r"^//.*\n?", "", text, flags=re.M)
    dax = {}
    for block in re.split(r"\n\s*\n", body):
        name, sep, expr = block.strip().partition(" =")
        if sep:
            dax[name.strip()] = " ".join(expr.split())
    tmdl = {
        n: " ".join(m["expression"].split()) for t in model.values() for n, m in t.measures.items()
    }
    assert dax == tmdl


def test_text_measures_match_the_page_registry(model: dict[str, Table]) -> None:
    prov = model["provenance"].measures
    assert dp.EPISTEMIC_STRATEGIES in prov["Epistemic Note Strategies"]["expression"]
    assert dp.EPISTEMIC_RISK in prov["Epistemic Note Risk"]["expression"]
    assert dp.FIXTURE_BANNER in prov["Data Banner"]["expression"]


# --------------------------------------------------------------------------- the report


def test_every_visual_field_exists_in_the_model(model: dict[str, Table]) -> None:
    files = visual_files()
    assert len(files) >= 45
    for path in files:
        for table, prop in field_refs(load(path)):
            assert table in model, f"{path}: unknown table {table}"
            known = model[table].columns | set(model[table].measures)
            assert prop in known, f"{path}: {table}[{prop}] not in the model"


def test_query_refs_are_consistent() -> None:
    for path in visual_files():
        query = load(path)["visual"].get("query", {})
        for role in query.get("queryState", {}).values():
            for proj in role["projections"]:
                kind = "Measure" if "Measure" in proj["field"] else "Column"
                ref = proj["field"][kind]
                expected = f"{ref['Expression']['SourceRef']['Entity']}.{ref['Property']}"
                assert proj["queryRef"] == expected, path
                assert proj["nativeQueryRef"] == ref["Property"], path


def test_pages_match_the_registry_and_spec() -> None:
    meta = load(PAGES_DIR / "pages.json")
    assert meta["pageOrder"] == [p.page_id for p in dp.PAGES]
    assert [p.title for p in dp.PAGES] == [
        "Headline",
        "Market",
        "Strategies",
        "Risk",
        "Data quality",
    ]
    for page in dp.PAGES:
        spec = load(PAGES_DIR / page.page_id / "page.json")
        assert spec["displayName"] == page.title
        assert (spec["width"], spec["height"]) == (1280, 720)


def _configured_paths() -> int:
    cfg = yaml.safe_load((REPO_ROOT / "config" / "strategies.yaml").read_text(encoding="utf-8"))
    return int(cfg["forward"]["n_paths"])


def test_each_page_has_title_german_subtitle_and_footer() -> None:
    n_paths = _configured_paths()
    for page in dp.PAGES:
        visuals = {
            p.parent.name: load(p)
            for p in (PAGES_DIR / page.page_id / "visuals").glob("*/visual.json")
        }
        assert textbox_text(visuals["title"]) == page.heading
        assert textbox_text(visuals["subtitle_de"]) == dp.subtitle(page, n_paths)
        assert textbox_text(visuals["source_note"]) == dp.SOURCE_NOTE
        assert "epistemic_note" in visuals and "data_banner" in visuals


def test_subtitles_match_the_build_kit_readme() -> None:
    readme = (DASH / "README.md").read_text(encoding="utf-8")
    documented = re.findall(r"\*Untertitel: „(.+?)“\*", readme)
    assert documented == [dp.subtitle(p, _configured_paths()) for p in dp.PAGES]


def test_accessibility_alt_text_and_tab_order() -> None:
    """pbip-accessibility rules: alt text on every non-decorative visual, unique tab order."""
    for page in dp.PAGES:
        orders = []
        for path in (PAGES_DIR / page.page_id / "visuals").glob("*/visual.json"):
            visual = load(path)
            pos, vtype = visual["position"], visual["visual"]["visualType"]
            assert pos["x"] >= 0 and pos["y"] >= 0
            assert pos["x"] + pos["width"] <= 1280 and pos["y"] + pos["height"] <= 720, path
            orders.append(pos["tabOrder"])
            if vtype in DECORATIVE:
                assert pos["tabOrder"] < 0
                continue
            vco = visual["visual"]["visualContainerObjects"]
            alt = literal_text(vco["general"][0]["properties"]["altText"])
            assert 10 <= len(alt) <= 150 or vtype == "textbox", f"{path}: alt text {alt!r}"
            if vtype == "textbox":
                assert alt == textbox_text(visual)
            elif vtype not in {"card"} or path.parent.name.startswith("card"):
                title = vco["title"][0]["properties"]["text"]
                assert literal_text(title), f"{path}: data visual without a title"
        assert len(orders) == len(set(orders)), f"{page.page_id}: duplicate tabOrder"


def test_theme_registered_and_keeps_strategy_colours() -> None:
    report = load(REPORT / "definition" / "report.json")
    custom = report["themeCollection"]["customTheme"]
    items = {
        item["name"]: item
        for pkg in report["resourcePackages"]
        if pkg["type"] == "RegisteredResources"
        for item in pkg["items"]
    }
    assert items[custom["name"]]["type"] == "CustomTheme"
    registered = REPORT / "StaticResources" / "RegisteredResources" / items[custom["name"]]["path"]
    assert registered.read_bytes() == (DASH / "theme.json").read_bytes()
    theme = json.loads(registered.read_text(encoding="utf-8"))
    assert [c.upper() for c in theme["dataColors"][:6]] == [
        c.upper() for c in STRATEGY_COLORS.values()
    ]


def test_pbir_points_at_the_semantic_model() -> None:
    pbir = load(REPORT / "definition.pbir")
    assert pbir["datasetReference"]["byPath"]["path"] == "../EPRA.SemanticModel"
    pbip = load(DASH / "EPRA.pbip")
    assert pbip["artifacts"] == [{"report": {"path": "EPRA.Report"}}]


def _validator_module() -> Any:
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "validate_pbip", REPO_ROOT / "scripts" / "validate_pbip.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_pbip"] = module
    spec.loader.exec_module(module)
    return module


def test_schema_validator_skips_without_schema_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI has no copy of Microsoft's schema tree: the gate must skip, not fail."""
    monkeypatch.delenv("PBIP_SCHEMA_DIR", raising=False)
    module = _validator_module()
    assert module.main([]) == 0
    files = module.pbip_json_files(DASH)
    assert DASH / "EPRA.pbip" in files and DASH / "theme.json" not in files
    for path in files:
        assert load(path)["$schema"].startswith(module.SCHEMA_URL_PREFIX), path
