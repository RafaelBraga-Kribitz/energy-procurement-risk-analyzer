"""T6.09 GV-303 checker (ADR-016 half-up, whitelist, mutation).

Implements: GV-303, ADR-016, D-17, D-18.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from epra.common.config import REPO_ROOT, Settings
from epra.report.ssot import assemble
from epra.report.ssot_check import check, parse_whitelist, round_half_up
from epra.strategies.align import STRATEGY_IDS


def _row(
    key: str,
    value: object,
    tag: str = "CALIBRATED",
    unit: str = "EUR",
) -> dict[str, object]:
    return {
        "key": key,
        "value": value,
        "unit": unit,
        "tag": tag,
        "produced_by": "test",
    }


def _complete_rows(*, p_ref: float = 1.25) -> list[dict[str, object]]:
    rows = [
        _row("p_ref_base", p_ref, unit="EUR/MWh"),
        _row("p_ref_peak", 50.0, unit="EUR/MWh"),
        _row("oespi_base_ref", 70.0, unit="index"),
        _row("oespi_peak_ref", 80.0, unit="index"),
        _row("consumer_peak_share", 0.48, unit="share"),
        _row("garch_persistence", 0.9, unit="1", tag="VERIFIED"),
        _row("annual_mean_price_2022", 200.0, unit="EUR/MWh", tag="VERIFIED"),
        _row("neg_hours_2022", 10.0, unit="hours", tag="VERIFIED"),
        _row("spread_mean_2022", 1.0, unit="EUR/MWh", tag="VERIFIED"),
        _row("wrong_strategy_cost_2022", 20.0),
        _row("wrong_strategy_cost_total", 20.0),
    ]
    for sid in STRATEGY_IDS:
        rows.append(_row(f"cost_{sid}_2022", 80.0 if sid == "S3" else 100.0))
        rows.append(_row(f"p95_next12m_{sid}", 1.0, tag="SIMULATED"))
        rows.append(_row(f"cvar95_next12m_{sid}", 2.0, tag="SIMULATED"))
    return rows


def _write_ssot(tmp_settings: Settings, p_ref: float = 1.25) -> Path:
    assemble(
        tmp_settings,
        frames=[pd.DataFrame(_complete_rows(p_ref=p_ref))],
        data_last_month="2024-01",
        mtimes=(0.0,),
        check_complete=True,
    )
    return tmp_settings.paths.reports / "NUMERIC_SSOT.md"


def _check_docs(
    tmp_path: Path,
    ssot: Path,
    body: str,
    *,
    gv302: bool = True,
) -> int:
    readme = tmp_path / "README.md"
    readme.write_text(body, encoding="utf-8")
    return check(
        repo_root=REPO_ROOT,
        readme_path=readme,
        exec_path=tmp_path / "no-exec.md",
        ssot_path=ssot,
        check_gv302=gv302,
    )


def test_half_up_not_banker() -> None:
    assert round(1.25, 1) == 1.2
    assert round_half_up(Decimal("1.25"), 1) == Decimal("1.3")


def test_whitelist_every_line_has_reason_and_includes_2022() -> None:
    path = REPO_ROOT / "scripts" / "ssot_whitelist.txt"
    mapping = parse_whitelist(path)
    assert "2022" in mapping
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert "#" in stripped
        token, reason = stripped.split("#", 1)
        assert token.strip()
        assert reason.strip()


def test_missing_ssot_current_readme_exits_0() -> None:
    assert not (REPO_ROOT / "reports" / "NUMERIC_SSOT.md").is_file()
    assert check(repo_root=REPO_ROOT, check_gv302=False) == 0


def test_year_2022_not_a_result_euro(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("Window 2021-2025 includes 2022 for StyriaMetal.\n", encoding="utf-8")
    assert (
        check(
            repo_root=REPO_ROOT,
            readme_path=readme,
            exec_path=tmp_path / "missing_exec.md",
            ssot_path=tmp_path / "missing_ssot.md",
            check_gv302=False,
        )
        == 0
    )


def test_whitelisted_2022_eur_does_not_false_positive(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("In 2022 EUR terms the window is calendar years.\n", encoding="utf-8")
    assert (
        check(
            repo_root=REPO_ROOT,
            readme_path=readme,
            exec_path=tmp_path / "no-exec.md",
            ssot_path=tmp_path / "no-ssot.md",
            check_gv302=False,
        )
        == 0
    )


def test_half_up_literal_matches_ssot(tmp_settings: Settings, tmp_path: Path) -> None:
    ssot = _write_ssot(tmp_settings, p_ref=1.25)
    assert _check_docs(tmp_path, ssot, "Anchor is 1.3 EUR/MWh (CALIBRATED).\n") == 0


def test_banker_literal_does_not_match(tmp_settings: Settings, tmp_path: Path) -> None:
    ssot = _write_ssot(tmp_settings, p_ref=1.25)
    assert _check_docs(tmp_path, ssot, "Anchor is 1.2 EUR/MWh (banker trap).\n") == 1


def test_mutation_digit_next_to_unit_fails(tmp_settings: Settings, tmp_path: Path) -> None:
    ssot = _write_ssot(tmp_settings, p_ref=1.25)
    assert _check_docs(tmp_path, ssot, "Anchor is 1.3 EUR/MWh.\n") == 0
    assert _check_docs(tmp_path, ssot, "Anchor is 1.4 EUR/MWh.\n") == 1


def test_unmatched_token_names_literal(
    tmp_settings: Settings, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ssot = _write_ssot(tmp_settings, p_ref=1.25)
    assert _check_docs(tmp_path, ssot, "Wrong headline 99.0 EUR.\n") == 1
    err = capsys.readouterr().err
    assert "99.0 EUR" in err
    assert "cost_S" in err or "cvar95" in err


def test_ci_job_ssot_check_present() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "ssot-check:" in workflow
    assert "python scripts/check_ssot_consistency.py" in workflow
    job = workflow.lower().split("ssot-check:")[1][:400]
    assert "required" not in job


def test_checker_source_has_no_builtin_round() -> None:
    text = (
        Path(__file__).resolve().parents[2] / "src" / "epra" / "report" / "ssot_check.py"
    ).read_text(encoding="utf-8")
    assert "ROUND_HALF_UP" in text
    assert "round(" not in text.replace("round_half_up", "")
