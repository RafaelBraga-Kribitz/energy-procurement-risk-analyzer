"""Unit tests for `epra.ingest.oespi.load_oespi` (ING-100/102/104).

Schema, single-series (D-01), and base-only-fallback (ING-104) cases use small
CSVs built inline for the failure paths, plus the committed
`tests/fixtures/oespi/synthetic_oespi_monthly.csv` (a clean 2019-2023 series a
downstream gate would PASS) for the happy path -- the same fixture
`test_ingest_gates.py` mutates for `gate_ing_103`'s fail cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epra.common.config import load_settings
from epra.ingest.exceptions import ContractError
from epra.ingest.oespi import load_oespi

SETTINGS = load_settings()

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "oespi" / "synthetic_oespi_monthly.csv"
)


def _write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "oespi_monthly.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_oespi_loads_committed_synthetic_fixture_with_peak_available() -> None:
    frame = load_oespi(SETTINGS, csv_path=_FIXTURE)
    assert list(frame.columns) == ["oespi_base", "oespi_peak", "source_url", "retrieved_at"]
    assert len(frame) == 60
    assert frame.attrs["peak_available"] is True
    assert frame["source_url"].nunique() == 1
    assert frame.index.name == "month"


def test_load_oespi_schema_drift_raises(tmp_path: Path) -> None:
    bad = _write_csv(
        tmp_path,
        "month,oespi_base,source_url,retrieved_at\n2019-01,95.0,https://x,2026-07-23\n",
    )
    with pytest.raises(ContractError):
        load_oespi(SETTINGS, csv_path=bad)


def test_load_oespi_base_only_fallback(tmp_path: Path) -> None:
    csv = (
        "month,oespi_base,oespi_peak,source_url,retrieved_at\n"
        "2019-01,95.0,,https://x,2026-07-23\n"
        "2019-02,97.0,,https://x,2026-07-23\n"
    )
    path = _write_csv(tmp_path, csv)
    frame = load_oespi(SETTINGS, csv_path=path)
    assert frame.attrs["peak_available"] is False
    assert frame["oespi_peak"].isna().all()


def test_load_oespi_partial_peak_blank_raises(tmp_path: Path) -> None:
    """A peak column blank for SOME but not all months is malformed, never silently split."""
    csv = (
        "month,oespi_base,oespi_peak,source_url,retrieved_at\n"
        "2019-01,95.0,128.0,https://x,2026-07-23\n"
        "2019-02,97.0,,https://x,2026-07-23\n"
    )
    path = _write_csv(tmp_path, csv)
    with pytest.raises(ContractError):
        load_oespi(SETTINGS, csv_path=path)


def test_load_oespi_source_url_splice_raises(tmp_path: Path) -> None:
    csv = (
        "month,oespi_base,oespi_peak,source_url,retrieved_at\n"
        "2019-01,95.0,128.0,https://old-method,2026-07-23\n"
        "2019-02,97.0,130.0,https://new-method,2026-07-23\n"
    )
    path = _write_csv(tmp_path, csv)
    with pytest.raises(ContractError):
        load_oespi(SETTINGS, csv_path=path)


def test_load_oespi_malformed_value_raises(tmp_path: Path) -> None:
    csv = (
        "month,oespi_base,oespi_peak,source_url,retrieved_at\n"
        "2019-01,95.0,128.0,https://x,2026-07-23\n"
        "2019-02,not-a-number,130.0,https://x,2026-07-23\n"
    )
    path = _write_csv(tmp_path, csv)
    with pytest.raises(ContractError):
        load_oespi(SETTINGS, csv_path=path)


def test_load_oespi_never_mutates_a_bad_row_to_nan(tmp_path: Path) -> None:
    """A malformed row must raise, never silently become NaN (P-3)."""
    csv = (
        "month,oespi_base,oespi_peak,source_url,retrieved_at\n"
        "2019-01,95.0,128.0,https://x,2026-07-23\n"
        "2019-02,,130.0,https://x,2026-07-23\n"
    )
    path = _write_csv(tmp_path, csv)
    with pytest.raises(ContractError):
        load_oespi(SETTINGS, csv_path=path)
