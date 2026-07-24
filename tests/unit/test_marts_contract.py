"""D-07 marts schema-contract drift guard.

Diffs `information_schema.columns` for `table_schema='marts'` against the
hand-authored `dbt/contracts/marts_contract.yml` (SPEC-02 §5, SG-05).
`marts_contract.yml` lives outside dbt's own `model-paths`, so this pytest
test is the only mechanism that enforces it (04-RESEARCH.md Pitfall 3) --
renaming or retyping any mart column, without updating both sides, fails
this test naming the offending mart and column.

Meaningful only after `cd dbt && dbt build` has populated the `marts`
schema; skips gracefully (not a false pass) if it hasn't.

Implements: D-07, DM-060.
"""

from __future__ import annotations

import pytest
import yaml

from epra.common.config import REPO_ROOT, load_settings
from epra.common.db import connect

CONTRACT_PATH = REPO_ROOT / "dbt" / "contracts" / "marts_contract.yml"

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
    con = connect(load_settings(), read_only=True)
    try:
        row = con.execute(
            "select count(*) from information_schema.tables where table_schema = 'marts'"
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return False
    return bool(row[0])


@pytest.mark.parametrize("mart", sorted(_CONTRACT))
def test_mart_schema_matches_contract(mart: str) -> None:
    """Actual (column_name, data_type) sequence byte-matches the contract (D-07)."""
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
