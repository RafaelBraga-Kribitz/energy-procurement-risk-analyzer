"""Tests for the implemented governance scripts (EN-003 token guard, ING-101)."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

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
    fake = "securityToken=" + "abc123def456ghi"  # built at runtime: never a literal here
    bad.write_text(f'url = "https://web-api.tp.entsoe.eu/api?{fake}"\n')
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


# ---------------------------------------------------------------------------
# oespi_reconcile.reconcile() in-process (ING-101) -- the subprocess tests above
# exercise the CLI; these cover reconcile() itself (month-set mismatch,
# whitespace tolerance, provenance columns) and the repo-anchored default --dir.
# ---------------------------------------------------------------------------


def _load_reconcile_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("oespi_reconcile", SCRIPTS / "oespi_reconcile.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entries(tmp_path: Path, rows1: str, rows2: str) -> tuple[Path, Path, Path]:
    entry1, entry2 = tmp_path / "e1.csv", tmp_path / "e2.csv"
    entry1.write_text(OESPI_HEADER + rows1, encoding="utf-8")
    entry2.write_text(OESPI_HEADER + rows2, encoding="utf-8")
    return entry1, entry2, tmp_path / "oespi_monthly.csv"


def test_reconcile_writes_entry1_verbatim_when_values_agree(tmp_path: Path) -> None:
    rec = _load_reconcile_module()
    rows1 = "2019-01,104.06,98.32,https://a.test,2026-07-19\n2019-02,105.00,99.00,https://a.test,2026-07-19\n"
    # Same values; whitespace and provenance differ -- provenance is not a transcribed value.
    rows2 = "2019-01, 104.06 ,98.32,https://a.test,2026-07-20\n2019-02,105.00,99.00,https://a.test,2026-07-20\n"
    entry1, entry2, out = _entries(tmp_path, rows1, rows2)

    assert rec.reconcile(entry1, entry2, out) == 0
    assert out.read_text(encoding="utf-8") == OESPI_HEADER + rows1


def test_reconcile_reports_months_present_in_only_one_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rec = _load_reconcile_module()
    entry1, entry2, out = _entries(
        tmp_path,
        "2019-01,104.06,98.32,https://a.test,2026-07-19\n2019-02,105.00,99.00,https://a.test,2026-07-19\n",
        "2019-01,104.06,98.32,https://a.test,2026-07-19\n",
    )

    assert rec.reconcile(entry1, entry2, out) == 1
    assert "2019-02: present in only one entry file" in capsys.readouterr().out
    assert not out.exists()


def test_reconcile_lists_every_value_mismatch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rec = _load_reconcile_module()
    entry1, entry2, out = _entries(
        tmp_path,
        "2019-01,104.06,98.32,https://a.test,2026-07-19\n",
        "2019-01,104.60,98.23,https://a.test,2026-07-19\n",
    )

    assert rec.reconcile(entry1, entry2, out) == 1
    stdout = capsys.readouterr().out
    assert "2 mismatch(es)" in stdout
    assert "oespi_base entry1='104.06' entry2='104.60'" in stdout
    assert "oespi_peak entry1='98.32' entry2='98.23'" in stdout


def test_reconcile_rejects_schema_drift(tmp_path: Path) -> None:
    rec = _load_reconcile_module()
    entry1 = tmp_path / "e1.csv"
    entry1.write_text("month,base,peak\n2019-01,1,2\n", encoding="utf-8")
    entry2 = tmp_path / "e2.csv"
    entry2.write_text(OESPI_HEADER + "2019-01,1,2,https://a.test,2026-07-19\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="ING-100 schema"):
        rec.reconcile(entry1, entry2, tmp_path / "out.csv")


def test_reconcile_default_dir_is_repo_anchored() -> None:
    assert _load_reconcile_module().DEFAULT_DIR == REPO_ROOT / "data" / "manual"
