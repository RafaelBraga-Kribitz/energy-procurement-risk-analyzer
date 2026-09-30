"""Deterministic fixture/stand-in warehouse bootstrap (ADR-016, SG-06).

Synthesizes a contiguous, seeded ``data/raw/**`` window (2022-01-01..
2024-12-31 by default) plus the two ``data/processed`` stand-in files that
``fct_consumer_load_hourly``/``fct_procurement_cost_monthly`` load, for two
distinct callers:

- **CI** (fresh checkout, empty ``data/raw``): running with no flags (or
  ``--force``) synthesizes the full raw window (ENTSO-E prices AT/DE-LU,
  load, generation; GeoSphere daily; the ING-110 calendar spine) *and* the
  processed stand-ins over that same window -- everything ``dbt build``
  needs, with zero network access.
- **Local dev** (real ingested data already in ``data/raw``): pass
  ``--processed-only`` to synthesize *just* the ``data/processed`` stand-ins,
  aligned to the real local windows (consumer load: the calendar spine
  incl. the forward-risk window, LP-003; strategy costs: the months that
  actually carry AT prices) -- this NEVER touches ``data/raw``.

``data/manual/oespi_monthly.csv`` is NEVER read or written by this script.
It is committed, human-reconciled data (ING-101/102) that every checkout --
CI included -- already contains, so dbt's ``stg_oespi_monthly`` always reads
the real series; synthesizing ÖSPI values would be invented data (A-2).

Guard: a plain run (no ``--force``, no ``--processed-only``) against an
already-populated ``data/raw`` refuses to write anything and returns 1 --
real ingested data is irreplaceable and must never be silently overwritten
by synthetic fixture rows. ``--force`` is an explicit, CI-only override.

Processed stand-ins honour the module OUTPUT CONTRACTS exactly (no ING-004
provenance columns, one file each):

- ``data/processed/consumer_load_hourly.parquet`` -- ``ts_utc, load_mwh``
  (SPEC-03 LP-003, SPEC-02 §5).
- ``data/processed/strategy_costs_monthly.parquet`` -- ``year_local,
  month_local, strategy_id, volume_mwh, cost_eur, unit_cost_eur_mwh``
  (SPEC-05 ST-001, SPEC-02 §5 ``fct_procurement_cost_monthly``).

Determinism: every random draw comes from a single ``numpy.random.default_rng``
seeded from the module-level ``_SEED`` constant, so two runs with the same
window produce byte-identical data columns (the raw ``ingested_at_utc``
provenance column is deliberately wall-clock -- see ``_io.write_month``).

Usage::

    python scripts/bootstrap_fixture_warehouse.py [--force] [--processed-only]
        [--data-root PATH] [--window-start YYYY-MM-DD] [--window-end YYYY-MM-DD]

Exit 0 on success, 1 if the guard refuses to run.

Implements: SG-06 (ADR-016), EN-080 (CI dbt job on synthesized fixtures),
LP-003 / ST-001 (processed output-contract stand-ins).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
from holidays.countries.austria import Austria

from epra.common.config import REPO_ROOT, Settings, load_settings
from epra.common.timeutil import VIENNA, is_peak_hour, iter_month_starts
from epra.ingest._io import request_hash, write_month

#: Determinism seed -- a single seeded generator drives every synthetic draw.
_SEED = 424242

#: ADR-016: the default CI fixture window -- contiguous, includes the 2022-08
#: crisis month (DM-064) and both 2024 DST transition days (DM-065).
_DEFAULT_WINDOW_START = date(2022, 1, 1)
_DEFAULT_WINDOW_END = date(2024, 12, 31)

#: DM-063 FK target -- the strategy grid is read from the committed seed so
#: the stand-in can never drift from ``dim_strategy`` (SPEC-02 §4).
_DIM_STRATEGY_SEED = REPO_ROOT / "dbt" / "seeds" / "dim_strategy.csv"

#: Processed output-contract files + columns (SPEC-03 LP-003, SPEC-05 ST-001,
#: SPEC-02 §5). ``dbt/models/sources.yml`` reads exactly these files.
CONSUMER_LOAD_FILE = "consumer_load_hourly.parquet"
CONSUMER_LOAD_COLUMNS = ["ts_utc", "load_mwh"]
STRATEGY_COSTS_FILE = "strategy_costs_monthly.parquet"
STRATEGY_COSTS_COLUMNS = [
    "year_local",
    "month_local",
    "strategy_id",
    "volume_mwh",
    "cost_eur",
    "unit_cost_eur_mwh",
]

#: DM-061 accepted ranges -- synthetic values are always kept safely inside
#: these bounds so the generic range tests never flake on a random draw.
_PRICE_RANGE_EUR_MWH = (-500.0, 5000.0)
_LOAD_RANGE_MW = (3000.0, 13000.0)
_TAVG_RANGE_C = (-30.0, 42.0)

#: Generation psr_type/psr_name pairs (SG-17: kind='aggregated' only).
_PSR_TYPES = [("B01", "Biomass"), ("B16", "Solar"), ("B19", "Wind Onshore")]


# ------------------------------------------------------------ config lookups


def strategy_ids(seed_path: Path = _DIM_STRATEGY_SEED) -> list[str]:
    """``strategy_id`` values of the committed ``dim_strategy`` seed, in file order.

    Implements: DM-063 (stand-in strategy ids always exist in dim_strategy).
    """
    with seed_path.open(encoding="utf-8", newline="") as fh:
        return [row["strategy_id"] for row in csv.DictReader(fh)]


def geosphere_station_id(settings: Settings) -> str:
    """The configured GeoSphere station (ING-091 / ADR-007) -- never hardcoded.

    Implements: ING-091 (station id comes from ``config/settings.yaml``).
    """
    station_id = settings.geosphere.station_id
    if not station_id:
        raise SystemExit("ERROR: settings.geosphere.station_id is not configured (ADR-007).")
    return station_id


# --------------------------------------------------------------------- time


def _parse_cli_date(text: str) -> date:
    """``argparse`` ``type=`` callback (mirrors ``epra.ingest.calendar``)."""
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {text!r}; expected YYYY-MM-DD") from exc


def _vienna_hour_index(start: date, end: date) -> pd.DatetimeIndex:
    """Contiguous Vienna-local hourly timestamps, ``start`` 00:00 through the
    last local hour of ``end`` (inclusive), returned tz-converted to UTC.

    DST-correct by construction: the spring-forward local day has 23 hours,
    the fall-back local day has 25 (DM-065).
    """
    # stdlib `timedelta`, not `pd.Timedelta(hours=...)` (pandas 2.3.3
    # "generic unit" DeprecationWarning; same fix as epra.ingest.calendar).
    end_of_day_naive = pd.Timestamp(end) + timedelta(hours=23)
    # pandas-stubs doesn't type the `nonexistent`/`ambiguous` kwargs here.
    local: pd.DatetimeIndex = pd.date_range(  # type: ignore[call-overload]
        start=pd.Timestamp(start),
        end=end_of_day_naive,
        freq="h",
        tz=VIENNA,
        nonexistent="shift_forward",
        ambiguous="infer",
    )
    return local.tz_convert("UTC")


# ---------------------------------------------------------- dataset builders


def _build_prices(rng: np.random.Generator, ts_utc: pd.DatetimeIndex, zone: str) -> pd.DataFrame:
    """Synthetic hourly day-ahead price for ``zone`` (AT or DE_LU).

    The 2022-08 crisis month gets an additive upward shock so it is visibly
    present in the series, still clipped inside DM-061's [-500, 5000] range.
    """
    n = len(ts_utc)
    price = rng.normal(loc=90.0, scale=35.0, size=n)
    local = ts_utc.tz_convert(VIENNA)
    crisis_mask = (local.year == 2022) & (local.month == 8)
    if crisis_mask.any():
        price = np.where(crisis_mask, price + rng.normal(loc=280.0, scale=40.0, size=n), price)
    low, high = _PRICE_RANGE_EUR_MWH
    price = np.clip(price, low + 50.0, high - 500.0).astype("float64")
    return pd.DataFrame(
        {"ts_utc": ts_utc, "price_eur_mwh": price, "resolution": "PT60M", "zone": zone}
    )


def _build_load(rng: np.random.Generator, ts_utc: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(ts_utc)
    low, high = _LOAD_RANGE_MW
    load_mw = rng.uniform(low + 200.0, high - 500.0, size=n).astype("float64")
    return pd.DataFrame({"ts_utc": ts_utc, "load_mw": load_mw, "resolution": "PT60M", "zone": "AT"})


def _build_gen(rng: np.random.Generator, ts_utc: pd.DatetimeIndex) -> pd.DataFrame:
    """Long-format hourly generation x psr_type, ``kind='aggregated'`` only
    (SG-17 -- raw ``consumption`` rows are never synthesized here)."""
    n = len(ts_utc)
    frames = [
        pd.DataFrame(
            {
                "ts_utc": ts_utc,
                "psr_type": psr_type,
                "psr_name": psr_name,
                "kind": "aggregated",
                "value_mw": rng.uniform(10.0, 800.0, size=n).astype("float64"),
                "resolution": "PT60M",
                "zone": "AT",
            }
        )
        for psr_type, psr_name in _PSR_TYPES
    ]
    return pd.concat(frames, ignore_index=True).sort_values("ts_utc").reset_index(drop=True)


def _build_geosphere(
    rng: np.random.Generator, dates: pd.DatetimeIndex, station_id: str
) -> pd.DataFrame:
    n = len(dates)
    low, high = _TAVG_RANGE_C
    tavg = rng.uniform(low + 5.0, high - 4.0, size=n).astype("float64")
    return pd.DataFrame(
        {
            "date": dates,
            "station_id": station_id,
            "tl_mittel_c": tavg,
            "parameter_raw": "tl_mittel",
        }
    )


def _build_calendar(start: date, end: date) -> pd.DataFrame:
    """ING-110 calendar shape, synthesized standalone (no dependency on real
    ingested price data / ``latest_complete_month`` -- this must work on a
    completely empty CI checkout)."""
    ts_utc = _vienna_hour_index(start, end)
    local = ts_utc.tz_convert(VIENNA)
    date_local = local.date
    dow_local = local.dayofweek

    at_holidays = Austria(subdiv="6", years=range(start.year, end.year + 1))
    is_holiday_at = pd.Index(date_local).isin(set(at_holidays.keys()))

    # Never re-derive the Mon-Fri 08-20 rule locally (ADR-011) -- reuse the
    # sanctioned timeutil helper per row, same as epra.ingest.calendar.
    is_peak = [
        is_peak_hour(ts.to_pydatetime(), is_holiday=bool(h))
        for ts, h in zip(local, is_holiday_at, strict=True)
    ]

    return pd.DataFrame(
        {
            "ts_utc": ts_utc,
            "date_local": date_local,
            "hour_local": local.hour,
            "dow_local": dow_local,
            "is_weekend": dow_local >= 5,
            "is_holiday_at": is_holiday_at,
            "is_peak_hour": is_peak,
            "year_local": local.year,
            "month_local": local.month,
        }
    )


def _build_consumer_load_hourly(rng: np.random.Generator, ts_utc: pd.DatetimeIndex) -> pd.DataFrame:
    """Stand-in for the SPEC-03 output (LP-003 columns exactly)."""
    load_mwh = rng.uniform(0.4, 4.5, size=len(ts_utc)).astype("float64")
    return pd.DataFrame({"ts_utc": ts_utc, "load_mwh": load_mwh})[CONSUMER_LOAD_COLUMNS]


def _build_strategy_costs_monthly(rng: np.random.Generator, start: date, end: date) -> pd.DataFrame:
    """Stand-in for the SPEC-05 ST-001 output -- every month in the window x
    every ``dim_strategy`` strategy_id (DM-063), SPEC-02 §5 columns exactly."""
    rows: list[dict[str, object]] = []
    grid = strategy_ids()
    for month_start_d in iter_month_starts(start, end):
        for strategy_id in grid:
            volume_mwh = float(rng.uniform(150.0, 450.0))
            unit_cost_eur_mwh = float(rng.uniform(40.0, 320.0))
            rows.append(
                {
                    "year_local": month_start_d.year,
                    "month_local": month_start_d.month,
                    "strategy_id": strategy_id,
                    "volume_mwh": round(volume_mwh, 4),
                    "cost_eur": round(volume_mwh * unit_cost_eur_mwh, 2),
                    "unit_cost_eur_mwh": round(unit_cost_eur_mwh, 4),
                }
            )
    return pd.DataFrame(rows, columns=STRATEGY_COSTS_COLUMNS)


# ------------------------------------------------------------------- writers


def _settings_with_data_raw(data_raw_root: Path) -> Settings:
    """The real project ``Settings`` with ``paths.data_raw`` redirected --
    same ``model_copy`` seam ``tests/conftest.py``'s ``tmp_settings`` uses, so
    raw writes go through ``write_month`` unmodified (ING-003/004 layout)."""
    settings = load_settings()
    paths = settings.paths.model_copy(update={"data_raw": data_raw_root})
    return settings.model_copy(update={"paths": paths})


def _write_ts_utc_dataset(frame: pd.DataFrame, dataset: str, settings: Settings) -> None:
    """Chunk ``frame`` by UTC calendar month and persist each chunk via
    ``write_month`` (default ``key_column='ts_utc'``)."""
    # tz_localize(None) before to_period(): avoids the "drops timezone
    # information" UserWarning; only the calendar-month bucket is needed.
    periods = frame["ts_utc"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M")
    for period, group in frame.groupby(periods, sort=True):
        month = period.to_timestamp().date()
        req_hash = request_hash(f"synthetic://bootstrap_fixture_warehouse/{dataset}/{period}")
        write_month(group.reset_index(drop=True), dataset, month, req_hash, settings)


def _write_date_keyed_dataset(
    frame: pd.DataFrame, dataset: str, settings: Settings, *, key_column: str = "date"
) -> None:
    """Chunk ``frame`` by calendar month of ``key_column`` and persist each
    chunk via ``write_month(..., key_column=key_column)``."""
    periods = pd.to_datetime(frame[key_column]).dt.to_period("M")
    for period, group in frame.groupby(periods, sort=True):
        month = period.to_timestamp().date()
        req_hash = request_hash(f"synthetic://bootstrap_fixture_warehouse/{dataset}/{period}")
        write_month(
            group.reset_index(drop=True), dataset, month, req_hash, settings, key_column=key_column
        )


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    """Single-file atomic parquet write (``.tmp`` + ``os.replace``, same
    pattern as ``_io.write_month``; pyarrow engine per ADR-004)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    frame.to_parquet(tmp_path, index=False, engine="pyarrow")
    os.replace(tmp_path, path)


def _write_processed_standins(
    rng: np.random.Generator,
    processed_root: Path,
    load_window: tuple[date, date],
    cost_window: tuple[date, date],
) -> None:
    """Write the two processed output-contract files (LP-003, ST-001)."""
    ts_utc = _vienna_hour_index(*load_window)
    _atomic_write_parquet(
        _build_consumer_load_hourly(rng, ts_utc), processed_root / CONSUMER_LOAD_FILE
    )
    _atomic_write_parquet(
        _build_strategy_costs_monthly(rng, *cost_window), processed_root / STRATEGY_COSTS_FILE
    )


def _write_raw_window(rng: np.random.Generator, raw_root: Path, start: date, end: date) -> None:
    """Synthesize every raw dataset dbt reads (SPEC-01 §7 layout) over the window."""
    settings = _settings_with_data_raw(raw_root)
    ts_utc = _vienna_hour_index(start, end)

    _write_ts_utc_dataset(_build_prices(rng, ts_utc, "AT"), "entsoe_prices_at", settings)
    _write_ts_utc_dataset(_build_prices(rng, ts_utc, "DE_LU"), "entsoe_prices_delu", settings)
    _write_ts_utc_dataset(_build_load(rng, ts_utc), "entsoe_load_at", settings)
    _write_ts_utc_dataset(_build_gen(rng, ts_utc), "entsoe_gen_at", settings)

    weather = _build_geosphere(
        rng, pd.date_range(start, end, freq="D"), geosphere_station_id(settings)
    )
    _write_date_keyed_dataset(weather, "geosphere_graz_daily", settings, key_column="date")

    _atomic_write_parquet(_build_calendar(start, end), raw_root / "calendar" / "calendar.parquet")


# --------------------------------------------------------- window discovery


def _is_populated(path: Path) -> bool:
    """True if ``path`` exists and contains at least one file (recursively)."""
    return path.exists() and any(p.is_file() for p in path.rglob("*"))


def _local_month_window(ts_utc: pd.Series) -> tuple[date, date]:
    """(first day of the first local month, last local date) of a UTC series."""
    local = pd.to_datetime(ts_utc, utc=True).dt.tz_convert(VIENNA)
    return local.min().date().replace(day=1), local.max().date()


def _discover_local_window(data_root: Path) -> tuple[date, date]:
    """The real local calendar window (incl. the forward-risk horizon, LP-003),
    read from ``data/raw/calendar/calendar.parquet``. Falls back to the default
    CI window if no calendar spine exists yet (a completely fresh checkout)."""
    calendar_path = data_root / "raw" / "calendar" / "calendar.parquet"
    if not calendar_path.exists():
        return _DEFAULT_WINDOW_START, _DEFAULT_WINDOW_END
    return _local_month_window(pd.read_parquet(calendar_path, columns=["ts_utc"])["ts_utc"])


def _discover_price_window(data_root: Path) -> tuple[date, date] | None:
    """Local month window actually covered by raw AT prices, or ``None``.

    Strategy costs (ST-001) exist only for months with a spot price, so the
    stand-in must end where the price data ends (DM-050 no-gap test).
    """
    files = sorted((data_root / "raw" / "entsoe_prices_at").rglob("*.parquet"))
    if not files:
        return None
    ts_utc = pd.concat([pd.read_parquet(f, columns=["ts_utc"]) for f in files])["ts_utc"]
    return _local_month_window(ts_utc)


# ---------------------------------------------------------------------- CLI


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an already-populated data/raw with synthetic fixture data. "
        "CI/disposable-environment use only. data/manual is never touched.",
    )
    parser.add_argument(
        "--processed-only",
        action="store_true",
        help="Only write the two data/processed stand-in files (never touches data/raw "
        "or data/manual), aligned to the real local calendar/price windows.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Override the data/ root (default: <repo>/data). Used by tests.",
    )
    parser.add_argument("--window-start", type=_parse_cli_date, default=None)
    parser.add_argument("--window-end", type=_parse_cli_date, default=None)
    return parser


def _run_processed_only(args: argparse.Namespace, data_root: Path) -> int:
    rng = np.random.default_rng(_SEED)
    if args.window_start and args.window_end:
        load_window = cost_window = (args.window_start, args.window_end)
    else:
        load_window = _discover_local_window(data_root)
        cost_window = _discover_price_window(data_root) or load_window
    _write_processed_standins(rng, data_root / "processed", load_window, cost_window)
    print(
        f"OK: wrote data/processed stand-ins (load {load_window[0]}..{load_window[1]}, "
        f"costs {cost_window[0]}..{cost_window[1]}); data/raw and data/manual untouched."
    )
    return 0


def _run_full(args: argparse.Namespace, data_root: Path) -> int:
    raw_root = data_root / "raw"
    if _is_populated(raw_root) and not args.force:
        print(
            f"ERROR: {raw_root} already contains data. Refusing to synthesize CI fixture "
            "data over real ingested data. Pass --force ONLY in a disposable CI/test "
            "environment, or use --processed-only to write just the data/processed stand-ins."
        )
        return 1
    start = args.window_start or _DEFAULT_WINDOW_START
    end = args.window_end or _DEFAULT_WINDOW_END
    rng = np.random.default_rng(_SEED)
    _write_raw_window(rng, raw_root, start, end)
    _write_processed_standins(rng, data_root / "processed", (start, end), (start, end))
    print(f"OK: synthesized data/raw + data/processed for {start}..{end} (data/manual untouched).")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: guarded full fixture synthesis, or processed-only stand-ins.

    Implements: SG-06 (ADR-016), EN-080 (CI dbt job fixture bootstrap),
    LP-003 / ST-001 (processed output-contract stand-ins).
    """
    args = _build_parser().parse_args(argv)
    data_root = args.data_root if args.data_root is not None else (REPO_ROOT / "data")
    if args.processed_only:
        return _run_processed_only(args, data_root)
    return _run_full(args, data_root)


if __name__ == "__main__":
    sys.exit(main())
