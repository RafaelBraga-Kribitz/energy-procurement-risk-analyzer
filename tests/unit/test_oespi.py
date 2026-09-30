"""Unit tests for `epra.ingest.oespi.load_oespi` (ING-100/102/104).

Schema, single-series (ING-102/ADR-008), and base-only-fallback (ING-104) cases use small
CSVs built inline for the failure paths, plus the committed
`tests/fixtures/oespi/synthetic_oespi_monthly.csv` (a clean 2019-2023 series a
downstream gate would PASS) for the happy path -- the same fixture
`test_ingest_gates.py` mutates for `gate_ing_103`'s fail cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import epra.ingest.oespi as oespi_module
from epra.common import logging as common_logging
from epra.common.config import REPO_ROOT, Settings, load_settings
from epra.common.timeutil import today_local
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


# ---------------------------------------------------------------------------
# main (ING-103 CLI) -- logs instead of print(); REPO_ROOT-anchored paths
# ---------------------------------------------------------------------------


def _settings_with(**paths: Path) -> Settings:
    return SETTINGS.model_copy(update={"paths": SETTINGS.paths.model_copy(update=paths)})


def test_main_logs_gate_result_and_never_prints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "oespi_monthly.csv").write_text(_FIXTURE.read_text(encoding="utf-8"), "utf-8")
    settings = _settings_with(data_manual=manual, reports=tmp_path / "reports")
    monkeypatch.setattr(oespi_module, "load_settings", lambda: settings)
    monkeypatch.setattr(common_logging, "setup", lambda **_: None)

    with caplog.at_level("INFO", logger="epra.ingest.oespi"):
        assert oespi_module.main([]) == 0

    assert capsys.readouterr().out == ""  # no print() (audit 2026-09-30 §4)
    messages = [r.getMessage() for r in caplog.records]
    assert any(m.startswith("gate=ING-103 passed=True") for m in messages)
    assert any("### ING-103 — PASS" in m for m in messages)


def test_main_returns_1_when_csv_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings_with(data_manual=tmp_path, reports=tmp_path / "reports")
    monkeypatch.setattr(oespi_module, "load_settings", lambda: settings)
    monkeypatch.setattr(common_logging, "setup", lambda **_: None)
    assert oespi_module.main([]) == 1


def test_main_and_loader_anchor_relative_paths_at_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Relative ``paths.reports``/``paths.data_manual`` never resolve against the cwd."""
    settings = _settings_with(data_manual=Path("data/manual"), reports=Path("reports"))
    monkeypatch.setattr(oespi_module, "load_settings", lambda: settings)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        common_logging, "setup", lambda logfile=None, **_: captured.update(log=logfile)
    )

    def fake_read(path: Path) -> None:
        captured["csv"] = path
        raise FileNotFoundError(path)

    monkeypatch.setattr(oespi_module, "_read_raw_csv", fake_read)
    monkeypatch.chdir(tmp_path)

    assert oespi_module.main([]) == 1
    assert captured["log"] == (
        REPO_ROOT / "reports" / "ingestion" / f"oespi_{today_local():%Y-%m-%d}.log"
    )
    assert captured["csv"] == REPO_ROOT / "data" / "manual" / "oespi_monthly.csv"
