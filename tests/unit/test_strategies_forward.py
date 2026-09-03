"""T6.07 forward cells, ADR-014 mapping, ADR-015 summarize.

Implements: ST-401..406, ST-602, ADR-014, ADR-015, D-07..D-12.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from matplotlib import pyplot as plt

from epra.common.config import Settings, load_strategy_config
from epra.common.db import warehouse_path
from epra.strategies.calibration import Anchors
from epra.strategies.forward_risk import (
    ST502_SENTENCE,
    build_cost_cells,
    check_st602c,
    figure_forward_fan,
    main,
    map_month,
    no_crisis_years,
    p_s3_forward,
    run,
    simulate,
    summarize,
)

_ANCHORS = Anchors(p_ref_base=50.0, p_ref_peak=70.0, oespi_base_ref=100.0, oespi_peak_ref=100.0)


def _hour(
    ts: str,
    *,
    year: int,
    month: int,
    day: int,
    hour_local: int,
    load: float,
    price: float,
    weekend: bool = False,
) -> dict[str, object]:
    return {
        "ts_utc": pd.Timestamp(ts, tz="UTC"),
        "load_mwh": load,
        "price_at_eur_mwh": price,
        "year_local": year,
        "month_local": month,
        "date_local": date(year, month, day),
        "hour_local": hour_local,
        "is_weekend": weekend,
    }


def _oespi_year(year: int, value: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year_local": [year] * 12,
            "month_local": list(range(1, 13)),
            "oespi_base": [value] * 12,
            "oespi_peak": [value] * 12,
        }
    )


def _h(
    ts: str,
    year: int,
    month: int,
    day: int,
    hour_local: int,
    load: float,
    price: float,
    weekend: bool = False,
) -> dict[str, object]:
    return _hour(
        ts,
        year=year,
        month=month,
        day=day,
        hour_local=hour_local,
        load=load,
        price=price,
        weekend=weekend,
    )


def _toy_cfg() -> object:
    cfg = load_strategy_config()
    return cfg.model_copy(
        update={"forward": cfg.forward.model_copy(update={"n_paths": 20, "horizon_months": 2})}
    )


def _toy_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    horizon = pd.DataFrame(
        [
            _h("2023-01-01 11:00:00", 2023, 1, 1, 12, 10.0, 0.0),
            _h("2023-02-01 11:00:00", 2023, 2, 1, 12, 5.0, 0.0),
        ]
    )
    pool = pd.DataFrame(
        [
            _h("2021-01-01 11:00:00", 2021, 1, 1, 12, 10.0, 40.0),
            _h("2022-01-01 11:00:00", 2022, 1, 1, 12, 10.0, 80.0),
            _h("2021-02-01 11:00:00", 2021, 2, 1, 12, 5.0, 20.0),
            _h("2022-02-01 11:00:00", 2022, 2, 1, 12, 5.0, 60.0),
        ]
    )
    oespi = pd.concat([_oespi_year(2021), _oespi_year(2022), _oespi_year(2023)], ignore_index=True)
    return horizon, pool, oespi


def test_map_month_identity_and_forward_fill() -> None:
    drawn = pd.DataFrame(
        [
            _h("2021-01-01 00:00:00", 2021, 1, 1, 0, 1.0, 10.0),
            _h("2021-01-01 01:00:00", 2021, 1, 1, 1, 1.0, 20.0),
            _h("2021-01-01 03:00:00", 2021, 1, 1, 3, 1.0, 40.0),
        ]
    )
    target = pd.DataFrame(
        [
            _h("2023-01-01 00:00:00", 2023, 1, 1, 0, 2.0, 0.0),
            _h("2023-01-01 01:00:00", 2023, 1, 1, 1, 2.0, 0.0),
            _h("2023-01-01 02:00:00", 2023, 1, 1, 2, 2.0, 0.0),
            _h("2023-01-01 03:00:00", 2023, 1, 1, 3, 2.0, 0.0),
        ]
    )
    mapped = map_month(drawn, target)
    prices = list(mapped["price_at_eur_mwh"])
    assert prices[0] == pytest.approx(10.0)
    assert prices[1] == pytest.approx(20.0)
    assert prices[2] == pytest.approx(20.0)
    assert prices[3] == pytest.approx(40.0)


def test_map_month_overflow_uses_last_same_weekend() -> None:
    drawn = pd.DataFrame(
        [
            _hour(
                "2021-04-01 12:00:00",
                year=2021,
                month=4,
                day=1,
                hour_local=12,
                load=1.0,
                price=11.0,
                weekend=False,
            ),
            _hour(
                "2021-04-03 12:00:00",
                year=2021,
                month=4,
                day=3,
                hour_local=12,
                load=1.0,
                price=33.0,
                weekend=True,
            ),
        ]
    )
    target = pd.DataFrame(
        [
            _hour(
                "2023-05-31 12:00:00",
                year=2023,
                month=5,
                day=31,
                hour_local=12,
                load=1.0,
                price=0.0,
                weekend=True,
            )
        ]
    )
    mapped = map_month(drawn, target)
    assert float(mapped["price_at_eur_mwh"].iloc[0]) == pytest.approx(33.0)


def test_cell_equals_direct_s1_on_two_month_toy() -> None:
    horizon, pool, oespi = _toy_frames()
    cfg = _toy_cfg()
    cells = build_cost_cells(
        horizon, pool, oespi, _ANCHORS, 0.4, cfg, (2022, 12), [(2023, 1), (2023, 2)]
    )
    s1 = cells.frame.loc[cells.frame["strategy_id"] == "S1"]
    jan_2022 = float(
        s1.loc[(s1["horizon_month"] == 1) & (s1["pool_year"] == 2022), "cost_eur"].iloc[0]
    )
    feb_2021 = float(
        s1.loc[(s1["horizon_month"] == 2) & (s1["pool_year"] == 2021), "cost_eur"].iloc[0]
    )
    assert jan_2022 == pytest.approx(800.0)
    assert feb_2021 == pytest.approx(100.0)
    assert jan_2022 + feb_2021 == pytest.approx(900.0)


def test_simulate_determinism_and_quantiles() -> None:
    horizon, pool, oespi = _toy_frames()
    cfg = _toy_cfg()
    cells = build_cost_cells(
        horizon, pool, oespi, _ANCHORS, 0.4, cfg, (2022, 12), [(2023, 1), (2023, 2)]
    )
    a = simulate(cells, 42, 20)
    b = simulate(cells, 42, 20)
    pd.testing.assert_frame_equal(a, b)
    summary = summarize(a)
    for rec in summary.itertuples(index=False):
        assert rec.p5 <= rec.p50 <= rec.p95


def test_summarize_adr015_closed_form() -> None:
    costs = np.arange(20.0, dtype=np.float64)
    paths = pd.DataFrame({"S1": costs})
    for sid in ("S2", "S3", "S4_30", "S4_50", "S4_70"):
        paths[sid] = costs
    out = summarize(paths)
    s1 = out.loc[out["strategy_id"] == "S1"].iloc[0]
    expected_p = np.quantile(costs, [0.05, 0.50, 0.95], method="linear")
    assert float(s1["p5"]) == pytest.approx(float(expected_p[0]))
    assert float(s1["p50"]) == pytest.approx(float(expected_p[1]))
    assert float(s1["p95"]) == pytest.approx(float(expected_p[2]))
    k = int(np.ceil(0.05 * 20))
    assert k == 1
    assert float(s1["cvar95"]) == pytest.approx(19.0)


def test_st602c_on_crafted_fatter_s1_tail() -> None:
    paths = pd.DataFrame(
        {
            "S1": np.linspace(10.0, 100.0, 20),
            "S2": np.linspace(10.0, 40.0, 20),
            "S3": np.linspace(10.0, 40.0, 20),
            "S4_30": np.linspace(10.0, 70.0, 20),
            "S4_50": np.linspace(10.0, 70.0, 20),
            "S4_70": np.linspace(10.0, 70.0, 20),
        }
    )
    summary = summarize(paths)
    check_st602c(summary)
    skinny = summary.copy()
    skinny.loc[skinny["strategy_id"] == "S1", "p95"] = 1.0
    skinny.loc[skinny["strategy_id"] == "S3", "p95"] = 9.0
    with pytest.raises(RuntimeError, match="ST-602"):
        check_st602c(skinny)


def test_drawn_lock_branch_and_missing_raises() -> None:
    oespi = _oespi_year(2021, 100.0)
    cfg = load_strategy_config()
    drawn = {(2021, m): (200.0, 200.0) for m in range(7, 13)}
    price = p_s3_forward(2022, oespi, _ANCHORS, cfg, 0.4, (2021, 6), drawn)
    observed_only = p_s3_forward(2022, oespi, _ANCHORS, cfg, 0.4, (2021, 12), {})
    assert price != pytest.approx(observed_only)
    with pytest.raises(ValueError, match="future lock month"):
        p_s3_forward(2022, oespi, _ANCHORS, cfg, 0.4, (2021, 6), {})


def test_no_crisis_excludes_crisis_december() -> None:
    dates = pd.Series(pd.to_datetime(["2021-12-15", "2022-12-15"]))
    labels = pd.Series(["crisis", "calm"])
    kept = no_crisis_years(dates, labels, [2021, 2022, 2023])
    assert kept == {2022}


def test_run_writes_simulated_artifacts(tmp_settings: Settings) -> None:
    horizon, pool, oespi = _toy_frames()
    cfg = _toy_cfg()
    dates = pd.Series(pd.to_datetime(["2021-12-15", "2022-12-15"]))
    labels = pd.Series(["calm", "calm"])
    paths = run(
        tmp_settings,
        horizon_hours=horizon,
        pool_hourly=pool,
        monthly_oespi=oespi,
        anchors=_ANCHORS,
        w_peak=0.4,
        cfg=cfg,
        data_last_month=(2022, 12),
        n_paths=20,
        dates=dates,
        labels=labels,
    )
    assert len(paths) == 20
    reports = tmp_settings.paths.reports / "strategies"
    assert (reports / "s5_forward_fan.png").is_file()
    assert (reports / "s5_risk_return.png").is_file()
    md = (reports / "s5_forward_risk.md").read_text(encoding="utf-8")
    assert ST502_SENTENCE in md
    ssot = pd.read_parquet(tmp_settings.paths.data_processed / "ssot_inputs_strategies.parquet")
    assert "p95_next12m_S1" in set(ssot["key"].astype(str))
    assert (ssot["tag"] == "SIMULATED").all()
    fig = figure_forward_fan(paths)
    texts = " ".join(t.get_text() for t in fig.texts)
    assert ST502_SENTENCE in texts
    plt.close(fig)


def test_cli_missing_warehouse_exits_1(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("epra.common.config.load_settings", lambda: tmp_settings)
    assert not warehouse_path(tmp_settings).is_file()
    assert main([]) == 1
