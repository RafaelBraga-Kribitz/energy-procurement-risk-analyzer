"""HTML dashboard twin (ADR-022): deterministic, self-contained, numbers = sources.

The synthetic-export tests run everywhere (CI ``test`` job has no exports); the
``exports/`` tests run wherever ``make export`` has produced CSVs (locally and in
CI's fixture pipeline) and tie the twin's chart values to the SSOT.

Implements: ADR-022, RP-401..RP-405, RP-703, A-4, A-6; checks ADR-018 banner.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

from epra.common.config import REPO_ROOT, load_settings, resolve_repo_path
from epra.report import dashboard_pages as dp
from epra.report import html_dashboard as hd
from epra.report.format import format_eur, format_eur_millions
from epra.report.style import STRATEGY_COLORS, STRATEGY_LABELS, strategy_colors

IDS = list(STRATEGY_LABELS)
YEARS = (2021, 2022)


def _contract() -> dict[str, list[str]]:
    spec = importlib.util.spec_from_file_location(
        "export_marts", REPO_ROOT / "scripts" / "export_marts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_marts"] = module
    spec.loader.exec_module(module)
    contract: dict[str, list[str]] = module.EXPORT_CONTRACT
    return contract


def _write(out: Path, name: str, rows: list[dict[str, object]]) -> None:
    frame = pd.DataFrame(rows, columns=_contract()[name])
    frame.to_csv(out / f"{name}.csv", index=False)


def synthetic_exports(out: Path, *, fixture: bool) -> dict[str, str]:
    """Tiny, internally consistent export set (test data, not results).

    Strategy ``k`` costs ``1000 * (k + 1) * month`` EUR per month, so every
    aggregate the twin draws has a closed form the SSOT rows below restate.
    """
    out.mkdir(parents=True, exist_ok=True)
    months = [(y, m) for y in YEARS for m in range(1, 13)]
    cost = [
        {
            "year_local": y,
            "month_local": m,
            "strategy_id": sid,
            "volume_mwh": 100.0,
            "cost_eur": 1000.0 * (k + 1) * m,
            "unit_cost_eur_mwh": 10.0 * (k + 1) * m,
        }
        for y, m in months
        for k, sid in enumerate(IDS)
    ]
    _write(out, "procurement_cost_monthly", cost)
    annual = [
        {
            "year": y,
            "strategy_id": sid,
            "volume_mwh": 1200.0,
            "cost_eur": 78000.0 * (k + 1),
            "unit_cost_eur_mwh": 65.0 * (k + 1),
            "delta_vs_min_eur": 78000.0 * k,
            "rank": k + 1,
        }
        for y in YEARS
        for k, sid in enumerate(IDS)
    ]
    _write(out, "strategy_annual_summary", annual)
    stats = {"mean": 4e6, "std": 5e5, "p5": 3e6, "p50": 3.9e6, "p95": 5.5e6, "cvar95": 6e6}
    _write(
        out,
        "forward_risk_summary",
        [
            {"variant": v, "strategy_id": sid, **{k: x + 1e4 * i for k, x in stats.items()}}
            for v in ("no_crisis", "unconditional")
            for i, sid in enumerate(IDS)
        ],
    )
    _write(
        out,
        "forward_paths",
        [
            {"variant": v, "path": p, "strategy_id": sid, "cost_eur": 3e6 + 1e5 * p + 1e4 * i}
            for v in ("no_crisis", "unconditional")
            for i, sid in enumerate(IDS)
            for p in range(5)
        ],
    )
    _write(
        out,
        "price_monthly",
        [
            {
                "year_local": y,
                "month_local": m,
                "price_base_eur_mwh": 50.0 + m,
                "price_peak_eur_mwh": None if m == 2 else 60.0 + m,
                "price_offpeak_eur_mwh": 45.0,
                "n_negative_hours": m % 3,
                "oespi_base": 100.0,
                "oespi_peak": 90.0,
            }
            for y, m in months[:-3]
        ],
    )
    _write(
        out,
        "spread_monthly",
        [
            {
                "year_local": y,
                "month_local": m,
                "spread_mean_eur_mwh": m - 6.5,
                "share_at_above_de_pct": 50.0,
            }
            for y, m in months[:-3]
        ],
    )
    _write(
        out,
        "data_quality_monthly",
        [
            {
                "year_local": y,
                "month_local": m,
                "expected_hours": 720,
                "priced_hours_at": 720 - (m == 5),
                "priced_hours_delu": 720,
                "load_hours": 720,
                "weather_days": 30,
                "days_in_month": 30,
                "coverage_at_pct": 100.0 - (m == 5) / 7.2,
                "n_dst_days": int(m in (3, 10)),
                "n_hours_from_pt15m": 720 if y == 2022 else 0,
                "resolution": "PT60M",
                "n_negative_hours": 0,
                "has_oespi": m != 12,
            }
            for y, m in months
        ],
    )
    _write(
        out,
        "dim_strategy",
        [
            {
                "strategy_id": sid,
                "strategy_name": sid,
                "strategy_label": STRATEGY_LABELS[sid],
                "sort_order": i + 1,
                "color_hex": STRATEGY_COLORS[sid],
                "description": "test",
            }
            for i, sid in enumerate(IDS)
        ],
    )
    ssot = {
        "wrong_strategy_cost_total": "780000.0",
        "best_strategy_5yr": "S1",
        "forward_n_paths": "2000",
        "q4_cost_min_strategy": "S1",
        "q4_risk_averse_strategy": "S1",
        "q4_risk_premium_eur": "0.0",
        "q4_p95_reduction_eur": "0.0",
        "data_last_month": "2022-09",
        **{f"cost5yr_{sid}": str(156000.0 * (k + 1)) for k, sid in enumerate(IDS)},
        **{f"p95_next12m_{sid}": str(5.5e6 + 1e4 * k) for k, sid in enumerate(IDS)},
        **{f"mean_next12m_{sid}": str(4e6 + 1e4 * k) for k, sid in enumerate(IDS)},
    }
    pd.DataFrame(
        [
            {"key": k, "value": v, "unit": "EUR", "tag": "CALIBRATED", "produced_by": "test"}
            for k, v in ssot.items()
        ]
    ).to_csv(out / "ssot.csv", index=False)
    pd.DataFrame(
        [{"is_fixture": fixture, "data_last_month": "2022-09", "generated_on": "2022-10-03"}]
    ).to_csv(out / "provenance.csv", index=False)
    return ssot


def _numbers_in_order(html: str, key: str) -> str:
    match = re.search(rf'data-ssot-key="{key}" data-value="([^"]*)"', html)
    assert match, key
    return match.group(1)


def test_build_is_deterministic_and_self_contained(tmp_path: Path) -> None:
    ssot = synthetic_exports(tmp_path / "exports", fixture=True)
    first = hd.build(tmp_path / "exports", tmp_path / "a.html").read_bytes()
    second = hd.build(tmp_path / "exports", tmp_path / "b.html").read_bytes()
    assert first == second
    html = first.decode("utf-8")
    assert not re.search(r"""(src|href)\s*=\s*["']?\s*(https?:)?//""", html, re.I)
    assert "<link" not in html and "@import" not in html and "url(" not in html
    assert dp.FIXTURE_BANNER in html and "<title>FIXTURE" in html
    for page in dp.PAGES:
        assert f'id="panel-{page.page_id}"' in html
        assert hd.esc(dp.subtitle(page, 2000)) in html
        assert hd.esc(page.epistemic) in html
    assert html.count(hd.esc(dp.SOURCE_NOTE)) == len(dp.PAGES)
    total = float(ssot["wrong_strategy_cost_total"])
    assert _numbers_in_order(html, "wrong_strategy_cost_total") == ssot["wrong_strategy_cost_total"]
    assert format_eur_millions(total) in html


def test_real_data_has_no_banner(tmp_path: Path) -> None:
    synthetic_exports(tmp_path / "exports", fixture=False)
    html = hd.render_html(hd.load_exports(tmp_path / "exports"))
    assert dp.FIXTURE_BANNER not in html and "<title>EPRA" in html


def test_payload_values_follow_the_exports(tmp_path: Path) -> None:
    synthetic_exports(tmp_path / "exports", fixture=True)
    ex = hd.load_exports(tmp_path / "exports")
    wrong = hd.wrong_strategy_by_year(ex)
    # 78,000 EUR per strategy step per year; S4_70 (6th) minus S1 (1st) = 5 steps.
    assert [r["gap"] for r in wrong] == [390000.0, 390000.0]
    assert sum(r["gap"] for r in wrong) == 780000.0
    assert {r["worst"] for r in wrong} == {"S4_70"} and {r["best"] for r in wrong} == {"S1"}
    matrix = hd.cost_matrix(ex)
    assert matrix["total"]["S3"]["cost"] == 156000.0 * 3
    assert matrix["rank"]["S1"] == [1, 1]
    market = hd.market_data(ex)
    assert market["peak"][1] is None and market["neg_partial"] == [False, True]
    risk = hd.risk_data(ex)
    assert set(risk) == {"no_crisis", "unconditional"}
    assert sum(risk["unconditional"]["hist"]["S1"]) == 5
    dq = hd.dq_data(ex)
    assert dq["axis_min"] == 99
    html = hd.render_html(ex)
    assert "Months without ÖSPI" in html and "2022-05" in html  # gap table lists the short month


def test_runner_up_margin_and_formatting() -> None:
    ssot = {"cost5yr_S1": "100.0", "cost5yr_S3": "90.0", "cost5yr_S2": "95.5"}
    assert hd.runner_up(ssot, "cost5yr_", ["S1", "S2", "S3"]) == ("S2", 5.5)
    assert hd.runner_up({"cost5yr_S1": "1"}, "cost5yr_", ["S1"]) == ("", 0.0)
    assert dp.german_int(2000) == "2.000"
    assert "2.000 simulierten" in dp.subtitle(dp.PAGES[3], 2000)
    assert format_eur(26950.56) == "€26,951"


def test_dark_and_light_strategy_colours() -> None:
    assert strategy_colors("light") == STRATEGY_COLORS
    dark = strategy_colors("dark")
    assert set(dark) == set(STRATEGY_COLORS) and dark != STRATEGY_COLORS
    css = hd.css_tokens()
    assert "prefers-color-scheme:dark" in css and f"--s-S1:{dark['S1']}" in css


def test_main_without_exports_fails_loudly(tmp_path: Path) -> None:
    assert hd.main(["--exports", str(tmp_path), "--out", str(tmp_path / "x.html")]) == 1
    synthetic_exports(tmp_path / "e", fixture=True)
    assert hd.main(["--exports", str(tmp_path / "e"), "--out", str(tmp_path / "x.html")]) == 0
    assert (tmp_path / "x.html").exists()


# ------------------------------------------------------------- on the real `make export` output

EXPORTS = resolve_repo_path(load_settings().paths.exports)
needs_exports = pytest.mark.skipif(
    not (EXPORTS / "ssot.csv").exists(), reason="run `make export` first"
)


@needs_exports
def test_twin_numbers_equal_the_ssot() -> None:
    """Bars, matrix totals and cards reconcile with reports/NUMERIC_SSOT.md (A-6)."""
    ex = hd.load_exports(EXPORTS)
    s = ex.ssot
    wrong = hd.wrong_strategy_by_year(ex)
    for row in wrong:
        assert row["gap"] == pytest.approx(float(s[f"wrong_strategy_cost_{row['year']}"]), abs=0.01)
    assert sum(r["gap"] for r in wrong) == pytest.approx(
        float(s["wrong_strategy_cost_total"]), abs=0.05
    )
    totals = hd.cost_matrix(ex)["total"]
    for sid, t in totals.items():
        assert t["cost"] == pytest.approx(float(s[f"cost5yr_{sid}"]), abs=0.05)
    assert min(totals, key=lambda sid: totals[sid]["cost"]) == s["best_strategy_5yr"]
    html = hd.render_html(ex)
    for key in (
        "wrong_strategy_cost_total",
        "p95_next12m_S1",
        "p95_next12m_S3",
        "q4_risk_premium_eur",
        "q4_p95_reduction_eur",
    ):
        assert _numbers_in_order(html, key) == s[key]
    assert format_eur_millions(float(s["wrong_strategy_cost_total"])) in html
    assert (dp.FIXTURE_BANNER in html) == hd.is_fixture(ex)
