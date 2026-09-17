"""A3 HMM / realized-vol / AN-304 tests.

Implements: AN-301, AN-302, AN-304, AN-705, D-06, D-09, D-10, T-3.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from epra.analytics import _kit as kit
from epra.analytics import regimes as a3
from epra.common.config import Settings


def test_daily_diff_is_arithmetic_not_log() -> None:
    frame = pd.DataFrame(
        {
            "date_local": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]),
            "price_base_eur_mwh": [10.0, 20.0, None, 5.0],
        }
    )
    out = a3.daily_diff(frame)
    assert list(out["d_t"]) == pytest.approx([10.0])


def test_fit_hmm_deterministic_and_labels_by_std() -> None:
    rng = np.random.default_rng(7)
    series = np.concatenate(
        [
            rng.normal(0.0, 0.05, 90),
            rng.normal(0.0, 0.9, 90),
            rng.normal(0.0, 3.5, 90),
        ]
    )
    z = a3.zscore(series)
    fit_a = a3.fit_hmm(z)
    fit_b = a3.fit_hmm(z)
    assert np.array_equal(fit_a.state_sequence, fit_b.state_sequence)
    assert fit_a.restart_seed_used == fit_b.restart_seed_used
    assert fit_a.n_components == 3
    assert fit_a.covariance_type == "full"
    assert fit_a.n_iter == 500
    stds = []
    for name in a3.LABELS:
        stds.append(float(z[fit_a.labels == name].std()))
    assert stds[0] < stds[1] < stds[2]


def _labeled_calendar(start: date, end: date, label: str) -> tuple[pd.Series, pd.Series]:
    days = pd.date_range(start, end, freq="D")
    dates = pd.Series(days)
    labels = pd.Series([label] * len(days))
    return dates, labels


def test_check_an304_skip_without_2019() -> None:
    dates, labels = _labeled_calendar(date(2022, 1, 1), date(2022, 12, 31), "crisis")
    result = a3.check_an304(dates, labels)
    assert result.status == "skip"
    assert result.status != "pass"
    assert "2019" in result.reason


def test_check_an304_fail_closed_when_coverage_exists() -> None:
    d2019, l2019 = _labeled_calendar(date(2019, 1, 1), date(2019, 12, 31), "crisis")
    dwin, lwin = _labeled_calendar(date(2021, 9, 1), date(2023, 6, 30), "calm")
    result = a3.check_an304(
        pd.concat([d2019, dwin], ignore_index=True),
        pd.concat([l2019, lwin], ignore_index=True),
    )
    assert result.status == "fail"
    assert result.calm_2019_share is not None
    assert result.calm_2019_share < 0.60
    assert result.crisis_window_top2_share is not None
    assert result.crisis_window_top2_share < 0.70


def test_check_an304_pass_on_constructed_labels() -> None:
    d2019, l2019 = _labeled_calendar(date(2019, 1, 1), date(2019, 12, 31), "calm")
    dwin, lwin = _labeled_calendar(date(2021, 9, 1), date(2023, 6, 30), "crisis")
    result = a3.check_an304(
        pd.concat([d2019, dwin], ignore_index=True),
        pd.concat([l2019, lwin], ignore_index=True),
    )
    assert result.status == "pass"
    assert result.calm_2019_share is not None
    assert result.calm_2019_share >= 0.60
    assert result.crisis_window_top2_share is not None
    assert result.crisis_window_top2_share >= 0.70


def test_december_regime_majority_and_calm_tiebreak() -> None:
    days = [date(2022, 12, d) for d in range(1, 21)]
    dates = pd.Series(pd.to_datetime(days))
    labels = pd.Series(["crisis"] * 12 + ["calm"] * 8)
    assert a3.december_regime(2022, dates, labels) == "crisis"
    tied = pd.Series(["crisis"] * 10 + ["calm"] * 10)
    assert a3.december_regime(2022, dates, tied) == "calm"


def test_realized_vol_twin_axis() -> None:
    n = 40
    frame = pd.DataFrame(
        {
            "date_local": pd.date_range("2022-01-01", periods=n, freq="D"),
            "price_base_eur_mwh": np.linspace(50.0, 80.0, n),
            "d_t": np.linspace(-1.0, 1.0, n),
        }
    )
    fig = a3.figure_realized_vol(frame)
    assert len(fig.axes) == 2
    ylabels = " ".join(ax.get_ylabel() or "" for ax in fig.axes)
    assert "EUR/MWh" in ylabels
    from matplotlib import pyplot as plt

    plt.close(fig)


def test_run_writes_hmm_artifacts_and_an704(tmp_settings: Settings) -> None:
    rng = np.random.default_rng(3)
    n = 270
    prices = 80.0 + np.cumsum(
        np.concatenate(
            [
                rng.normal(0.0, 0.05, 90),
                rng.normal(0.0, 0.9, 90),
                rng.normal(0.0, 3.0, 90),
            ]
        )
    )
    daily = pd.DataFrame(
        {
            "date_local": pd.date_range("2023-01-01", periods=n, freq="D"),
            "price_base_eur_mwh": prices,
        }
    )
    a3.run(tmp_settings, daily=daily)
    out = kit.analytics_dir(tmp_settings)
    assert (out / "a3_realized_vol.png").is_file()
    assert (out / "a3_regimes.png").is_file()
    md_path = out / "a3_regime_stats.md"
    assert md_path.is_file()
    prose = kit.prose_after_last_table(md_path.read_text(encoding="utf-8"))
    assert len(prose) >= 400
    assert "log" in prose.lower()  # explains why NOT logs
    assert "arithmetic" in prose.lower()


def test_run_writes_garch_overlay_and_ssot(tmp_settings: Settings) -> None:
    daily = pd.DataFrame(
        {
            "date_local": pd.date_range("2023-01-01", periods=120, freq="D"),
            "price_base_eur_mwh": np.linspace(40.0, 60.0, 120) + np.sin(np.arange(120)),
        }
    )
    a3.run(tmp_settings, daily=daily)
    out = kit.analytics_dir(tmp_settings)
    assert (out / "a3_garch_vs_realized.png").is_file()
    ssot = pd.read_parquet(kit.processed_dir(tmp_settings) / "ssot_inputs_analytics.parquet")
    row = ssot.loc[ssot["key"] == "garch_persistence"].iloc[0]
    assert row["tag"] == "VERIFIED"
    assert row["produced_by"] == a3.PRODUCED_BY


def test_garch_persistence_identity() -> None:
    rng = np.random.default_rng(11)
    d_t = rng.normal(0.0, 2.0, 250)
    a = a3.fit_garch(d_t)
    b = a3.fit_garch(d_t)
    assert a.persistence == b.persistence
    assert a.alpha == b.alpha
    assert a.beta == b.beta
    assert a.scale == 1.0
    assert "unscaled" in a.rescale_note


def test_near_integrated_persistence_is_not_clamped() -> None:
    garch = a3.GarchFit(
        persistence=1.05,
        alpha=0.20,
        beta=0.85,
        scale=1.0,
        rescale_note=a3._garch_note(1.0, 1.05),
        conditional_vol=np.ones(8),
        near_integrated=True,
    )
    assert garch.persistence == 1.05
    assert garch.near_integrated
    assert "not clamped" in garch.rescale_note
    frame = pd.DataFrame(
        {
            "date_local": pd.date_range("2022-01-01", periods=8, freq="D"),
            "d_t": np.arange(8, dtype=float),
        }
    )
    fig = a3.figure_garch_vs_realized(frame, garch)
    texts = " ".join(t.get_text() for t in fig.texts)
    assert "not clamped" in texts
    from matplotlib import pyplot as plt

    plt.close(fig)


def test_scale_warning_detection() -> None:
    assert a3._scale_warning_seen(["y is poorly scaled"])
    assert not a3._scale_warning_seen(["convergence warning"])
