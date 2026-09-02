"""Deterministic fixture/stand-in warehouse bootstrap (D-03..D-06, SG-06).

Synthesizes a contiguous, seeded ``data/raw/**`` window (2022-01-01..
2024-12-31 by default) plus the ``data/processed/**`` stand-ins that
``fct_consumer_load_hourly``/``fct_procurement_cost_monthly`` (04-05) load,
for two distinct callers:

- **CI** (fresh checkout, empty ``data/``): running with no flags (or
  ``--force``) synthesizes the full raw window (ENTSO-E prices AT/DE-LU,
  load, generation; GeoSphere daily; the ING-110 calendar spine) *and* the
  processed stand-ins over that same window -- everything ``dbt build``
  needs, with zero network access (D-04, D-05).
- **Local dev** (real ingested data already in ``data/raw``): pass
  ``--processed-only`` to synthesize *just* the ``data/processed`` stand-ins,
  aligned to the real ingestion window discovered from the committed
  ``data/raw/calendar/calendar.parquet`` spine (D-06) -- this NEVER touches
  ``data/raw`` or ``data/manual``, so it is always safe to run against a
  real, already-populated warehouse.

Guard (03_MODULES.md scripts table): a plain run (no ``--force``, no
``--processed-only``) against an already-populated ``data/raw`` or an
existing ``data/manual/oespi_monthly.csv`` refuses to write anything and
returns 1 -- real ingested data is irreplaceable and must never be
silently overwritten by synthetic fixture rows. ``--force`` is an explicit,
CI-only override.

Determinism: every random draw comes from a single ``numpy.random.default_rng``
seeded from the module-level ``_SEED`` constant, so two runs with the same
window produce byte-identical data columns (the ``ingested_at_utc``
provenance column is deliberately wall-clock -- see ``_io.write_month``,
whose own idempotency tests document the same seam).

Writes go exclusively through ``epra.ingest._io.write_month`` (parquet;
atomic ``.tmp`` + ``os.replace``) for every monthly dataset, and a
matching local atomic-write helper for the two whole-file/CSV outputs
(``calendar.parquet``, ``oespi_monthly.csv``) that do not fit
``write_month``'s per-row date/ts_utc validation contract. No committed
fixture parquet is ever copied (D-04) -- every row is synthesized here.

Usage::

    python scripts/bootstrap_fixture_warehouse.py [--force] [--processed-only]
        [--data-root PATH] [--window-start YYYY-MM-DD] [--window-end YYYY-MM-DD]

Exit 0 on success, 1 if the guard refuses to run.

Implements: SG-06 (ADR-010), D-03, D-04, D-05, D-06.
"""

from __future__ import annotations

import argparse
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

#: Determinism seed (Claude's Discretion per CONTEXT.md) -- a single seeded
#: generator drives every synthetic draw in this module.
_SEED = 424242

#: D-03: the default CI fixture window -- contiguous, includes the 2022-08
#: crisis month and both 2024 DST transition days.
_DEFAULT_WINDOW_START = date(2022, 1, 1)
_DEFAULT_WINDOW_END = date(2024, 12, 31)

#: DM-063 FK target -- must exactly match dbt/seeds/dim_strategy.csv.
_STRATEGY_IDS = ["S1", "S2", "S3", "S4_30", "S4_50", "S4_70"]

#: DM-061 accepted ranges -- synthetic values are always kept safely inside
#: these bounds so the generic range tests never flake on a random draw.
_PRICE_RANGE_EUR_MWH = (-500.0, 5000.0)
_LOAD_RANGE_MW = (3000.0, 13000.0)
_TAVG_RANGE_C = (-30.0, 42.0)

#: Generation psr_type/psr_name pairs (SG-17: kind='aggregated' only).
_PSR_TYPES = [("B01", "Biomass"), ("B16", "Solar"), ("B19", "Wind Onshore")]

#: GeoSphere station used across the real ingest (ADR-007) -- reused here so
#: the synthetic fixture shape matches the real raw contract exactly.
_GEOSPHERE_STATION_ID = "30"


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
    the fall-back local day has 25 (D-03).
    """
    # Use stdlib `timedelta`, not `pd.Timedelta(hours=...)` -- the latter hits
    # a pandas 2.3.3 "generic unit" DeprecationWarning on the bare-kwarg
    # constructor path (same fix already applied in epra.ingest.calendar).
    end_of_day_naive = pd.Timestamp(end) + timedelta(hours=23)
    # pandas-stubs doesn't type the `nonexistent`/`ambiguous` DST-handling
    # kwargs on this overload (they exist and work at runtime -- verified
    # against real spring-forward/fall-back days).
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

    The 2022-08 crisis month (D-03) gets an additive upward shock so it is
    visibly present in the series, still clipped inside DM-061's
    [-500, 5000] range.
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
        {
            "ts_utc": ts_utc,
            "price_eur_mwh": price,
            "resolution": "PT60M",
            "zone": zone,
        }
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
    frames = []
    for psr_type, psr_name in _PSR_TYPES:
        frames.append(
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
        )
    return pd.concat(frames, ignore_index=True).sort_values("ts_utc").reset_index(drop=True)


def _build_geosphere(rng: np.random.Generator, dates: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(dates)
    low, high = _TAVG_RANGE_C
    tavg = rng.uniform(low + 5.0, high - 4.0, size=n).astype("float64")
    return pd.DataFrame(
        {
            "date": dates,
            "station_id": _GEOSPHERE_STATION_ID,
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
    holiday_dates = set(at_holidays.keys())
    is_holiday_at = pd.Index(date_local).isin(holiday_dates)

    # Never re-derive the Mon-Fri 08-20 rule locally (D-10) -- reuse the
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
    """D-05 stand-in for the SPEC-03 consumer-load module output."""
    n = len(ts_utc)
    load_mwh = rng.uniform(0.4, 4.5, size=n).astype("float64")
    return pd.DataFrame({"ts_utc": ts_utc, "load_mwh": load_mwh})


def _build_procurement_cost_monthly(
    rng: np.random.Generator, start: date, end: date
) -> pd.DataFrame:
    """D-05 stand-in for the SPEC-05 procurement-strategy module output --
    every month in the window x all 6 ``dim_strategy`` strategy_ids
    (DM-063). Carries a helper ``date`` column (first-of-month) solely so
    this frame can be validated/written through ``write_month``'s
    ``key_column='date'`` path (SPEC-02 §5 does not itself expose ``date``;
    the mart selects only its own named columns)."""
    rows: list[dict[str, object]] = []
    for month_start_d in iter_month_starts(start, end):
        for strategy_id in _STRATEGY_IDS:
            volume_mwh = float(rng.uniform(150.0, 450.0))
            unit_cost_eur_mwh = float(rng.uniform(40.0, 320.0))
            rows.append(
                {
                    "date": month_start_d,
                    "year_local": month_start_d.year,
                    "month_local": month_start_d.month,
                    "strategy_id": strategy_id,
                    "volume_mwh": round(volume_mwh, 4),
                    "cost_eur": round(volume_mwh * unit_cost_eur_mwh, 2),
                    "unit_cost_eur_mwh": round(unit_cost_eur_mwh, 4),
                }
            )
    return pd.DataFrame(rows)


def _build_oespi_rows(start: date, end: date) -> pd.DataFrame:
    """Synthetic monthly OESPI index -- deterministic by construction (no rng
    draw), oespi_base always > 0 (DM-061)."""
    rows = []
    for i, month_start_d in enumerate(iter_month_starts(start, end)):
        base = 95.0 + 0.75 * i
        rows.append(
            {
                "month": f"{month_start_d:%Y-%m}",
                "oespi_base": round(base, 2),
                "oespi_peak": round(base * 1.15, 2),
                "source_url": "https://example.test/synthetic-oespi",
                "retrieved_at": "2026-01-01",
            }
        )
    return pd.DataFrame(
        rows, columns=["month", "oespi_base", "oespi_peak", "source_url", "retrieved_at"]
    )


# ------------------------------------------------------------------- writers


def _settings_with_data_raw(data_raw_root: Path) -> Settings:
    """The real project ``Settings`` with ``paths.data_raw`` redirected --
    same ``model_copy`` seam ``tests/conftest.py``'s ``tmp_settings`` fixture
    uses, reused here so raw *and* processed writes both go through
    ``write_month`` unmodified (D-04's "reuse write_month" instruction)."""
    settings = load_settings()
    paths = settings.paths.model_copy(update={"data_raw": data_raw_root})
    return settings.model_copy(update={"paths": paths})


def _write_ts_utc_dataset(frame: pd.DataFrame, dataset: str, settings: Settings) -> None:
    """Chunk ``frame`` by UTC calendar month and persist each chunk via
    ``write_month`` (default ``key_column='ts_utc'``)."""
    # tz_localize(None) before to_period(): to_period() on a tz-aware series
    # emits a "drops timezone information" UserWarning even though the values
    # are already UTC and the tz is being dropped intentionally here (we only
    # need the calendar-month bucket, not the tz-aware instant).
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
    """Single-file atomic parquet write (mirrors ``_io.write_month``'s
    ``.tmp`` + ``os.replace`` pattern) for the one whole-file dataset
    (``calendar.parquet``) that has no monthly-file layout to chunk into."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    frame.to_parquet(tmp_path, index=False, engine="pyarrow")
    os.replace(tmp_path, path)


def _atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    """Same atomic-write pattern as ``_atomic_write_parquet``, for the one
    CSV output (``oespi_monthly.csv``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
    frame.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)


def _write_processed_standins(
    rng: np.random.Generator, processed_root: Path, start: date, end: date
) -> None:
    settings = _settings_with_data_raw(processed_root)
    ts_utc = _vienna_hour_index(start, end)
    _atomic_write_parquet(
        _build_consumer_load_hourly(rng, ts_utc),
        processed_root / "consumer_load_hourly.parquet",
    )
    _write_date_keyed_dataset(
        _build_procurement_cost_monthly(rng, start, end),
        "procurement_cost_monthly",
        settings,
        key_column="date",
    )


# --------------------------------------------------------------------- guard


def _is_populated(path: Path) -> bool:
    """True if ``path`` exists and contains at least one file (recursively)."""
    return path.exists() and any(p.is_file() for p in path.rglob("*"))


def _discover_local_window(data_root: Path) -> tuple[date, date]:
    """The real local ingestion window (D-06: "aligned to the real
    2019->latest window"), read from the committed ``calendar.parquet``
    spine. Falls back to the default CI window if no calendar spine exists
    yet (e.g. a completely fresh checkout)."""
    calendar_path = data_root / "raw" / "calendar" / "calendar.parquet"
    if not calendar_path.exists():
        return _DEFAULT_WINDOW_START, _DEFAULT_WINDOW_END
    ts_utc = pd.read_parquet(calendar_path, columns=["ts_utc"])["ts_utc"]
    local = pd.to_datetime(ts_utc, utc=True).dt.tz_convert(VIENNA)
    start = local.min().date().replace(day=1)
    end = local.max().date()
    return start, end


# ---------------------------------------------------------------------- CLI


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an already-populated data/raw or data/manual/oespi_monthly.csv "
        "with synthetic fixture data. CI/disposable-environment use only -- never pass "
        "this against a real, already-ingested data/ tree.",
    )
    parser.add_argument(
        "--processed-only",
        action="store_true",
        help="Only synthesize data/processed/** stand-ins (never touches data/raw or "
        "data/manual), aligned to the real local ingestion window discovered from "
        "data/raw/calendar/calendar.parquet (D-06). Always safe to run locally.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Override the data/ root (default: <repo>/data). Used by tests.",
    )
    parser.add_argument("--window-start", type=_parse_cli_date, default=None)
    parser.add_argument("--window-end", type=_parse_cli_date, default=None)
    args = parser.parse_args(argv)

    data_root = args.data_root if args.data_root is not None else (REPO_ROOT / "data")
    raw_root = data_root / "raw"
    manual_csv = data_root / "manual" / "oespi_monthly.csv"
    processed_root = data_root / "processed"

    rng = np.random.default_rng(_SEED)

    if args.processed_only:
        start, end = (
            (args.window_start, args.window_end)
            if args.window_start and args.window_end
            else _discover_local_window(data_root)
        )
        _write_processed_standins(rng, processed_root, start, end)
        print(
            f"OK: wrote data/processed stand-ins for {start:%Y-%m-%d}..{end:%Y-%m-%d} "
            "(--processed-only, data/raw and data/manual left untouched)."
        )
        return 0

    populated = _is_populated(raw_root) or manual_csv.exists()
    if populated and not args.force:
        print(
            f"ERROR: {raw_root} and/or {manual_csv} already contain data. Refusing to "
            "synthesize CI fixture data over real ingested data (guard, 03_MODULES.md)."
        )
        print(
            "Pass --force ONLY in a disposable CI/test environment, or use "
            "--processed-only to populate just the data/processed stand-ins without "
            "touching data/raw or data/manual."
        )
        return 1

    start = args.window_start or _DEFAULT_WINDOW_START
    end = args.window_end or _DEFAULT_WINDOW_END

    settings = _settings_with_data_raw(raw_root)
    ts_utc = _vienna_hour_index(start, end)

    _write_ts_utc_dataset(_build_prices(rng, ts_utc, "AT"), "entsoe_prices_at", settings)
    _write_ts_utc_dataset(_build_prices(rng, ts_utc, "DE_LU"), "entsoe_prices_delu", settings)
    _write_ts_utc_dataset(_build_load(rng, ts_utc), "entsoe_load_at", settings)
    _write_ts_utc_dataset(_build_gen(rng, ts_utc), "entsoe_gen_at", settings)

    daily_dates = pd.date_range(start, end, freq="D")
    _write_date_keyed_dataset(
        _build_geosphere(rng, daily_dates), "geosphere_graz_daily", settings, key_column="date"
    )

    _atomic_write_parquet(_build_calendar(start, end), raw_root / "calendar" / "calendar.parquet")
    _atomic_write_csv(_build_oespi_rows(start, end), manual_csv)

    _write_processed_standins(rng, processed_root, start, end)

    print(
        f"OK: synthesized data/raw + data/manual + data/processed for "
        f"{start:%Y-%m-%d}..{end:%Y-%m-%d}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
