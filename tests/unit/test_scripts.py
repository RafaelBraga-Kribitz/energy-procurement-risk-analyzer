"""Tests for the implemented governance scripts (EN-003 token guard, ING-101)."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

OESPI_HEADER = "month,oespi_base,oespi_peak,source_url,retrieved_at\n"


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


def test_token_guard_flags_literal(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('url = "https://web-api.tp.entsoe.eu/api?securityToken=abc123def456ghi"\n')
    result = _run("check_no_token_in_code.py", str(bad))
    assert result.returncode == 1
    assert "bad.py:1" in result.stdout


def test_token_guard_allows_env_placeholder(tmp_path: Path) -> None:
    ok = tmp_path / "ok.py"
    ok.write_text(
        'url = f"...securityToken={token}"\nother = "securityToken=${ENTSOE_API_TOKEN}"\n'
    )
    result = _run("check_no_token_in_code.py", str(ok))
    assert result.returncode == 0


def test_oespi_reconcile_accepts_matching_entries(tmp_path: Path) -> None:
    row = "2019-01,104.06,98.32,https://example.test,2026-07-19\n"
    (tmp_path / "oespi_monthly_entry1.csv").write_text(OESPI_HEADER + row)
    (tmp_path / "oespi_monthly_entry2.csv").write_text(OESPI_HEADER + row)
    result = _run("oespi_reconcile.py", "--dir", str(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "oespi_monthly.csv").read_text() == OESPI_HEADER + row


def test_oespi_reconcile_rejects_mismatch(tmp_path: Path) -> None:
    (tmp_path / "oespi_monthly_entry1.csv").write_text(
        OESPI_HEADER + "2019-01,104.06,98.32,https://example.test,2026-07-19\n"
    )
    (tmp_path / "oespi_monthly_entry2.csv").write_text(
        OESPI_HEADER + "2019-01,104.60,98.32,https://example.test,2026-07-19\n"
    )
    result = _run("oespi_reconcile.py", "--dir", str(tmp_path))
    assert result.returncode == 1
    assert "oespi_base" in result.stdout
    assert not (tmp_path / "oespi_monthly.csv").exists()


def test_oespi_reconcile_requires_both_entries(tmp_path: Path) -> None:
    result = _run("oespi_reconcile.py", "--dir", str(tmp_path))
    assert result.returncode == 1
    assert "not found" in result.stdout
