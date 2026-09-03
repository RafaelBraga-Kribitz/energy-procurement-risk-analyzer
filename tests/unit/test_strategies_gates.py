"""T6.10 operator gates: Makefile, ST-405, dirty-tree golden, CLI on tmp.

Implements: ST-405, ST-601, ST-603, EN-050, D-03, D-19.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

from epra.common.config import REPO_ROOT, Settings, load_strategy_config
from epra.common.db import connect, warehouse_path
from epra.report.ssot import assemble
from epra.strategies.align import AlignedVolumes, processed_dir
from epra.strategies.annual import KNOWN_REPORTS, strategies_dir
from epra.strategies.calibration import Anchors
from epra.strategies.forward_risk import build_cost_cells, simulate, summarize
from epra.strategies.forward_risk import main as forward_main
from epra.strategies.forward_risk import run as forward_run
from epra.strategies.retrospective import main as retro_main
from epra.strategies.retrospective import run as retro_run

_ANCHORS = Anchors(p_ref_base=50.0, p_ref_peak=70.0, oespi_base_ref=100.0, oespi_peak_ref=100.0)


def _h(
    ts: str,
    year: int,
    month: int,
    day: int,
    hour_local: int,
    load: float,
    price: float,
) -> dict[str, object]:
    return {
        "ts_utc": pd.Timestamp(ts, tz="UTC"),
        "load_mwh": load,
        "price_at_eur_mwh": price,
        "year_local": year,
        "month_local": month,
        "date_local": date(year, month, day),
        "hour_local": hour_local,
        "is_weekend": False,
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


def _load_golden_script() -> ModuleType:
    path = REPO_ROOT / "scripts" / "generate_golden_metrics.py"
    spec = importlib.util.spec_from_file_location("generate_golden_metrics", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_makefile_simulate_and_ssot_are_clis_not_dbt() -> None:
    text = Path("Makefile").read_text(encoding="utf-8")
    sim = text[text.index("simulate:") : text.index("ssot:")]
    ssot = text[text.index("ssot:") : text.index("export:")]
    assert "python -m epra.strategies.retrospective" in sim
    assert "python -m epra.strategies.forward_risk" in sim
    assert "cd dbt" not in sim
    assert "not implemented" not in sim
    assert "python scripts/generate_ssot.py" in ssot
    assert "cd dbt" not in ssot
    assert "not implemented" not in ssot


def test_generate_golden_refuses_dirty_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_golden_script()
    monkeypatch.setattr(mod, "git_porcelain", lambda _cwd: " M src/epra/strategies/_golden.py\n")
    assert mod.main(["--output", str(tmp_path / "out.json"), "--cwd", str(tmp_path)]) == 1
    assert not (tmp_path / "out.json").is_file()


def test_generate_golden_writes_when_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_golden_script()
    monkeypatch.setattr(mod, "git_porcelain", lambda _cwd: "")
    dest = tmp_path / "strategy_annual_summary.json"
    assert mod.main(["--output", str(dest), "--cwd", str(tmp_path)]) == 0
    assert dest.is_file()
    assert "Not Austrian market evidence" in dest.read_text(encoding="utf-8")


def test_st405_two_simulate_calls_identical() -> None:
    horizon, pool, oespi = _toy_frames()
    cfg = _toy_cfg()
    cells = build_cost_cells(
        horizon, pool, oespi, _ANCHORS, 0.4, cfg, (2022, 12), [(2023, 1), (2023, 2)]
    )
    a = summarize(simulate(cells, 42, 20))
    b = summarize(simulate(cells, 42, 20))
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def _aligned_2022() -> tuple[AlignedVolumes, pd.DataFrame]:
    ts = pd.Timestamp("2022-01-03 10:00:00", tz="UTC")
    hourly = pd.DataFrame(
        {
            "ts_utc": [ts],
            "load_mwh": [10.0],
            "price_at_eur_mwh": [100.0],
            "year_local": [2022],
            "month_local": [1],
            "is_peak_hour": [True],
        }
    )
    monthly = pd.DataFrame({"year_local": [2022], "month_local": [1], "volume_mwh": [10.0]})
    oespi = pd.concat(
        [
            pd.DataFrame(
                {
                    "year_local": [y] * 12,
                    "month_local": list(range(1, 13)),
                    "oespi_base": [100.0] * 12,
                    "oespi_peak": [100.0] * 12,
                }
            )
            for y in (2021, 2022)
        ]
    )
    return AlignedVolumes(hourly=hourly, monthly=monthly, dropped_hours=0), oespi


def test_cli_mains_on_tmp_then_assemble(
    tmp_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect(tmp_settings, read_only=False).close()
    assert warehouse_path(tmp_settings).is_file()
    aligned, oespi = _aligned_2022()
    cfg = load_strategy_config().model_copy(update={"retrospective_years": [2022]})
    horizon, pool, fwd_oespi = _toy_frames()
    fwd_cfg = _toy_cfg()

    def _retro(settings: Settings, **_kwargs: object) -> pd.DataFrame:
        return retro_run(
            settings,
            aligned=aligned,
            monthly_oespi=oespi,
            anchors=_ANCHORS,
            w_peak=0.4,
            cfg=cfg,
            sensitivities=False,
        )

    def _fwd(settings: Settings, **_kwargs: object) -> pd.DataFrame:
        return forward_run(
            settings,
            horizon_hours=horizon,
            pool_hourly=pool,
            monthly_oespi=fwd_oespi,
            anchors=_ANCHORS,
            w_peak=0.4,
            cfg=fwd_cfg,
            data_last_month=(2022, 12),
            n_paths=20,
            dates=pd.Series(pd.to_datetime(["2021-12-15", "2022-12-15"])),
            labels=pd.Series(["calm", "calm"]),
        )

    monkeypatch.setattr("epra.common.config.load_settings", lambda: tmp_settings)
    monkeypatch.setattr("epra.strategies.retrospective.run", _retro)
    monkeypatch.setattr("epra.strategies.forward_risk.run", _fwd)
    out = strategies_dir(tmp_settings)
    out.mkdir(parents=True, exist_ok=True)
    leftover = out / KNOWN_REPORTS[0]
    leftover.write_bytes(b"stale")
    leftover.unlink()
    assert retro_main([]) == 0
    assert forward_main([]) == 0
    assert (out / "s5_annual_costs.png").is_file()
    assert (out / "s5_forward_fan.png").is_file()
    body = assemble(tmp_settings, data_last_month="2022-01", check_complete=False)
    assert "wrong_strategy_cost_total" in body
    assert "p95_next12m_S1" in body
    assert processed_dir(tmp_settings).joinpath("ssot_inputs_strategies.parquet").is_file()


def test_stubs_only_m7_charts() -> None:
    path = REPO_ROOT / "tests" / "unit" / "test_stubs_fail_loudly.py"
    spec = importlib.util.spec_from_file_location("test_stubs_fail_loudly", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    stubs = mod.STUBS
    assert stubs
    assert all(milestone == "M7" for milestone, _func, _args in stubs)
