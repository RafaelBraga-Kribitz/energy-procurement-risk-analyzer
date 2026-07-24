"""ING-070 raw contract drift guards.

Opens each committed §7 fixture parquet under `tests/fixtures/<source>/` and
asserts the exact column names, dtypes, and (for `ts_utc`-keyed datasets)
zone values SPEC-01 §7 specifies. Runs entirely against small (<=200 row)
fixture files committed to git — no network access, no live external calls
(CI: `pytest -m "not live"`).

The ENTSO-E fixture parquets are generated once via the real Appendix-A
parsers (`parse_publication_xml`, `parse_gl_xml`) and `_io.write_month`, then
copied into this flat `<dataset>_2024-01.parquet` layout — see
`.planning/phases/EPRA-02-m1-entso-e-ingestion/02-07-SUMMARY.md` for the
generation method. `entsoe_prices_delu` has no committed DE_LU-domain XML
source fixture yet, so its frame was hand-built directly in the SPEC-01 §7
shape (same precedent as every other synthetic ENTSO-E fixture already
committed in this repo, e.g. `prices_pt60m_at.xml`'s
`mRID="epra-fixture-prices-pt60m-at"`).

`geosphere_graz_daily` (03-04, M2) is date-keyed, not `ts_utc`-keyed
(`_io.write_month(..., key_column="date")`, Pattern 1) — it has no `zone`
column, so the `ts_utc`/`zone`-specific tests below skip it via
`_DATE_KEYED_DATASETS` and `test_geosphere_graz_daily_dtypes_match_spec01_section7`
asserts its own shape instead. Its fixture was generated the same way (real
`parse_geojson` + `write_month(key_column="date")`) against the committed
`tests/fixtures/geosphere/klima_2019-01.geojson` response, with the January
dates remapped from 2019 to 2024 only to follow this file's `_2024-01`
naming convention (temperature/station/parameter values are untouched) —
see `.planning/phases/EPRA-03-m2-auxiliary-data/03-04-SUMMARY.md`.

Implements: ING-070.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from epra.common.config import REPO_ROOT

FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"

#: ING-004 provenance columns appended by `_io.write_month` after the raw
#: dataset's own columns, in this fixed order (see `_io._PROVENANCE_COLUMNS`).
_PROVENANCE_COLUMNS = ["ingested_at_utc", "source", "request_hash"]

#: SPEC-01 §7 raw contract: dataset -> (own columns in order, zone values
#: allowed). `zone values` is `None` for a date-keyed dataset with no `zone`
#: column (see `_DATE_KEYED_DATASETS`) — its fixture-generic tests below skip
#: the zone assertion rather than treating an empty set as "zero zones allowed".
_CONTRACTS: dict[str, tuple[list[str], set[str] | None]] = {
    "entsoe_prices_at": (["ts_utc", "price_eur_mwh", "resolution", "zone"], {"AT"}),
    "entsoe_prices_delu": (["ts_utc", "price_eur_mwh", "resolution", "zone"], {"DE_LU"}),
    "entsoe_load_at": (["ts_utc", "load_mw", "resolution", "zone"], {"AT"}),
    "entsoe_gen_at": (
        ["ts_utc", "psr_type", "psr_name", "kind", "value_mw", "resolution", "zone"],
        {"AT"},
    ),
    "geosphere_graz_daily": (["date", "station_id", "tl_mittel_c", "parameter_raw"], None),
}

#: Datasets keyed by a plain calendar `date` (SPEC-01 §7 GeoSphere), not
#: `ts_utc` — no `zone` column either. The `ts_utc`/`zone`-specific tests
#: below skip these; `test_geosphere_graz_daily_dtypes_match_spec01_section7`
#: covers the equivalent shape assertions for this grain.
_DATE_KEYED_DATASETS = {"geosphere_graz_daily"}

#: dataset -> its fixtures subdirectory under `tests/fixtures/`.
_DATASET_FIXTURE_SUBDIR: dict[str, str] = {
    "entsoe_prices_at": "entsoe",
    "entsoe_prices_delu": "entsoe",
    "entsoe_load_at": "entsoe",
    "entsoe_gen_at": "entsoe",
    "geosphere_graz_daily": "geosphere",
}

#: ING-070: fixtures generated once, <=200 rows each, committed (no network in CI).
_MAX_FIXTURE_ROWS = 200


def _fixture_path(dataset: str) -> Path:
    return FIXTURES_ROOT / _DATASET_FIXTURE_SUBDIR[dataset] / f"{dataset}_2024-01.parquet"


@pytest.mark.parametrize("dataset", sorted(_CONTRACTS))
def test_fixture_committed_and_bounded(dataset: str) -> None:
    """Every §7 dataset has a committed fixture parquet, <=200 rows (ING-070)."""
    path = _fixture_path(dataset)
    assert path.exists(), f"missing committed fixture: {path}"
    frame = pd.read_parquet(path)
    assert len(frame) <= _MAX_FIXTURE_ROWS, (
        f"{dataset}: fixture has {len(frame)} rows, exceeds ING-070 cap of {_MAX_FIXTURE_ROWS}"
    )
    assert len(frame) > 0, f"{dataset}: fixture is empty"


@pytest.mark.parametrize("dataset", sorted(_CONTRACTS))
def test_fixture_exact_column_layout(dataset: str) -> None:
    """Column order is the dataset's own §7 columns, then the 3 ING-004 columns."""
    own_columns, _zones = _CONTRACTS[dataset]
    frame = pd.read_parquet(_fixture_path(dataset))
    assert list(frame.columns) == [*own_columns, *_PROVENANCE_COLUMNS]


@pytest.mark.parametrize("dataset", sorted(_CONTRACTS))
def test_fixture_ts_utc_is_utc_tz_aware_timestamp(dataset: str) -> None:
    """ts_utc is a tz-aware UTC datetime64 column (ING-005)."""
    if dataset in _DATE_KEYED_DATASETS:
        pytest.skip(f"{dataset} is date-keyed (no ts_utc column, Pattern 1)")
    frame = pd.read_parquet(_fixture_path(dataset))
    assert pd.api.types.is_datetime64_any_dtype(frame["ts_utc"])
    assert str(frame["ts_utc"].dt.tz) == "UTC"


@pytest.mark.parametrize("dataset", sorted(_CONTRACTS))
def test_fixture_zone_matches_spec01_section7(dataset: str) -> None:
    """zone column values are exactly the SPEC-01 §7-specified set for this dataset."""
    _own_columns, expected_zones = _CONTRACTS[dataset]
    if expected_zones is None:
        pytest.skip(f"{dataset} has no zone column (date-keyed, Pattern 1)")
    frame = pd.read_parquet(_fixture_path(dataset))
    assert set(frame["zone"].unique()) == expected_zones


@pytest.mark.parametrize("dataset", sorted(_CONTRACTS))
def test_fixture_provenance_columns_present_and_typed(dataset: str) -> None:
    """ING-004 provenance columns exist with the expected string/object dtypes."""
    frame = pd.read_parquet(_fixture_path(dataset))
    for col in _PROVENANCE_COLUMNS:
        assert col in frame.columns
        assert frame[col].dtype == object
    # request_hash must never contain a literal ENTSO-E token (A-7): _io.request_hash
    # strips securityToken before hashing, so it's a 64-char hex sha256 digest only.
    assert (frame["request_hash"].str.len() == 64).all()
    assert frame["request_hash"].str.match(r"^[0-9a-f]{64}$").all()


def test_entsoe_prices_at_dtypes_match_spec01_section7() -> None:
    """entsoe_prices_at: price_eur_mwh double, resolution/zone varchar (ING-070)."""
    frame = pd.read_parquet(_fixture_path("entsoe_prices_at"))
    assert frame["price_eur_mwh"].dtype == "float64"
    assert frame["resolution"].dtype == object
    assert frame["zone"].dtype == object
    assert set(frame["resolution"].unique()) <= {"PT60M", "PT30M", "PT15M"}


def test_entsoe_prices_delu_dtypes_match_spec01_section7() -> None:
    """entsoe_prices_delu: same shape as entsoe_prices_at, zone='DE_LU' (ING-070)."""
    frame = pd.read_parquet(_fixture_path("entsoe_prices_delu"))
    assert frame["price_eur_mwh"].dtype == "float64"
    assert frame["resolution"].dtype == object
    assert (frame["zone"] == "DE_LU").all()


def test_entsoe_load_at_dtypes_match_spec01_section7() -> None:
    """entsoe_load_at: load_mw double, resolution/zone varchar (ING-070)."""
    frame = pd.read_parquet(_fixture_path("entsoe_load_at"))
    assert frame["load_mw"].dtype == "float64"
    assert frame["resolution"].dtype == object
    assert (frame["zone"] == "AT").all()


def test_entsoe_gen_at_dtypes_match_spec01_section7() -> None:
    """entsoe_gen_at: long format, psr_type/psr_name/kind varchar, value_mw double (ING-032/070)."""
    frame = pd.read_parquet(_fixture_path("entsoe_gen_at"))
    assert frame["value_mw"].dtype == "float64"
    for col in ("psr_type", "psr_name", "kind", "resolution", "zone"):
        assert frame[col].dtype == object
    assert set(frame["kind"].unique()) <= {"aggregated", "consumption"}
    assert (frame["zone"] == "AT").all()


def test_geosphere_graz_daily_dtypes_match_spec01_section7() -> None:
    """geosphere_graz_daily: date-keyed (no ts_utc/zone), tl_mittel_c double,
    station_id/parameter_raw varchar (ING-070, Pattern 1)."""
    frame = pd.read_parquet(_fixture_path("geosphere_graz_daily"))
    assert frame["tl_mittel_c"].dtype == "float64"
    assert frame["station_id"].dtype == object
    assert frame["parameter_raw"].dtype == object
    assert all(hasattr(v, "isoformat") for v in frame["date"])  # date/datetime-like, never a string
    assert "ts_utc" not in frame.columns
    assert "zone" not in frame.columns
