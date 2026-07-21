"""Unit tests for `epra.ingest.entsoe.hourly_mean` — the ING-062 guard
against the sum/mean confusion trap (T-2).

A synthetic PT15M day is fed through `hourly_mean` and the result MUST be
the arithmetic mean of the four quarters within each hour, never their sum.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from epra.ingest.entsoe import hourly_mean


def _pt15m_hour(hour_start: str, values: list[float]) -> pd.DataFrame:
    """One hour of 4 PT15M rows starting at `hour_start` (UTC ISO string)."""
    start = pd.Timestamp(hour_start, tz="UTC")
    return pd.DataFrame(
        {
            "ts_utc": [start + timedelta(minutes=15 * i) for i in range(4)],
            "value": values,
        }
    )


def test_hourly_mean_averages_quarters_not_sum() -> None:
    # ING-062: known values [10, 20, 30, 40] must aggregate to mean 25.0,
    # never sum 100.0.
    df = _pt15m_hour("2024-01-01T00:00:00Z", [10.0, 20.0, 30.0, 40.0])

    out = hourly_mean(df, "value")

    assert len(out) == 1
    assert out["value"].iloc[0] == 25.0
    assert out["value"].iloc[0] != 100.0


def test_hourly_mean_full_day_of_pt15m_prices() -> None:
    # A full synthetic PT15M day (24 hours x 4 quarters) — every hour's mean
    # must equal the arithmetic mean of its 4 quarters, never their sum.
    rows = []
    for hour in range(24):
        base = 10.0 + hour
        quarters = [base, base + 1, base + 2, base + 3]
        rows.append(_pt15m_hour(f"2024-01-01T{hour:02d}:00:00Z", quarters))
    df = pd.concat(rows, ignore_index=True)

    out = hourly_mean(df, "value")

    assert len(out) == 24
    for hour in range(24):
        expected_mean = 10.0 + hour + 1.5  # mean of [base, base+1, base+2, base+3]
        assert out["value"].iloc[hour] == expected_mean


def test_hourly_mean_works_for_load_mw_column_name() -> None:
    # Helper must be reusable for any numeric column name, not hardcoded to
    # price_eur_mwh (ING-061 also applies to load/generation MW averaging).
    df = _pt15m_hour("2024-01-01T00:00:00Z", [100.0, 200.0, 300.0, 400.0])
    df = df.rename(columns={"value": "load_mw"})

    out = hourly_mean(df, "load_mw")

    assert len(out) == 1
    assert out["load_mw"].iloc[0] == 250.0


def test_hourly_mean_floors_ts_utc_to_the_hour() -> None:
    df = _pt15m_hour("2024-01-01T05:00:00Z", [1.0, 2.0, 3.0, 4.0])

    out = hourly_mean(df, "value")

    assert out["ts_utc"].iloc[0] == pd.Timestamp("2024-01-01T05:00:00Z")


def test_hourly_mean_pt60m_input_is_unchanged() -> None:
    # An already-hourly frame (PT60M) should pass through unchanged — mean
    # of a single value is that value, not a discarded/duplicated row.
    df = pd.DataFrame(
        {
            "ts_utc": pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"], utc=True),
            "price_eur_mwh": [45.0, 50.0],
        }
    )

    out = hourly_mean(df, "price_eur_mwh")

    assert out["price_eur_mwh"].tolist() == [45.0, 50.0]
