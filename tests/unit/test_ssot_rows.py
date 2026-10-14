"""SSOT input-row helper: tags, duplicate keys, round trip (GV-101/102/301)."""

from __future__ import annotations

import pytest

from epra.common.config import Settings
from epra.common.ssot import SsotRow, read_ssot_rows, ssot_value, write_ssot_rows


def _settings(tmp_settings: Settings) -> Settings:
    paths = tmp_settings.paths.model_copy(
        update={"data_processed": tmp_settings.paths.data_raw.parent / "processed"}
    )
    return tmp_settings.model_copy(update={"paths": paths})


def test_round_trip_and_lookup(tmp_settings: Settings) -> None:
    settings = _settings(tmp_settings)
    assert read_ssot_rows(settings).empty
    write_ssot_rows([SsotRow("b_key", 2.5, "EUR", "VERIFIED", "x")], "p1", settings)
    write_ssot_rows([SsotRow("a_key", 1.0, "share", "CALIBRATED", "y")], "p2", settings)
    rows = read_ssot_rows(settings)
    assert rows["key"].tolist() == ["a_key", "b_key"]
    assert ssot_value(settings, "b_key") == 2.5
    with pytest.raises(KeyError, match="missing_key"):
        ssot_value(settings, "missing_key")


def test_rejects_unknown_tag_and_duplicates(tmp_settings: Settings) -> None:
    settings = _settings(tmp_settings)
    with pytest.raises(ValueError, match="epistemic tag"):
        write_ssot_rows([SsotRow("k", 1.0, "EUR", "GUESSED", "x")], "p", settings)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="duplicate"):
        write_ssot_rows([SsotRow("k", 1.0, "EUR", "VERIFIED", "x")] * 2, "p", settings)


def test_cross_producer_duplicate_detected(tmp_settings: Settings) -> None:
    settings = _settings(tmp_settings)
    write_ssot_rows([SsotRow("k", 1.0, "EUR", "VERIFIED", "x")], "p1", settings)
    write_ssot_rows([SsotRow("k", 2.0, "EUR", "VERIFIED", "y")], "p2", settings)
    with pytest.raises(ValueError, match="more than one producer"):
        read_ssot_rows(settings)
