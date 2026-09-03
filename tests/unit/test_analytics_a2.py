"""A2 AT-DE-LU spread tests — synthetic stats, zero line, AN-704.

Implements: AN-201, AN-202, AN-203, AN-704.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from epra.analytics import _kit as kit
from epra.analytics import spread as a2
from epra.common.config import Settings
from epra.report.format import format_eur_mwh
from epra.report.style import SOURCE_NOTE


def _hour(
    *,
    year: int,
    month: int,
    at: float | None,
    delu: float | None,
    peak: bool,
) -> dict[str, object]:
    return {
        "year_local": year,
        "month_local": month,
        "hour_local": 12,
        "price_at_eur_mwh": at,
        "price_delu_eur_mwh": delu,
        "is_peak_hour": peak,
    }


def _known_spread() -> pd.DataFrame:
    """Peak spreads 10, 10; off-peak 2, 2; plus one NULL AT (dropped)."""
    return pd.DataFrame(
        [
            _hour(year=2023, month=1, at=20.0, delu=10.0, peak=True),
            _hour(year=2023, month=1, at=30.0, delu=20.0, peak=True),
            _hour(year=2023, month=1, at=12.0, delu=10.0, peak=False),
            _hour(year=2023, month=1, at=14.0, delu=12.0, peak=False),
            _hour(year=2023, month=1, at=None, delu=8.0, peak=False),
        ]
    )


def test_spread_stats_matches_hand_calc() -> None:
    stats = a2.spread_stats(_known_spread())
    assert list(stats.columns) == list(a2.AN202_COLUMNS)
    row = stats.iloc[0]
    spreads = np.array([10.0, 10.0, 2.0, 2.0])
    assert int(row["n_hours"]) == 4
    assert float(row["spread_mean"]) == pytest.approx(float(spreads.mean()))
    assert float(row["spread_median"]) == pytest.approx(6.0)
    assert float(row["spread_std"]) == pytest.approx(float(pd.Series(spreads).std(ddof=1)))
    assert float(row["share_at_gt_delu"]) == pytest.approx(1.0)
    assert float(row["spread_mean_peak"]) == pytest.approx(10.0)
    assert float(row["spread_mean_offpeak"]) == pytest.approx(2.0)
    assert a2.count_dropped_spread_hours(_known_spread()) == 1


def test_null_on_either_side_dropped_not_zero() -> None:
    frame = pd.concat(
        [
            _known_spread(),
            pd.DataFrame([_hour(year=2023, month=1, at=0.0, delu=0.0, peak=False)]),
        ],
        ignore_index=True,
    )
    stats = a2.spread_stats(frame)
    assert int(stats.iloc[0]["n_hours"]) == 5
    assert float(stats.iloc[0]["spread_mean"]) == pytest.approx(4.8)


def test_share_at_gt_delu_partial() -> None:
    frame = pd.DataFrame(
        [
            _hour(year=2022, month=3, at=5.0, delu=10.0, peak=False),
            _hour(year=2022, month=3, at=12.0, delu=10.0, peak=True),
        ]
    )
    assert float(a2.spread_stats(frame).iloc[0]["share_at_gt_delu"]) == pytest.approx(0.5)


def test_monthly_chart_has_zero_line() -> None:
    fig = a2.figure_spread_monthly(_known_spread())
    assert a2.zero_line_present(fig)
    ax = fig.axes[0]
    assert "EUR/MWh" in (ax.get_ylabel() or "")
    from matplotlib import pyplot as plt

    plt.close(fig)


def test_so_what_mentions_germany_and_interpolates() -> None:
    stats = a2.spread_stats(_known_spread())
    prose = a2.so_what_paragraph(stats, n_dropped=1)
    assert "you are not in germany" in prose.lower()
    assert "austrian" in prose.lower()
    assert format_eur_mwh(float(stats.iloc[0]["spread_mean"])) in prose
    assert "999.0 EUR/MWh" not in prose
    sentences = [s for s in prose.split(". ") if s.strip()]
    assert 5 <= len(sentences) <= 12


def test_run_writes_artifacts_ssot_and_an704(tmp_settings: Settings) -> None:
    a2.run(tmp_settings, hourly=_known_spread())
    out = kit.analytics_dir(tmp_settings)
    assert (out / "a2_spread_summary.md").is_file()
    assert (out / "a2_spread_monthly.png").is_file()
    md = (out / "a2_spread_summary.md").read_text(encoding="utf-8")
    prose = kit.prose_after_last_table(md)
    assert len(prose) >= 400
    assert "you are not in germany" in prose.lower()
    ssot = pd.read_parquet(kit.processed_dir(tmp_settings) / "ssot_inputs_analytics.parquet")
    assert "spread_mean_2023" in set(ssot["key"].astype(str))
    assert (ssot["tag"] == "VERIFIED").all()
    assert (ssot["produced_by"] == a2.PRODUCED_BY).all()
    texts = []
    fig = a2.figure_spread_monthly(_known_spread())
    kit.stamp_rp702(fig)
    texts.append(" ".join(t.get_text() for t in fig.texts))
    from matplotlib import pyplot as plt

    plt.close(fig)
    assert SOURCE_NOTE in texts[0]
