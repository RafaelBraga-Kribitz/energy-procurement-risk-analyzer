"""A1 descriptive tests — synthetic frames, chart artists, AN-704 prose.

Implements: AN-101, AN-102, AN-103, AN-104, AN-105, AN-704, D-07, D-08.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

from epra.analytics import _kit as kit
from epra.analytics import descriptive as a1
from epra.common.config import Settings
from epra.report.format import format_eur_mwh
from epra.report.style import FIGSIZE, OKABE_ITO, SOURCE_NOTE


def _hour(
    *,
    year: int,
    month: int,
    hour: int,
    price: float | None,
    peak: bool,
) -> dict[str, object]:
    return {
        "year_local": year,
        "month_local": month,
        "hour_local": hour,
        "price_at_eur_mwh": price,
        "is_peak_hour": peak,
    }


def _known_year() -> pd.DataFrame:
    """Four priced hours: 10, 20, -5, 100 plus one NULL (must not become 0)."""
    return pd.DataFrame(
        [
            _hour(year=2023, month=1, hour=8, price=10.0, peak=True),
            _hour(year=2023, month=1, hour=9, price=20.0, peak=True),
            _hour(year=2023, month=1, hour=2, price=-5.0, peak=False),
            _hour(year=2023, month=1, hour=3, price=100.0, peak=False),
            _hour(year=2023, month=1, hour=4, price=None, peak=False),
        ]
    )


def test_annual_summary_matches_hand_calc_and_drops_null() -> None:
    summary = a1.annual_summary(_known_year())
    assert list(summary.columns) == list(a1.AN101_COLUMNS)
    row = summary.iloc[0]
    prices = np.array([10.0, 20.0, -5.0, 100.0])
    assert int(row["n_hours"]) == 4
    assert float(row["hourly_mean"]) == pytest.approx(float(prices.mean()))
    assert float(row["hourly_median"]) == pytest.approx(float(np.median(prices)))
    assert float(row["hourly_std"]) == pytest.approx(float(pd.Series(prices).std(ddof=1)))
    assert float(row["hourly_min"]) == -5.0
    assert float(row["hourly_max"]) == 100.0
    assert float(row["base_mean"]) == float(row["hourly_mean"])
    assert float(row["peak_mean"]) == pytest.approx(15.0)
    assert float(row["offpeak_mean"]) == pytest.approx(47.5)
    assert float(row["peak_offpeak_spread"]) == pytest.approx(15.0 - 47.5)
    assert int(row["n_negative"]) == 1
    assert float(row["share_negative"]) == pytest.approx(0.25)
    assert int(row["n_gt_500"]) == 0
    assert a1.count_dropped_price_hours(_known_year()) == 1


def test_null_price_is_not_treated_as_zero() -> None:
    with_zero = pd.concat(
        [
            _known_year(),
            pd.DataFrame([_hour(year=2023, month=1, hour=5, price=0.0, peak=False)]),
        ],
        ignore_index=True,
    )
    summary = a1.annual_summary(with_zero)
    assert int(summary.iloc[0]["n_hours"]) == 5
    assert float(summary.iloc[0]["hourly_mean"]) == pytest.approx(
        float(np.mean([10.0, 20.0, -5.0, 100.0, 0.0]))
    )


def test_hours_above_500_counted() -> None:
    frame = pd.DataFrame(
        [
            _hour(year=2022, month=8, hour=18, price=501.0, peak=True),
            _hour(year=2022, month=8, hour=2, price=10.0, peak=False),
        ]
    )
    assert int(a1.annual_summary(frame).iloc[0]["n_gt_500"]) == 1


def _complete_year(year: int, price: float) -> pd.DataFrame:
    rows = [
        _hour(year=year, month=m, hour=h, price=price + m + h / 10.0, peak=h >= 8)
        for m in range(1, 13)
        for h in (0, 12)
    ]
    return pd.DataFrame(rows)


def test_heatmap_five_panels_empty_incomplete_shared_clim() -> None:
    frame = pd.concat(
        [_complete_year(2023, 40.0), _complete_year(2024, 80.0)],
        ignore_index=True,
    )
    fig = a1.figure_heatmap(frame)
    assert len(fig.axes) >= 5
    by_title = {ax.get_title(): ax for ax in fig.axes}
    assert by_title[a1.EMPTY_PANEL_TITLE.format(year=2021)]
    assert by_title[a1.EMPTY_PANEL_TITLE.format(year=2022)]
    assert by_title["2023"]
    assert by_title["2024"]
    assert by_title[a1.EMPTY_PANEL_TITLE.format(year=2025)]
    assert len(by_title[a1.EMPTY_PANEL_TITLE.format(year=2021)].images) == 0
    assert len(by_title[a1.EMPTY_PANEL_TITLE.format(year=2022)].images) == 0
    assert len(by_title[a1.EMPTY_PANEL_TITLE.format(year=2025)].images) == 0
    ims = [by_title["2023"].images[0], by_title["2024"].images[0]]
    assert ims[0].get_clim() == ims[1].get_clim()
    plt.close(fig)


def test_duration_curves_2022_vermillion_linear_not_log() -> None:
    frame = pd.concat(
        [
            pd.DataFrame(
                [
                    _hour(year=2022, month=1, hour=i, price=float(200 - i), peak=False)
                    for i in range(5)
                ]
            ),
            pd.DataFrame(
                [
                    _hour(year=2023, month=1, hour=i, price=float(50 - i), peak=False)
                    for i in range(5)
                ]
            ),
        ],
        ignore_index=True,
    )
    fig = a1.figure_duration_curves(frame)
    ax = fig.axes[0]
    assert ax.get_yscale() == "linear"
    assert "100" in (ax.get_xlabel() or "") or "%" in (ax.get_xlabel() or "")
    assert "EUR/MWh" in (ax.get_ylabel() or "")
    hex_2022 = a1.duration_line_hex(fig, 2022)
    assert hex_2022 == OKABE_ITO["vermillion"].lower()
    line_2022 = next(ln for ln in ax.get_lines() if ln.get_label() == "2022")
    line_2023 = next(ln for ln in ax.get_lines() if ln.get_label() == "2023")
    assert line_2022.get_zorder() > line_2023.get_zorder()
    plt.close(fig)


def test_negative_stats_depth_and_daylight_share() -> None:
    frame = pd.DataFrame(
        [
            _hour(year=2023, month=6, hour=12, price=-10.0, peak=False),
            _hour(year=2023, month=1, hour=3, price=-30.0, peak=False),
            _hour(year=2023, month=6, hour=8, price=5.0, peak=True),
        ]
    )
    stats = a1.negative_hour_stats(frame)
    row = stats.iloc[0]
    assert int(row["n_negative"]) == 2
    assert float(row["mean_depth_eur_mwh"]) == pytest.approx(20.0)
    assert float(row["daylight_apr_sep_share"]) == pytest.approx(0.5)


def test_negative_hours_chart_has_bars() -> None:
    frame = pd.DataFrame([_hour(year=2023, month=6, hour=12, price=-4.0, peak=False)])
    fig = a1.figure_negative_hours(frame)
    ax = fig.axes[0]
    bars = [p for p in ax.patches if isinstance(p, Rectangle)]
    assert bars
    assert ax.get_xlabel() == "hour_local"
    plt.close(fig)


def test_so_what_interpolates_table_mentions_required_topics() -> None:
    summary = a1.annual_summary(_known_year())
    neg = a1.negative_hour_stats(_known_year())
    prose = a1.so_what_paragraph(summary, neg, n_dropped=1)
    assert "solar-driven midday depression" in prose.lower()
    assert "2022 crisis" in prose
    assert "flexible consumer" in prose.lower()
    assert format_eur_mwh(float(summary.iloc[0]["hourly_mean"])) in prose
    assert "501.0 EUR/MWh" not in prose
    sentences = [s for s in prose.split(". ") if s.strip()]
    assert 5 <= len(sentences) <= 12
    assert not any(line.strip().startswith("- ") for line in prose.splitlines())


def test_run_writes_artifacts_ssot_and_an704(tmp_settings: Settings) -> None:
    frame = pd.concat(
        [
            _complete_year(2022, 180.0),
            _known_year(),
            pd.DataFrame([_hour(year=2022, month=6, hour=12, price=-8.0, peak=False)]),
        ],
        ignore_index=True,
    )
    a1.run(tmp_settings, hourly=frame)
    out = kit.analytics_dir(tmp_settings)
    assert (out / "a1_annual_summary.md").is_file()
    assert (out / "a1_annual_summary.csv").is_file()
    assert (out / "a1_heatmap_hour_month.png").is_file()
    assert (out / "a1_duration_curves.png").is_file()
    assert (out / "a1_negative_hours.png").is_file()
    md = (out / "a1_annual_summary.md").read_text(encoding="utf-8")
    prose = kit.prose_after_last_table(md)
    assert len(prose) >= 400
    assert "solar-driven midday depression" in prose.lower()
    assert "2022 crisis" in prose
    assert "flexible consumer" in prose.lower()
    ssot = pd.read_parquet(kit.processed_dir(tmp_settings) / "ssot_inputs_analytics.parquet")
    keys = set(ssot["key"].astype(str))
    assert "neg_hours_2022" in keys
    assert "neg_hours_2023" in keys
    assert "annual_mean_price_2022" in keys
    assert (ssot["tag"] == "VERIFIED").all()
    assert (ssot["produced_by"] == a1.PRODUCED_BY).all()
    csv = pd.read_csv(out / "a1_annual_summary.csv")
    assert "hourly_mean" in csv.columns


def test_heatmap_png_stamped_rp702(tmp_settings: Settings, tmp_path: Path) -> None:
    fig = a1.figure_heatmap(_complete_year(2023, 30.0))
    dest = tmp_path / "heat.png"
    kit.save_png(fig, dest)
    assert dest.is_file()
    fig2 = a1.figure_heatmap(_complete_year(2023, 30.0))
    kit.stamp_rp702(fig2)
    assert tuple(fig2.get_size_inches()) == FIGSIZE
    texts = " ".join(t.get_text() for t in fig2.texts)
    assert SOURCE_NOTE in texts
    assert "VERIFIED" in texts
    plt.close(fig2)
