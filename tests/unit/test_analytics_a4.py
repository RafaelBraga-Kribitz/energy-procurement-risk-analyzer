"""A4 weather/load OLS tests — synthetic HDD slope, invariance prose.

Implements: AN-401, AN-402, AN-704, SPEC-04 §5.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from epra.analytics import _kit as kit
from epra.analytics import weather as a4
from epra.common.config import Settings
from epra.report.style import SOURCE_NOTE


def _synthetic_hourly() -> pd.DataFrame:
    """load = 5000 + 15*hdd_18 + 8*month; HDD is the given column, not 18-tavg."""
    rows: list[dict[str, object]] = []
    for month in range(1, 13):
        for day in (5, 12, 19, 26):
            day_local = date(2023, month, day)
            hdd = float(day)
            load = 5000.0 + 15.0 * hdd + 8.0 * month
            tavg = 20.0  # would imply HDD_18 = 0 if recomputed; must be ignored
            for hour in (0, 12):
                rows.append(
                    {
                        "date_local": day_local,
                        "year_local": 2023,
                        "month_local": month,
                        "hour_local": hour,
                        "load_at_mw": load,
                        "hdd_18": hdd,
                        "tavg_c": tavg,
                        "is_weekend": day_local.weekday() >= 5,
                    }
                )
    return pd.DataFrame(rows)


def test_fit_load_hdd_recovers_positive_slope() -> None:
    daily = a4.daily_system_load(_synthetic_hourly())
    fit = a4.fit_load_hdd(daily)
    assert fit.hdd_coef == pytest.approx(15.0, rel=1e-6, abs=1e-6)
    assert fit.hdd_coef > 0
    assert fit.cov_type == "HC1"
    assert "C(month_local)" in fit.formula
    assert fit.n_obs == 48


def test_hdd_column_used_as_given_not_recomputed_from_tavg() -> None:
    src = Path(a4.__file__).read_text(encoding="utf-8")
    assert "tavg_c" not in src
    assert "18 -" not in src
    daily = a4.daily_system_load(_synthetic_hourly())
    assert float(daily["hdd_18"].min()) > 0
    fit = a4.fit_load_hdd(daily)
    assert fit.hdd_coef > 0


def test_scatter_colored_by_weekend() -> None:
    daily = a4.daily_system_load(_synthetic_hourly())
    fit = a4.fit_load_hdd(daily)
    fig = a4.figure_load_vs_hdd(daily, fit)
    ax = fig.axes[0]
    assert len(ax.collections) >= 2
    assert "HDD_18" in (ax.get_xlabel() or "")
    assert "MW" in (ax.get_ylabel() or "")
    from matplotlib import pyplot as plt

    plt.close(fig)


def test_invariance_sentence_in_prose() -> None:
    daily = a4.daily_system_load(_synthetic_hourly())
    fit = a4.fit_load_hdd(daily)
    prose = a4.so_what_paragraph(fit, n_days=len(daily), n_dropped=0)
    assert "weather-invariant by construction" in prose
    assert "SYSTEM" in prose or "system" in prose
    assert "StyriaMetal" in prose
    sentences = [s for s in prose.split(". ") if s.strip()]
    assert 5 <= len(sentences) <= 12


def test_run_writes_artifacts_and_an704(tmp_settings: Settings) -> None:
    a4.run(tmp_settings, hourly=_synthetic_hourly())
    out = kit.analytics_dir(tmp_settings)
    assert (out / "a4_load_weather.md").is_file()
    assert (out / "a4_load_vs_hdd.png").is_file()
    md = (out / "a4_load_weather.md").read_text(encoding="utf-8")
    prose = kit.prose_after_last_table(md)
    assert len(prose) >= 400
    assert a4.INVARIANCE_SENTENCE in md
    fig = a4.figure_load_vs_hdd(
        a4.daily_system_load(_synthetic_hourly()),
        a4.fit_load_hdd(a4.daily_system_load(_synthetic_hourly())),
    )
    kit.stamp_rp702(fig)
    texts = " ".join(t.get_text() for t in fig.texts)
    from matplotlib import pyplot as plt

    plt.close(fig)
    assert SOURCE_NOTE in texts
