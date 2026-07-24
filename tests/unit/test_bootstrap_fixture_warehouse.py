"""D-04 deterministic fixture/stand-in generator tests.

Covers the --force guard (03_MODULES.md: never overwrite a populated
data/raw or data/manual/oespi_monthly.csv without --force), the
--processed-only local-dev mode (D-06: never touches data/raw/data/manual),
determinism (same seed -> identical data columns across two runs), and
2022-2024 window/DST/crisis-month coverage of the default CI window.

Every test targets a `tmp_path`-redirected `--data-root` -- this suite never
touches the repo's real `data/raw`, `data/manual`, or `data/processed` trees
(mirrors `tests/unit/test_scripts.py`'s subprocess-driven CLI test style).

Implements: SG-06 (ADR-010), D-03, D-04, D-05, D-06.
"""

from __future__ import annotations

import glob
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
SCRIPT = "bootstrap_fixture_warehouse.py"

_ALL_STRATEGY_IDS = {"S1", "S2", "S3", "S4_30", "S4_50", "S4_70"}


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


def _read_dataset(data_root: Path, dataset: str, subdir: str) -> pd.DataFrame:
    pattern = str(data_root / subdir / dataset / "**" / "*.parquet")
    files = sorted(glob.glob(pattern, recursive=True))
    assert files, f"no parquet files written for {dataset} under {data_root / subdir}"
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def _dummy_raw_price_file(data_root: Path) -> Path:
    return data_root / "raw" / "entsoe_prices_at" / "2022" / "entsoe_prices_at_2022-01.parquet"


# --------------------------------------------------------------------- guard


def test_force_guard_refuses_populated_raw_without_force(tmp_path: Path) -> None:
    """Default run against a populated data/raw returns 1 and leaves the
    pre-existing raw file untouched (guard, 03_MODULES.md)."""
    dummy = _dummy_raw_price_file(tmp_path / "data")
    dummy.parent.mkdir(parents=True)
    dummy.write_bytes(b"not-a-real-parquet-file")

    result = _run(
        "--data-root",
        str(tmp_path / "data"),
        "--window-start",
        "2022-01-01",
        "--window-end",
        "2022-02-28",
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert dummy.read_bytes() == b"not-a-real-parquet-file", (
        "guard must leave the pre-existing raw file untouched"
    )
    assert not (tmp_path / "data" / "processed").exists(), (
        "guard failure must write nothing at all, including data/processed"
    )


def test_force_guard_refuses_populated_manual_oespi_without_force(tmp_path: Path) -> None:
    """The same guard also protects the real reconciled data/manual/oespi_monthly.csv
    (both data/raw and data/manual hold irreplaceable real data)."""
    manual_csv = tmp_path / "data" / "manual" / "oespi_monthly.csv"
    manual_csv.parent.mkdir(parents=True)
    manual_csv.write_text(
        "month,oespi_base,oespi_peak,source_url,retrieved_at\n2019-01,100.0,95.0,x,y\n"
    )

    result = _run(
        "--data-root",
        str(tmp_path / "data"),
        "--window-start",
        "2022-01-01",
        "--window-end",
        "2022-02-28",
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "oespi_base" in manual_csv.read_text()


def test_force_guard_proceeds_with_force(tmp_path: Path) -> None:
    """--force overrides the guard and proceeds to write raw + processed."""
    dummy = _dummy_raw_price_file(tmp_path / "data")
    dummy.parent.mkdir(parents=True)
    dummy.write_bytes(b"not-a-real-parquet-file")

    result = _run(
        "--data-root",
        str(tmp_path / "data"),
        "--force",
        "--window-start",
        "2022-01-01",
        "--window-end",
        "2022-02-28",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert dummy.read_bytes() != b"not-a-real-parquet-file"
    assert any((tmp_path / "data" / "processed").rglob("*.parquet"))


def test_processed_only_never_requires_force_and_never_touches_raw(tmp_path: Path) -> None:
    """D-06: --processed-only writes only data/processed, regardless of
    data/raw's state, and never requires --force."""
    dummy = _dummy_raw_price_file(tmp_path / "data")
    dummy.parent.mkdir(parents=True)
    dummy.write_bytes(b"real-looking-raw-data")
    manual_csv = tmp_path / "data" / "manual" / "oespi_monthly.csv"
    manual_csv.parent.mkdir(parents=True)
    manual_csv.write_text("real-oespi-data\n")

    result = _run(
        "--data-root",
        str(tmp_path / "data"),
        "--processed-only",
        "--window-start",
        "2022-01-01",
        "--window-end",
        "2022-02-28",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert dummy.read_bytes() == b"real-looking-raw-data"
    assert manual_csv.read_text() == "real-oespi-data\n"
    processed_root = tmp_path / "data" / "processed"
    assert any(processed_root.rglob("*.parquet"))

    consumer = _read_dataset(tmp_path / "data", "consumer_load_hourly", "processed")
    assert not consumer["load_mwh"].isna().any()
    proc = _read_dataset(tmp_path / "data", "procurement_cost_monthly", "processed")
    assert set(proc["strategy_id"].unique()) == _ALL_STRATEGY_IDS


# --------------------------------------------------------------- determinism


def test_determinism_same_seed_identical_data_across_two_runs(tmp_path: Path) -> None:
    """Two independent runs with the same seed and window produce identical
    data columns for every written dataset (raw + processed + calendar +
    oespi CSV). ``ingested_at_utc`` is the one column allowed to differ
    (wall-clock provenance -- same seam ``_io.write_month``'s own
    idempotency tests document); ``request_hash`` is itself deterministic
    (derived from dataset/month, not the clock), so it is asserted equal
    along with every other column."""
    common = ["--window-start", "2022-01-01", "--window-end", "2022-02-28"]
    root1, root2 = tmp_path / "run1" / "data", tmp_path / "run2" / "data"

    r1 = _run("--data-root", str(root1), *common)
    r2 = _run("--data-root", str(root2), *common)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert r2.returncode == 0, r2.stdout + r2.stderr

    for dataset, subdir in [
        ("entsoe_prices_at", "raw"),
        ("entsoe_prices_delu", "raw"),
        ("entsoe_load_at", "raw"),
        ("entsoe_gen_at", "raw"),
        ("geosphere_graz_daily", "raw"),
        ("consumer_load_hourly", "processed"),
        ("procurement_cost_monthly", "processed"),
    ]:
        f1 = _read_dataset(root1, dataset, subdir).drop(columns=["ingested_at_utc"])
        f2 = _read_dataset(root2, dataset, subdir).drop(columns=["ingested_at_utc"])
        pd.testing.assert_frame_equal(f1, f2)

    cal1 = pd.read_parquet(root1 / "raw" / "calendar" / "calendar.parquet")
    cal2 = pd.read_parquet(root2 / "raw" / "calendar" / "calendar.parquet")
    pd.testing.assert_frame_equal(cal1, cal2)

    oespi1 = (root1 / "manual" / "oespi_monthly.csv").read_bytes()
    oespi2 = (root2 / "manual" / "oespi_monthly.csv").read_bytes()
    assert oespi1 == oespi2, "oespi_monthly.csv has no wall-clock column -- must be byte-identical"


# ----------------------------------------------------------- window/coverage


def test_default_window_covers_2022_2024_with_dst_days_and_crisis_month(tmp_path: Path) -> None:
    """The default (no --window-* override) window is contiguous
    2022-01-01..2024-12-31, includes both 2024 DST transition days with the
    correct 23/25 local-hour counts, and includes the 2022-08 crisis month
    (D-03)."""
    result = _run("--data-root", str(tmp_path / "data"))
    assert result.returncode == 0, result.stdout + result.stderr

    cal = pd.read_parquet(tmp_path / "data" / "raw" / "calendar" / "calendar.parquet")
    date_local = pd.to_datetime(cal["date_local"])

    assert date_local.min().date().isoformat() == "2022-01-01"
    assert date_local.max().date().isoformat() == "2024-12-31"
    assert date_local.dt.date.nunique() == 1096  # 365 + 365 + 366 (2024 leap year)

    assert (date_local.dt.date == pd.Timestamp("2024-03-31").date()).sum() == 23
    assert (date_local.dt.date == pd.Timestamp("2024-10-27").date()).sum() == 25

    all_dates = set(date_local.dt.date.unique())
    assert any(d.year == 2022 and d.month == 8 for d in all_dates), (
        "2022-08 crisis month must be present in the synthesized window"
    )

    prices = _read_dataset(tmp_path / "data", "entsoe_prices_at", "raw")
    assert prices["price_eur_mwh"].between(-500, 5000).all()
    prices_delu = _read_dataset(tmp_path / "data", "entsoe_prices_delu", "raw")
    assert set(prices_delu["zone"].unique()) == {"DE_LU"}
    load = _read_dataset(tmp_path / "data", "entsoe_load_at", "raw")
    assert load["load_mw"].between(3000, 13000).all()
    gen = _read_dataset(tmp_path / "data", "entsoe_gen_at", "raw")
    assert set(gen["kind"].unique()) == {"aggregated"}
    weather = _read_dataset(tmp_path / "data", "geosphere_graz_daily", "raw")
    assert weather["tl_mittel_c"].between(-30, 42).all()

    oespi = pd.read_csv(tmp_path / "data" / "manual" / "oespi_monthly.csv")
    assert (oespi["oespi_base"] > 0).all()
    assert len(oespi) == 36

    consumer = _read_dataset(tmp_path / "data", "consumer_load_hourly", "processed")
    assert consumer["load_mwh"].gt(0).all()

    proc = _read_dataset(tmp_path / "data", "procurement_cost_monthly", "processed")
    assert set(proc["strategy_id"].unique()) == _ALL_STRATEGY_IDS
    months = proc[["year_local", "month_local"]].drop_duplicates()
    assert len(months) == 36  # Jan 2022 .. Dec 2024, no gaps (DM-050)
    for strategy_id in _ALL_STRATEGY_IDS:
        assert (proc["strategy_id"] == strategy_id).sum() == 36


def test_processed_only_discovers_real_local_window_from_calendar(tmp_path: Path) -> None:
    """D-06: without an explicit --window-* override, --processed-only reads
    the local ingestion window from an existing data/raw/calendar/calendar.parquet
    spine (mirrors how a real local checkout with real ingested data already
    has a calendar.parquet spanning its real 2019->latest window)."""
    seed_result = _run(
        "--data-root",
        str(tmp_path / "seed" / "data"),
        "--window-start",
        "2023-01-01",
        "--window-end",
        "2023-03-31",
    )
    assert seed_result.returncode == 0, seed_result.stdout + seed_result.stderr

    target_root = tmp_path / "data"
    target_root.mkdir()
    (target_root / "raw" / "calendar").mkdir(parents=True)
    (tmp_path / "seed" / "data" / "raw" / "calendar" / "calendar.parquet").rename(
        target_root / "raw" / "calendar" / "calendar.parquet"
    )

    result = _run("--data-root", str(target_root), "--processed-only")
    assert result.returncode == 0, result.stdout + result.stderr

    proc = _read_dataset(target_root, "procurement_cost_monthly", "processed")
    assert set(proc["year_local"].unique()) == {2023}
    assert set(proc["month_local"].unique()) == {1, 2, 3}


@pytest.mark.parametrize("flag", ["--data-root"])
def test_missing_data_root_argument_value_is_a_usage_error(flag: str) -> None:
    """Sanity: --data-root requires a value (argparse usage error, exit 2)."""
    result = _run(flag)
    assert result.returncode == 2
