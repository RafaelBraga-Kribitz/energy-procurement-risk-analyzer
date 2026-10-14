"""SPEC-05 M6 tests: formulas against known truth (synthetic inputs only),
no-lookahead (ST-503), bootstrap mechanics, determinism (ST-405), sanity
relations (ST-602), and an end-to-end run on the synthetic warehouse.

Strategy "recovery" is tested on synthetic inputs only — never as results.

Implements tests for: ST-101..107, ST-201..204, ST-301..303, ST-401..406,
ST-501..503, ST-602, ST-603.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

from epra.common.config import REPO_ROOT, Settings
from epra.common.frames import scalar
from epra.common.ssot import read_ssot_rows
from epra.strategies import forward_risk as fr
from epra.strategies.calibration import Anchors, anchors_from_inputs
from epra.strategies.engine import (
    StrategyParams,
    annual_summary,
    indexed_price,
    lock_price,
    monthly_costs,
    wrong_strategy_cost,
)
from epra.strategies.gates import sanity_failures
from epra.strategies.inputs import ReferenceStats

ANCHORS = Anchors(p_ref_base=40.0, p_ref_peak=50.0, oespi_base_ref=100.0, oespi_peak_ref=80.0)


def _params(**overrides: object) -> StrategyParams:
    values: dict[str, object] = {
        "anchors": ANCHORS,
        "w_peak": 0.4,
        "fixed_premium_eur_mwh": 5.0,
        "lock_window_months": (7, 8, 9, 10, 11, 12),
        "hybrid_ratios": (0.3, 0.5, 0.7),
        "peak_available": True,
    }
    values.update(overrides)
    return StrategyParams(**values)  # type: ignore[arg-type]


def _oespi(years: range, base: float = 100.0, peak: float = 80.0) -> pd.DataFrame:
    rows = [(y, m, base, peak) for y in years for m in range(1, 13)]
    return pd.DataFrame(rows, columns=["year_local", "month_local", "oespi_base", "oespi_peak"])


def _spot(years: range, price: float, volume: float = 1000.0) -> pd.DataFrame:
    rows = [(y, m, volume, volume * price) for y in years for m in range(1, 13)]
    return pd.DataFrame(rows, columns=["year_local", "month_local", "volume_mwh", "spot_cost_eur"])


# ---------------------------------------------------------------- calibration


def test_st201_202_203_anchor_formulas() -> None:
    ref = ReferenceStats(
        consumer_cost_eur=2_000_000.0,
        consumer_volume_mwh=50_000.0,
        mean_price_all_hours_eur_mwh=38.0,
        mean_price_peak_eur_mwh=45.0,
    )
    oespi = _oespi(range(2019, 2020), base=104.0, peak=90.0)
    a = anchors_from_inputs(ref, oespi, 2019)
    assert a.p_ref_base == pytest.approx(40.0)
    assert a.p_ref_peak == pytest.approx(45.0 * 40.0 / 38.0)
    assert (a.oespi_base_ref, a.oespi_peak_ref) == (104.0, 90.0)


def test_anchor_reference_year_must_be_complete() -> None:
    ref = ReferenceStats(1.0, 1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="11/12"):
        anchors_from_inputs(ref, _oespi(range(2019, 2020)).iloc[:11], 2019)


# ------------------------------------------------------------------- formulas


def test_st102_index_at_reference_gives_anchor_blend() -> None:
    price = indexed_price(100.0, 80.0, _params())
    assert float(price) == pytest.approx(40.0 * 0.6 + 50.0 * 0.4)
    doubled = indexed_price(200.0, 160.0, _params())
    assert float(doubled) == pytest.approx(2 * float(price))


def test_st104_base_only_mode() -> None:
    assert float(indexed_price(150.0, 999.0, _params(peak_available=False))) == pytest.approx(60.0)


def test_st105_lock_price_premium_included() -> None:
    oespi = _oespi(range(2020, 2023))
    assert lock_price(oespi, 2022, _params()) == pytest.approx(44.0 + 5.0)


def test_st503_lock_uses_only_prior_h2_index() -> None:
    oespi = _oespi(range(2020, 2023))
    reference = lock_price(oespi, 2022, _params())
    tampered = oespi.copy()
    outside = ~((tampered["year_local"] == 2021) & (tampered["month_local"] >= 7))
    tampered.loc[outside, ["oespi_base", "oespi_peak"]] = 1e6  # incl. all of 2022
    assert lock_price(tampered, 2022, _params()) == pytest.approx(reference)
    inside = (tampered["year_local"] == 2021) & (tampered["month_local"] == 9)
    tampered.loc[inside, "oespi_base"] = 400.0
    assert lock_price(tampered, 2022, _params()) != pytest.approx(reference)


def test_lock_window_incomplete_raises() -> None:
    oespi = _oespi(range(2021, 2023))
    with pytest.raises(ValueError, match="lock window"):
        lock_price(oespi[oespi["month_local"] != 10], 2022, _params())


def test_monthly_costs_known_truth_and_equal_volumes() -> None:
    years = range(2020, 2023)
    out = monthly_costs(_spot(years, price=100.0), _oespi(years), _params(), [2021, 2022])
    by = out.groupby("strategy_id")
    assert set(by["volume_mwh"].sum()) == {24_000.0}  # ST-501: identical volumes
    unit = by["cost_eur"].sum() / by["volume_mwh"].sum()
    assert unit["S1"] == pytest.approx(100.0)
    assert unit["S2"] == pytest.approx(44.0)
    assert unit["S3"] == pytest.approx(49.0)
    assert unit["S4_30"] == pytest.approx(0.3 * 49.0 + 0.7 * 100.0)
    assert unit["S4_70"] == pytest.approx(0.7 * 49.0 + 0.3 * 100.0)
    assert list(out.columns) == [
        "year_local",
        "month_local",
        "strategy_id",
        "volume_mwh",
        "cost_eur",
        "unit_cost_eur_mwh",
    ]


def test_missing_index_month_raises() -> None:
    years = range(2020, 2023)
    oespi = _oespi(years)
    oespi = oespi[~((oespi["year_local"] == 2022) & (oespi["month_local"] == 3))]
    with pytest.raises(ValueError, match="ÖSPI missing"):
        monthly_costs(_spot(years, 100.0), oespi, _params(), [2022])


def test_st301_302_annual_summary_rank_delta_wrong_cost() -> None:
    years = range(2020, 2023)
    annual = annual_summary(monthly_costs(_spot(years, 100.0), _oespi(years), _params(), [2022]))
    s1 = annual.set_index("strategy_id").loc["S1"]
    assert s1["rank"] == 6
    assert s1["delta_vs_min_eur"] == pytest.approx((100.0 - 44.0) * 12_000.0)
    assert float(wrong_strategy_cost(annual).loc[2022]) == pytest.approx(56.0 * 12_000.0)


# ---------------------------------------------------------------- ST-602 gate


def _annual(s1: float, s3: float, s4: float) -> pd.DataFrame:
    return pd.DataFrame(
        {"year": 2022, "strategy_id": ["S1", "S3", "S4_50"], "cost_eur": [s1, s3, s4]}
    )


def _forward(s1: float, s3: float) -> pd.DataFrame:
    return pd.DataFrame({"variant": "unconditional", "strategy_id": ["S1", "S3"], "p95": [s1, s3]})


def test_st602_passes_and_each_relation_can_fail() -> None:
    assert sanity_failures(_annual(10, 5, 7.5), _forward(9, 8)) == []
    assert any("(a)" in f for f in sanity_failures(_annual(5, 10, 7.5), _forward(9, 8)))
    assert any("(b)" in f for f in sanity_failures(_annual(10, 5, 11), _forward(9, 8)))
    assert any("(c)" in f for f in sanity_failures(_annual(10, 5, 7.5), _forward(7, 8)))


# ------------------------------------------------------------ forward pieces


def test_target_months_wrap_year() -> None:
    assert fr.target_months((2025, 11), 3) == [(2025, 12), (2026, 1), (2026, 2)]


def _month(days: int, first_weekend: set[int], price_of_day: bool = True) -> pd.DataFrame:
    rows = [
        (d, h, d in first_weekend, float(d * 100 + h) if price_of_day else 1.0)
        for d in range(1, days + 1)
        for h in range(24)
    ]
    return pd.DataFrame(
        rows, columns=["day_local", "hour_local", "is_weekend_or_holiday", "price_at_eur_mwh"]
    )


def test_st401_align_extra_day_reuses_last_same_type_day() -> None:
    drawn = _month(30, first_weekend={29, 30})
    target = _month(31, first_weekend={30, 31}).drop(columns="price_at_eur_mwh")
    aligned = fr.align_prices(drawn, target)
    day31 = aligned[target["day_local"].to_numpy() == 31]
    assert day31[5] == pytest.approx(30 * 100 + 5)  # last weekend day of drawn month
    assert aligned[0] == pytest.approx(100.0)


def test_st401_align_dst_missing_hour_forward_filled_and_duplicates_averaged() -> None:
    drawn = _month(2, first_weekend=set())
    drawn = drawn[~((drawn["day_local"] == 1) & (drawn["hour_local"] == 2))]
    dup = pd.DataFrame([(2, 2, False, 9999.0)], columns=drawn.columns)
    drawn = pd.concat([drawn, dup], ignore_index=True)
    target = _month(2, first_weekend=set()).drop(columns="price_at_eur_mwh")
    aligned = fr.align_prices(drawn, target)
    assert aligned[2] == pytest.approx(aligned[1])  # 01 02:00 missing -> ffill from 01:00
    assert aligned[24 + 2] == pytest.approx((202.0 + 9999.0) / 2)


def test_st403_risk_metrics_cvar_is_mean_of_worst_5pct() -> None:
    costs = pd.Series(np.arange(1, 101, dtype=float))
    m = fr.risk_metrics(costs)
    assert m["cvar95"] == pytest.approx(np.mean([96, 97, 98, 99, 100]))
    assert m["p50"] == pytest.approx(50.5)
    assert m["cvar95"] >= m["p95"]


def _cells() -> fr.Cells:
    return fr.Cells(
        targets=[(2026, 11), (2026, 12), (2027, 1)],
        pool_years=[[2019, 2020], [2019, 2020, 2021], [2020, 2021]],
        volume=np.array([10.0, 20.0, 30.0]),
        spot_cost=[np.array([100.0, 200.0]), np.array([1.0, 2.0, 3.0]), np.array([1000.0, 5000.0])],
        oespi_base=[
            np.array([100.0, 200.0]),
            np.array([100.0, 300.0, 500.0]),
            np.array([100.0, 100.0]),
        ],
        oespi_peak=[
            np.array([80.0, 160.0]),
            np.array([80.0, 240.0, 400.0]),
            np.array([80.0, 80.0]),
        ],
    )


def test_st405_draws_seed_deterministic_and_in_range() -> None:
    cells = _cells()
    first, second = fr.draw_indices(cells, 500, 42), fr.draw_indices(cells, 500, 42)
    np.testing.assert_array_equal(first, second)
    assert (first.max(axis=0) < np.array([2, 3, 2])).all()
    assert not np.array_equal(first, fr.draw_indices(cells, 500, 43))


def test_st406_vectorized_equals_hour_by_hour_loop() -> None:
    cells = _cells()
    draws = fr.draw_indices(cells, 50, 7)
    oespi = pd.DataFrame(
        {
            "year_local": [2025] * 12 + [2026] * 10,
            "month_local": list(range(1, 13)) + list(range(1, 11)),
            "oespi_base": 100.0,
            "oespi_peak": 80.0,
        }
    )
    params = _params(lock_window_months=(7, 8, 9, 10, 11, 12))
    fast = fr.path_costs(cells, draws, oespi, params)
    for path in (0, 13, 49):
        idx = draws[path]
        s1 = sum(cells.spot_cost[t][idx[t]] for t in range(3))
        s2 = sum(
            cells.volume[t]
            * float(indexed_price(cells.oespi_base[t][idx[t]], cells.oespi_peak[t][idx[t]], params))
            for t in range(3)
        )
        # 2026 delivery: lock 2025-H2 observed (=44 + 5). 2027: lock 2026-07..10
        # observed, 2026-11/12 drawn from this path.
        lock_base = (4 * 100.0 + cells.oespi_base[0][idx[0]] + cells.oespi_base[1][idx[1]]) / 6
        lock_peak = (4 * 80.0 + cells.oespi_peak[0][idx[0]] + cells.oespi_peak[1][idx[1]]) / 6
        p27 = float(indexed_price(lock_base, lock_peak, params)) + 5.0
        s3 = (10.0 + 20.0) * 49.0 + 30.0 * p27
        assert fast.loc[path, "S1"] == pytest.approx(s1)
        assert fast.loc[path, "S2"] == pytest.approx(s2)
        assert fast.loc[path, "S3"] == pytest.approx(s3)
        assert fast.loc[path, "S4_50"] == pytest.approx(0.5 * s3 + 0.5 * s1)


def test_adr019_lock_gap_carries_last_observed_value_forward() -> None:
    cells = _cells()
    draws = np.zeros((1, 3), dtype=int)
    oespi = pd.DataFrame(
        {
            "year_local": [2025] * 12 + [2026] * 8,
            "month_local": list(range(1, 13)) + list(range(1, 9)),
            "oespi_base": [100.0] * 19 + [130.0],
            "oespi_peak": 80.0,
        }
    )
    prices = fr.s3_prices(cells, draws, oespi, _params())
    # 2027 lock: 2026-07 (100), 08 (130), 09-10 gap -> 130 carried, 11-12 drawn idx 0 -> 100
    expected_base = (100 + 130 + 130 + 130 + 100 + 100) / 6
    assert prices[2027][0] == pytest.approx(
        float(indexed_price(expected_base, 80.0, _params())) + 5.0
    )


def test_st401_step4_december_regimes_and_pool_exclusion() -> None:
    dates = pd.date_range("2021-12-01", "2022-12-31", freq="D")
    regimes = pd.DataFrame(
        {"date_local": dates, "regime": np.where(dates.year == 2022, "crisis", "elevated")}
    )
    assert fr.december_regimes(regimes) == {2021: "elevated", 2022: "crisis"}
    oespi = _oespi(range(2021, 2024))
    pool = fr.build_pool(oespi, excluded_years={2022})
    assert pool[6] == [2021, 2023]


def test_q4_recommendation() -> None:
    summary = pd.DataFrame(
        {
            "variant": "unconditional",
            "strategy_id": ["S1", "S3"],
            "mean": [100.0, 110.0],
            "p95": [200.0, 150.0],
        }
    )
    q4 = fr.recommendation(summary)
    assert q4 == {
        "cost_min_strategy": "S1",
        "risk_averse_strategy": "S3",
        "risk_premium_eur": 10.0,
        "p95_reduction_eur": 50.0,
    }


# ----------------------------------------------------------- end to end (M6)


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, Path(REPO_ROOT, "scripts", f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def simulated(simulated_warehouse: Settings) -> Settings:
    return simulated_warehouse


def test_st001_outputs_written(simulated: Settings) -> None:
    processed = simulated.paths.data_processed
    costs = pd.read_parquet(processed / "strategy_costs_monthly.parquet")
    assert len(costs) == 5 * 12 * 6
    assert set(costs["strategy_id"]) == {"S1", "S2", "S3", "S4_30", "S4_50", "S4_70"}
    for name in (
        "strategy_annual_summary.md",
        "sensitivity_matrix.md",
        "forward_risk_summary.md",
        "s5_annual_costs.png",
        "s5_cumulative.png",
        "s5_forward_fan.png",
        "s5_risk_return.png",
    ):
        assert (simulated.paths.reports / "strategies" / name).exists(), name


def test_st502_lp050_captions_on_strategy_reports(simulated: Settings) -> None:
    from epra.report.style import LP050_CAPTION, ST502_CAPTION

    for name in ("strategy_annual_summary.md", "sensitivity_matrix.md", "forward_risk_summary.md"):
        text = (simulated.paths.reports / "strategies" / name).read_text(encoding="utf-8")
        assert ST502_CAPTION in text and LP050_CAPTION in text


def test_st303_sensitivity_grid(simulated: Settings) -> None:
    sens = pd.read_csv(simulated.paths.reports / "strategies" / "sensitivity_matrix.csv")
    assert sens["scenario"].tolist() == [
        "base",
        "premium_0",
        "premium_10",
        "flat_baseload",
        "lock_full_prior_year",
    ]
    by = sens.set_index("scenario")
    s3 = [scalar(by, name, "S3") for name in ("premium_0", "base", "premium_10")]
    assert s3[0] < s3[1] < s3[2]
    assert scalar(by, "premium_0", "S1") == pytest.approx(scalar(by, "base", "S1"))


def test_ssot_rows_tagged_and_generator_validates(
    simulated: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows = read_ssot_rows(simulated)
    by_producer = rows.groupby("produced_by")["tag"].unique()
    assert list(by_producer["strategies/retrospective.py"]) == ["CALIBRATED"]
    assert list(by_producer["strategies/forward_risk.py"]) == ["SIMULATED"]
    script = _script("generate_ssot")
    monkeypatch.setattr(script, "load_settings", lambda: simulated)
    out = tmp_path / "NUMERIC_SSOT.md"
    assert script.main(["--output", str(out), "--updated", "2026-01-01"]) == 0
    text = out.read_text(encoding="utf-8")
    assert "| wrong_strategy_cost_total |" in text and "| p95_next12m_S1 |" in text


def test_st405_forward_rerun_identical(simulated: Settings) -> None:
    first = pd.read_parquet(simulated.paths.data_processed / "forward_risk_summary.parquet")
    fr.run(simulated)
    second = pd.read_parquet(simulated.paths.data_processed / "forward_risk_summary.parquet")
    pd.testing.assert_frame_equal(first, second)
    assert math.isfinite(float(first["cvar95"].max()))


def test_sql_headline_queries_match_python(simulated: Settings) -> None:
    """ADR-020 §1: the sql/ headline queries reproduce the Python results exactly."""
    import duckdb

    processed = simulated.paths.data_processed.as_posix()
    con = duckdb.connect(str(simulated.paths.warehouse))
    con.execute(
        "create or replace table marts.fct_procurement_cost_monthly as select * from "
        f"read_parquet('{processed}/strategy_costs_monthly.parquet')"
    )
    seed = (REPO_ROOT / "dbt" / "seeds" / "dim_strategy.csv").as_posix()
    con.execute(f"create or replace table marts.dim_strategy as select * from read_csv('{seed}')")
    con.close()
    run_sql = _script("run_sql")
    sql_dir = REPO_ROOT / "sql"

    annual = pd.read_parquet(simulated.paths.data_processed / "strategy_annual_summary.parquet")
    q1 = run_sql.run_file(sql_dir / "q1_annual_strategy_cost_matrix.sql", simulated)
    merged = annual.merge(q1, on=["year", "strategy_id"], suffixes=("_py", "_sql"))
    assert len(merged) == len(annual) == 30
    for col in ("cost_eur", "unit_cost_eur_mwh", "delta_vs_min_eur", "rank"):
        np.testing.assert_allclose(merged[f"{col}_py"], merged[f"{col}_sql"], rtol=1e-9)

    wrong = run_sql.run_file(sql_dir / "q1_wrong_strategy_cost.sql", simulated)
    np.testing.assert_allclose(
        wrong["wrong_strategy_cost_eur"].to_numpy(),
        wrong_strategy_cost(annual).to_numpy(),
        rtol=1e-9,
    )

    forward = pd.read_parquet(simulated.paths.data_processed / "forward_risk_summary.parquet")
    q3 = run_sql.run_file(sql_dir / "q3_forward_risk_p95_cvar95.sql", simulated)
    merged = forward.merge(q3, on=["variant", "strategy_id"], suffixes=("_py", "_sql"))
    assert len(merged) == len(forward)
    for col in ("mean", "p5", "p50", "p95", "cvar95"):
        np.testing.assert_allclose(merged[f"{col}_py"], merged[f"{col}_sql"], rtol=1e-9)
