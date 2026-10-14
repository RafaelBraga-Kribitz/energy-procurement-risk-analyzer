"""Regenerate golden test values (EN-072, ST-601, LP-040).

Goldens are regenerated ONLY by this script, ONLY in a PR that explains why,
with a diff of old vs new values (AGENTS.md §2 item 6 — human approves).

Targets:

- ``profile``: ``tests/golden/consumer_load_2023.sha256`` — sha256 of the 2023
  slice of the StyriaMetal profile built on a 2022-2024 calendar (LP-040).
- ``strategies``: ``tests/golden/strategy_annual_summary.json`` (ST-601) — the
  annual matrix of closed-form synthetic inputs (never published results).

Usage: ``python scripts/generate_golden_metrics.py --target profile``

Implements: EN-072 regeneration path, LP-040, ST-601.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date

import numpy as np
import pandas as pd

from epra.common.config import REPO_ROOT, load_consumer_profile, load_strategy_config
from epra.consumer import profile
from epra.ingest.calendar import calendar_frame
from epra.strategies.calibration import Anchors
from epra.strategies.engine import StrategyParams, annual_summary, monthly_costs

GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
PROFILE_GOLDEN = GOLDEN_DIR / "consumer_load_2023.sha256"
#: LP-040 golden window: 2023 sits inside a complete-year calendar.
PROFILE_WINDOW = (date(2022, 1, 1), date(2024, 12, 31))
PROFILE_GOLDEN_YEAR = 2023
STRATEGY_GOLDEN = GOLDEN_DIR / "strategy_annual_summary.json"
#: ST-601 golden inputs are closed-form (no data, no randomness): the golden
#: pins the engine's arithmetic, not any market observation (A-2).
GOLDEN_ANCHORS = Anchors(
    p_ref_base=40.0, p_ref_peak=42.0, oespi_base_ref=100.0, oespi_peak_ref=85.0
)
GOLDEN_W_PEAK = 0.48
GOLDEN_DECIMALS = 6


def regenerate_profile_golden() -> str:
    """Rewrite the LP-040 checksum file; returns the new checksum.

    Implements: LP-040.
    """
    built = profile.build_profile(calendar_frame(*PROFILE_WINDOW), load_consumer_profile())
    checksum = profile.year_checksum(built, PROFILE_GOLDEN_YEAR)
    old = PROFILE_GOLDEN.read_text(encoding="utf-8").strip() if PROFILE_GOLDEN.exists() else None
    PROFILE_GOLDEN.write_text(checksum + "\n", encoding="utf-8")
    print(f"profile golden: {old} -> {checksum}")
    return checksum


def golden_inputs() -> tuple[pd.DataFrame, pd.DataFrame, StrategyParams]:
    """Closed-form monthly spot + ÖSPI 2019-2025 and the config's parameter set.

    Implements: ST-601 (deterministic golden inputs).
    """
    months = pd.period_range("2019-01", "2025-12", freq="M")
    t = np.arange(len(months), dtype=float)
    crisis = np.exp(-(((t - 43.0) / 8.0) ** 2))  # spot peaks around 2022-08
    index_wave = np.exp(-(((t - 49.0) / 10.0) ** 2))  # index lags spot
    volume = 4000.0 + 300.0 * np.cos(2 * np.pi * (months.month.to_numpy() - 1) / 12)
    price = 45.0 + 400.0 * crisis + 8.0 * np.sin(t)
    keys = {"year_local": months.year.to_numpy(), "month_local": months.month.to_numpy()}
    spot = pd.DataFrame({**keys, "volume_mwh": volume, "spot_cost_eur": volume * price})
    oespi = pd.DataFrame(
        {**keys, "oespi_base": 100.0 + 600.0 * index_wave, "oespi_peak": 85.0 + 540.0 * index_wave}
    )
    cfg = load_strategy_config()
    params = StrategyParams(
        anchors=GOLDEN_ANCHORS,
        w_peak=GOLDEN_W_PEAK,
        fixed_premium_eur_mwh=cfg.fixed_premium_eur_mwh,
        lock_window_months=tuple(cfg.lock_window_months),
        hybrid_ratios=tuple(cfg.hybrid_ratios),
        peak_available=cfg.peak_available,
    )
    return spot, oespi, params


def golden_annual_summary() -> pd.DataFrame:
    """ST-301 annual summary of the golden inputs (rounded for the JSON).

    Implements: ST-601.
    """
    spot, oespi, params = golden_inputs()
    years = list(load_strategy_config().retrospective_years)
    annual = annual_summary(monthly_costs(spot, oespi, params, years))
    return annual.round(GOLDEN_DECIMALS)


def regenerate_strategy_golden() -> None:
    """Rewrite ``tests/golden/strategy_annual_summary.json`` (ST-601).

    Implements: ST-601.
    """
    records = golden_annual_summary().to_dict("records")
    old = (
        json.loads(STRATEGY_GOLDEN.read_text(encoding="utf-8"))
        if STRATEGY_GOLDEN.exists()
        else None
    )
    STRATEGY_GOLDEN.write_text(json.dumps(records, indent=1) + "\n", encoding="utf-8")
    changed = "new" if old is None else ("unchanged" if old == records else "CHANGED")
    print(f"strategy golden: {len(records)} rows written ({changed})")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Implements: EN-072.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", choices=["profile", "strategies"], required=True)
    args = parser.parse_args(argv)
    if args.target == "profile":
        regenerate_profile_golden()
    else:
        regenerate_strategy_golden()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
