"""Marts schema-contract drift guard (M3 exit gate, AGENTS.md §3).

Diffs `information_schema.columns` for `table_schema='marts'` against the
hand-authored `dbt/contracts/marts_contract.yml` (SPEC-02 §4-§5, SG-05) for
all 8 objects in the `marts` schema: the 6 fct_* marts, `dim_calendar`, and
the `dim_strategy` seed. `marts_contract.yml` lives outside dbt's own
`model-paths`, so this pytest test is the only mechanism that enforces it --
renaming or retyping any mart column, without updating both sides, fails
this test naming the offending mart and column.

The warehouse-backed cases are meaningful only after `cd dbt && dbt build`
has populated the `marts` schema; they skip (not a false pass) if it hasn't.
The static coverage check (every mart model/seed has a contract entry) runs
always.

Implements: DM-010 (ts_utc typing, ADR-014), DM-060, SPEC-02 §4-§5 contracts.
"""

from __future__ import annotations

import pytest
import yaml

from epra.common.config import REPO_ROOT, load_settings
from epra.common.db import connect, warehouse_path

CONTRACT_PATH = REPO_ROOT / "dbt" / "contracts" / "marts_contract.yml"
MARTS_MODEL_DIR = REPO_ROOT / "dbt" / "models" / "marts"

#: Seeds materialized into the `marts` schema (dbt_project.yml `+schema: marts`).
MARTS_SEEDS = {"dim_strategy"}

with CONTRACT_PATH.open(encoding="utf-8") as _fh:
    _CONTRACT: dict[str, dict[str, list[dict[str, str]]]] = yaml.safe_load(_fh)


def _expected_columns(mart: str) -> list[tuple[str, str]]:
    """(column_name, data_type) pairs for `mart`, in the contract's own order."""
    return [(column["name"], column["type"]) for column in _CONTRACT[mart]["columns"]]


def _actual_columns(mart: str) -> list[tuple[str, str]]:
    """(column_name, data_type) pairs for `mart` read from the built warehouse."""
    con = connect(load_settings(), read_only=True)
    try:
        rows = con.execute(
            "select column_name, data_type "
            "from information_schema.columns "
            "where table_schema = 'marts' and table_name = ? "
            "order by ordinal_position",
            [mart],
        ).fetchall()
    finally:
        con.close()
    return [(name, data_type) for name, data_type in rows]


def _marts_schema_populated() -> bool:
    """True once `dbt build` has materialized at least one `marts` table."""
    settings = load_settings()
    # Fresh CI checkouts have no epra.duckdb; read_only connect raises IOException.
    if not warehouse_path(settings).exists():
        return False
    con = connect(settings, read_only=True)
    try:
        row = con.execute(
            "select count(*) from information_schema.tables where table_schema = 'marts'"
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return False
    return bool(row[0])


def _mart_objects() -> set[str]:
    """Every object dbt materializes into `marts`: mart model files + marts seeds."""
    return {path.stem for path in MARTS_MODEL_DIR.glob("*.sql")} | MARTS_SEEDS


def test_contract_covers_every_mart_object() -> None:
    """The contract has exactly one entry per mart model/seed -- all 8, no extras."""
    assert _mart_objects() == set(_CONTRACT)
    assert len(_CONTRACT) == 8


def test_warehouse_marts_schema_has_no_uncontracted_tables() -> None:
    """Nothing lands in `marts` without a contract entry."""
    if not _marts_schema_populated():
        pytest.skip("marts schema is empty -- run `cd dbt && dbt build` first")
    con = connect(load_settings(), read_only=True)
    try:
        rows = con.execute(
            "select table_name from information_schema.tables where table_schema = 'marts'"
        ).fetchall()
    finally:
        con.close()
    assert {name for (name,) in rows} == set(_CONTRACT)


@pytest.mark.parametrize("mart", sorted(_CONTRACT))
def test_mart_schema_matches_contract(mart: str) -> None:
    """Actual (column_name, data_type) sequence byte-matches the contract."""
    if not _marts_schema_populated():
        pytest.skip("marts schema is empty -- run `cd dbt && dbt build` first")

    expected = _expected_columns(mart)
    actual = _actual_columns(mart)

    if not actual:
        pytest.fail(f"{mart}: no columns found in information_schema.columns (model not built?)")

    for position, (expected_column, actual_column) in enumerate(
        zip(expected, actual, strict=False)
    ):
        assert expected_column == actual_column, (
            f"{mart}: column #{position} mismatch -- "
            f"expected {expected_column[0]!r} ({expected_column[1]}), "
            f"got {actual_column[0]!r} ({actual_column[1]})"
        )

    assert len(actual) == len(expected), (
        f"{mart}: expected {len(expected)} columns {[c[0] for c in expected]}, "
        f"got {len(actual)} columns {[c[0] for c in actual]}"
    )
