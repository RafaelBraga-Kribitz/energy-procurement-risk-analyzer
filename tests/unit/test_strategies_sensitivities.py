"""T6.06 ST-303 three config-delta sensitivities.

Implements: ST-303, D-14, D-15.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from epra.common.config import Settings, load_consumer_profile, load_strategy_config
from epra.strategies.align import AlignedVolumes, align_hourly
from epra.strategies.calibration import Anchors
from epra.strategies.retrospective import ST502_SENTENCE
from epra.strategies.sensitivities import (
    FORBIDDEN_HEADING,
    HEADING_FLAT,
    HEADING_LOCK,
    HEADING_PREMIUM,
    PREMIUMS_EUR_MWH,
    annual_for_cfg,
    lock_window_block,
    premium_block,
    run_sensitivities,
)

_ANCHORS = Anchors(p_ref_base=50.0, p_ref_peak=70.0, oespi_base_ref=100.0, oespi_peak_ref=100.0)


def _calendar() -> pd.DataFrame:
    ts = [
        pd.Timestamp("2022-01-03 10:00:00", tz="UTC"),
        pd.Timestamp("2022-01-03 22:00:00", tz="UTC"),
    ]
    return pd.DataFrame(
        {
            "ts_utc": ts,
            "date_local": [date(2022, 1, 3), date(2022, 1, 3)],
            "hour_local": [11, 23],
            "dow_local": [0, 0],
            "is_holiday_at": [False, False],
            "year_local": [2022, 2022],
            "month_local": [1, 1],
        }
    )


def _prices(calendar: pd.DataFrame) -> pd.DataFrame:
    return calendar.assign(price_at_eur_mwh=100.0)


def _aligned(calendar: pd.DataFrame, prices: pd.DataFrame) -> AlignedVolumes:
    load = pd.DataFrame({"ts_utc": calendar["ts_utc"], "load_mwh": [10.0, 10.0]})
    return align_hourly(load, prices)


def _oespi() -> pd.DataFrame:
    months = list(range(1, 13))
    jan_high = [200.0] + [100.0] * 11
    return pd.concat(
        [
            pd.DataFrame(
                {
                    "year_local": [2021] * 12,
                    "month_local": months,
                    "oespi_base": jan_high,
                    "oespi_peak": jan_high,
                }
            ),
            pd.DataFrame(
                {
                    "year_local": [2022] * 12,
                    "month_local": months,
                    "oespi_base": [100.0] * 12,
                    "oespi_peak": [100.0] * 12,
                }
            ),
        ],
        ignore_index=True,
    )


@pytest.fixture
def _complete_year(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("epra.consumer.profile._year_is_complete", lambda *_a, **_k: True)


def test_sensitivity_matrix_three_headings_only(
    tmp_settings: Settings, _complete_year: None
) -> None:
    calendar = _calendar()
    prices = _prices(calendar)
    cfg = load_strategy_config().model_copy(update={"retrospective_years": [2022]})
    body = run_sensitivities(
        tmp_settings,
        aligned=_aligned(calendar, prices),
        monthly_oespi=_oespi(),
        anchors=_ANCHORS,
        w_peak=0.4,
        cfg=cfg,
        prices=prices,
        calendar_df=calendar,
        consumer_cfg=load_consumer_profile(),
    )
    headings = [line for line in body.splitlines() if line.startswith("## ")]
    assert headings == [HEADING_PREMIUM, HEADING_FLAT, HEADING_LOCK]
    assert FORBIDDEN_HEADING not in body
    assert "peak_available" not in body
    assert ST502_SENTENCE in body
    path = tmp_settings.paths.reports / "strategies" / "sensitivity_matrix.md"
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == body


def test_premium_rerun_shifts_s3_by_volume(
    _complete_year: None,
) -> None:
    calendar = _calendar()
    prices = _prices(calendar)
    aligned = _aligned(calendar, prices)
    cfg = load_strategy_config().model_copy(update={"retrospective_years": [2022]})
    block = premium_block(aligned, _oespi(), _ANCHORS, 0.4, cfg)
    assert set(block["premium_eur_mwh"]) == set(PREMIUMS_EUR_MWH)
    s3 = block.loc[block["strategy_id"] == "S3"].set_index("premium_eur_mwh")
    volume = float(s3.loc[0.0, "volume_mwh"])
    assert float(s3.loc[10.0, "cost_eur"]) == pytest.approx(
        float(s3.loc[0.0, "cost_eur"]) + 10.0 * volume
    )


def test_lock_window_full_year_moves_s3() -> None:
    calendar = _calendar()
    prices = _prices(calendar)
    aligned = _aligned(calendar, prices)
    oespi = _oespi()
    cfg = load_strategy_config().model_copy(update={"retrospective_years": [2022]})
    baseline = annual_for_cfg(aligned, oespi, _ANCHORS, 0.4, cfg)
    full = lock_window_block(aligned, oespi, _ANCHORS, 0.4, cfg)
    s3_base = float(baseline.loc[baseline["strategy_id"] == "S3", "cost_eur"].iloc[0])
    s3_full = float(full.loc[full["strategy_id"] == "S3", "cost_eur"].iloc[0])
    assert s3_full != pytest.approx(s3_base)


def test_flat_baseload_rebuilds_volume(
    _complete_year: None,
) -> None:
    from epra.strategies.sensitivities import align_flat_baseload

    calendar = _calendar()
    prices = _prices(calendar)
    baseline = _aligned(calendar, prices)
    flat = align_flat_baseload(prices, calendar, load_consumer_profile())
    assert float(flat.monthly["volume_mwh"].sum()) != pytest.approx(
        float(baseline.monthly["volume_mwh"].sum())
    )
    assert (flat.hourly["load_mwh"] - flat.hourly["load_mwh"].iloc[0]).abs().max() == pytest.approx(
        0.0
    )
