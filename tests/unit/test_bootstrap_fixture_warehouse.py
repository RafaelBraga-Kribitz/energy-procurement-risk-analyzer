"""Deterministic fixture/stand-in generator tests (ADR-016).

Covers the --force guard (never overwrite a populated data/raw without
--force), the invariant that data/manual/oespi_monthly.csv is NEVER written
(not even with --force), the --processed-only local-dev mode (never touches
data/raw/data/manual), the exact processed output contracts (SPEC-03 LP-003
single file ``consumer_load_hourly.parquet``; SPEC-05 ST-001 single file
``strategy_costs_monthly.parquet``), determinism (same seed -> identical data
columns across two runs), and 2022-2024 window/DST/crisis-month coverage.

Every test targets a `tmp_path`-redirected `--data-root` -- this suite never
touches the repo's real `data/raw`, `data/manual`, or `data/processed` trees
(mirrors `tests/unit/test_scripts.py`'s subprocess-driven CLI test style).

Implements: SG-06 (ADR-016), EN-080, LP-003, ST-001, DM-063.
"""

from __future__ import annotations

import csv
import glob
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

from epra.common.config import load_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
SCRIPT = "bootstrap_fixture_warehouse.py"

with (REPO_ROOT / "dbt" / "seeds" / "dim_strategy.csv").open(encoding="utf-8") as _fh:
    _ALL_STRATEGY_IDS = {row["strategy_id"] for row in csv.DictReader(_fh)}

_CONSUMER_LOAD_COLUMNS = ["ts_utc", "load_mwh"]
_STRATEGY_COSTS_COLUMNS = [
    "year_local",
    "month_local",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
    "unit_cost_eur_mwh",
]


def _load_script_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bootstrap_fixture_warehouse", SCRIPTS / SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _read_processed(data_root: Path, filename: str) -> pd.DataFrame:
    path = data_root / "processed" / filename
    assert path.is_file(), f"processed contract file {path} not written"
    return pd.read_parquet(path)


def _write_manual_oespi(data_root: Path) -> Path:
    manual_csv = data_root / "manual" / "oespi_monthly.csv"
    manual_csv.parent.mkdir(parents=True)
    manual_csv.write_text(
        "month,oespi_base,oespi_peak,source_url,retrieved_at\n2019-01,100.0,95.0,x,y\n"
    )
    return manual_csv


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


def test_existing_manual_oespi_does_not_block_and_is_never_touched(tmp_path: Path) -> None:
    """data/manual/oespi_monthly.csv is committed, human-reconciled data present
    in every checkout (CI included): it must neither trip the raw guard nor ever
    be rewritten by the generator (A-2, ING-101)."""
    manual_csv = _write_manual_oespi(tmp_path / "data")
    before = manual_csv.read_bytes()

    result = _run(
        "--data-root",
        str(tmp_path / "data"),
        "--window-start",
        "2022-01-01",
        "--window-end",
        "2022-02-28",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert manual_csv.read_bytes() == before


def test_force_never_overwrites_manual_oespi(tmp_path: Path) -> None:
    """Even --force over a populated data/raw leaves the ÖSPI CSV byte-identical."""
    manual_csv = _write_manual_oespi(tmp_path / "data")
    before = manual_csv.read_bytes()
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
    assert manual_csv.read_bytes() == before


def test_full_run_never_creates_manual_dir(tmp_path: Path) -> None:
    """The generator has no ÖSPI writer at all: data/manual is never created."""
    result = _run(
        "--data-root",
        str(tmp_path / "data"),
        "--window-start",
        "2022-01-01",
        "--window-end",
        "2022-01-31",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "data" / "manual").exists()


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
    """--processed-only writes only data/processed, regardless of
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

    consumer = _read_processed(tmp_path / "data", "consumer_load_hourly.parquet")
    assert not consumer["load_mwh"].isna().any()
    proc = _read_processed(tmp_path / "data", "strategy_costs_monthly.parquet")
    assert set(proc["strategy_id"].unique()) == _ALL_STRATEGY_IDS


def test_processed_outputs_match_module_output_contracts(tmp_path: Path) -> None:
    """Exactly the two SPEC contract files, with exactly the contract columns
    (LP-003 / ST-001 / SPEC-02 §5) -- no ING-004 provenance columns, no
    partitioned directory layout."""
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

    processed = tmp_path / "data" / "processed"
    assert sorted(p.name for p in processed.iterdir()) == [
        "consumer_load_hourly.parquet",
        "strategy_costs_monthly.parquet",
    ]
    consumer = _read_processed(tmp_path / "data", "consumer_load_hourly.parquet")
    assert list(consumer.columns) == _CONSUMER_LOAD_COLUMNS
    assert str(consumer["ts_utc"].dt.tz) == "UTC"
    costs = _read_processed(tmp_path / "data", "strategy_costs_monthly.parquet")
    assert list(costs.columns) == _STRATEGY_COSTS_COLUMNS


# --------------------------------------------------------------- determinism


def test_determinism_same_seed_identical_data_across_two_runs(tmp_path: Path) -> None:
    """Two independent runs with the same seed and window produce identical
    data columns for every written dataset (raw + processed + calendar).
    ``ingested_at_utc`` is the one column allowed to differ
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
    ]:
        f1 = _read_dataset(root1, dataset, subdir).drop(columns=["ingested_at_utc"])
        f2 = _read_dataset(root2, dataset, subdir).drop(columns=["ingested_at_utc"])
        pd.testing.assert_frame_equal(f1, f2)

    for filename in ["consumer_load_hourly.parquet", "strategy_costs_monthly.parquet"]:
        pd.testing.assert_frame_equal(
            _read_processed(root1, filename), _read_processed(root2, filename)
        )

    cal1 = pd.read_parquet(root1 / "raw" / "calendar" / "calendar.parquet")
    cal2 = pd.read_parquet(root2 / "raw" / "calendar" / "calendar.parquet")
    pd.testing.assert_frame_equal(cal1, cal2)


# ----------------------------------------------------------- window/coverage


def test_default_window_covers_2022_2024_with_dst_days_and_crisis_month(tmp_path: Path) -> None:
    """The default (no --window-* override) window is contiguous
    2022-01-01..2024-12-31, includes both 2024 DST transition days with the
    correct 23/25 local-hour counts, and includes the 2022-08 crisis month
    (ADR-016, DM-064, DM-065)."""
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
    assert set(weather["station_id"].unique()) == {load_settings().geosphere.station_id}

    consumer = _read_processed(tmp_path / "data", "consumer_load_hourly.parquet")
    assert consumer["load_mwh"].gt(0).all()

    proc = _read_processed(tmp_path / "data", "strategy_costs_monthly.parquet")
    assert set(proc["strategy_id"].unique()) == _ALL_STRATEGY_IDS
    months = proc[["year_local", "month_local"]].drop_duplicates()
    assert len(months) == 36  # Jan 2022 .. Dec 2024, no gaps (DM-050)
    for strategy_id in _ALL_STRATEGY_IDS:
        assert (proc["strategy_id"] == strategy_id).sum() == 36


def test_processed_only_discovers_real_local_window_from_calendar(tmp_path: Path) -> None:
    """Without an explicit --window-* override, --processed-only reads
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

    proc = _read_processed(target_root, "strategy_costs_monthly.parquet")
    assert set(proc["year_local"].unique()) == {2023}
    assert set(proc["month_local"].unique()) == {1, 2, 3}


def test_processed_only_aligns_costs_to_price_window_and_load_to_calendar(
    tmp_path: Path,
) -> None:
    """Strategy costs exist only for months carrying spot prices (ST-001, DM-050):
    with a calendar spine that runs past the last price (the forward-risk
    horizon), the cost stand-in ends at the last price month while the consumer
    load still spans the whole calendar (LP-003)."""
    long_seed = tmp_path / "long" / "data"
    short_seed = tmp_path / "short" / "data"
    for root, end in [(long_seed, "2023-06-30"), (short_seed, "2023-03-31")]:
        seeded = _run("--data-root", str(root), "--window-start", "2023-01-01", "--window-end", end)
        assert seeded.returncode == 0, seeded.stdout + seeded.stderr

    target_root = tmp_path / "data"
    (target_root / "raw" / "calendar").mkdir(parents=True)
    (long_seed / "raw" / "calendar" / "calendar.parquet").rename(
        target_root / "raw" / "calendar" / "calendar.parquet"
    )
    (short_seed / "raw" / "entsoe_prices_at").rename(target_root / "raw" / "entsoe_prices_at")

    result = _run("--data-root", str(target_root), "--processed-only")
    assert result.returncode == 0, result.stdout + result.stderr

    costs = _read_processed(target_root, "strategy_costs_monthly.parquet")
    assert sorted(costs["month_local"].unique()) == [1, 2, 3]
    consumer = _read_processed(target_root, "consumer_load_hourly.parquet")
    assert consumer["ts_utc"].dt.tz_convert("Europe/Vienna").dt.month.max() == 6


def test_strategy_ids_come_from_dim_strategy_seed() -> None:
    """The stand-in strategy grid is read from dbt/seeds/dim_strategy.csv (DM-063)."""
    module = _load_script_module()
    assert set(module.strategy_ids()) == _ALL_STRATEGY_IDS


def test_geosphere_station_comes_from_settings() -> None:
    """The synthetic weather station id is the configured one (ADR-007), and a
    missing configuration fails loudly instead of inventing one."""
    module = _load_script_module()
    settings = load_settings()
    assert module.geosphere_station_id(settings) == settings.geosphere.station_id

    geosphere = settings.geosphere.model_copy(update={"station_id": None})
    with pytest.raises(SystemExit):
        module.geosphere_station_id(settings.model_copy(update={"geosphere": geosphere}))


@pytest.mark.parametrize("flag", ["--data-root"])
def test_missing_data_root_argument_value_is_a_usage_error(flag: str) -> None:
    """Sanity: --data-root requires a value (argparse usage error, exit 2)."""
    result = _run(flag)
    assert result.returncode == 2
