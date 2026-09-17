"""ST-303 sensitivities: three config-delta reruns of the same cost engine.

Exactly three blocks (A-3 / D-14): premium {0, 5, 10}, flat_baseload via
``build_profile`` then re-align, and lock window months 1..12 of Y-1.
``peak_available`` is not a sensitivity row (D-15).

Implements: ST-303, D-14.
"""

from __future__ import annotations

import pandas as pd

from epra.analytics._kit import frame_to_markdown, write_markdown
from epra.common.config import ConsumerProfileCfg, Settings, StrategyCfg, load_consumer_profile
from epra.strategies.align import (
    CALENDAR_COLS,
    AlignedVolumes,
    align_hourly,
    load_calendar,
    load_price_hourly,
)
from epra.strategies.annual import annual_summary, strategies_dir
from epra.strategies.calibration import Anchors
from epra.strategies.retrospective import ST502_SENTENCE, _stack_costs

PREMIUMS_EUR_MWH = (0.0, 5.0, 10.0)
LOCK_WINDOW_FULL = list(range(1, 13))
HEADING_PREMIUM = "## Premium EUR/MWh"
HEADING_FLAT = "## Load profile flat_baseload"
HEADING_LOCK = "## Lock window full prior year"
FORBIDDEN_HEADING = "## Peak available"


def _filter_years(aligned: AlignedVolumes, years: set[int]) -> AlignedVolumes:
    return AlignedVolumes(
        hourly=aligned.hourly.loc[aligned.hourly["year_local"].isin(years)],
        monthly=aligned.monthly.loc[aligned.monthly["year_local"].isin(years)],
        dropped_hours=aligned.dropped_hours,
    )


def annual_for_cfg(
    aligned: AlignedVolumes,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    cfg: StrategyCfg,
) -> pd.DataFrame:
    """Same engine as retrospective ``run``, without writing artifacts.

    Implements: ST-303.
    """
    retro = _filter_years(aligned, set(cfg.retrospective_years))
    return annual_summary(_stack_costs(retro, oespi, anchors, w_peak, cfg))


def calendar_from_prices(prices: pd.DataFrame) -> pd.DataFrame | None:
    """Use price-mart calendar attributes when they are already on the frame."""
    if all(col in prices.columns for col in CALENDAR_COLS):
        return prices.loc[:, list(CALENDAR_COLS)].drop_duplicates("ts_utc")
    return None


def align_flat_baseload(
    prices: pd.DataFrame,
    calendar_df: pd.DataFrame,
    consumer_cfg: ConsumerProfileCfg,
) -> AlignedVolumes:
    """Rebuild load with ``profile_name=flat_baseload`` and ST-101 align.

    Implements: ST-303, D-14.
    """
    from epra.consumer.profile import build_profile

    flat_cfg = consumer_cfg.model_copy(update={"profile_name": "flat_baseload"})
    load = build_profile(calendar_df, flat_cfg)
    return align_hourly(load, prices)


def _cost_rows(annual: pd.DataFrame, **extra: float) -> pd.DataFrame:
    rows = annual.loc[:, ["year_local", "strategy_id", "volume_mwh", "cost_eur"]].copy()
    for key, value in extra.items():
        rows[key] = value
    return rows


def premium_block(
    aligned: AlignedVolumes,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    cfg: StrategyCfg,
) -> pd.DataFrame:
    """Rerun with ``fixed_premium_eur_mwh`` in {0, 5, 10}.

    Implements: ST-303.
    """
    parts = [
        _cost_rows(
            annual_for_cfg(
                aligned,
                oespi,
                anchors,
                w_peak,
                cfg.model_copy(update={"fixed_premium_eur_mwh": premium}),
            ),
            premium_eur_mwh=premium,
        )
        for premium in PREMIUMS_EUR_MWH
    ]
    return pd.concat(parts, ignore_index=True)


def lock_window_block(
    aligned: AlignedVolumes,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    cfg: StrategyCfg,
) -> pd.DataFrame:
    """Rerun with lock window = all twelve months of Y-1.

    Implements: ST-303.
    """
    cfg_full = cfg.model_copy(update={"lock_window_months": list(LOCK_WINDOW_FULL)})
    return _cost_rows(annual_for_cfg(aligned, oespi, anchors, w_peak, cfg_full))


def flat_profile_block(
    prices: pd.DataFrame,
    calendar_df: pd.DataFrame,
    consumer_cfg: ConsumerProfileCfg,
    oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    cfg: StrategyCfg,
) -> pd.DataFrame:
    """Rerun after ``build_profile(..., profile_name=flat_baseload)`` + align.

    Implements: ST-303, D-14.
    """
    flat = align_flat_baseload(prices, calendar_df, consumer_cfg)
    return _cost_rows(annual_for_cfg(flat, oespi, anchors, w_peak, cfg))


def _resolve_calendar_prices(
    settings: Settings,
    *,
    prices: pd.DataFrame | None,
    calendar_df: pd.DataFrame | None,
    aligned: AlignedVolumes,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if prices is None:
        prices = aligned.hourly
        if not all(col in prices.columns for col in ("ts_utc", "price_at_eur_mwh")):
            prices = load_price_hourly(settings)
    if calendar_df is None:
        calendar_df = calendar_from_prices(prices)
    if calendar_df is None:
        calendar_df = load_calendar(settings)
    return prices, calendar_df


def render_sensitivity_markdown(
    premium: pd.DataFrame, flat: pd.DataFrame, lock: pd.DataFrame
) -> str:
    """Three headings only; ST-502 once; no peak_available block.

    Implements: ST-303, ST-502, D-14.
    """
    return (
        "# Sensitivity matrix (ST-303)\n\n"
        f"{ST502_SENTENCE}\n\n"
        "Each block is a full rerun of the same cost engine with one config "
        "change. There is no fourth sensitivity.\n\n"
        f"{HEADING_PREMIUM}\n\n"
        f"{frame_to_markdown(premium)}\n\n"
        f"{HEADING_FLAT}\n\n"
        f"{frame_to_markdown(flat)}\n\n"
        f"{HEADING_LOCK}\n\n"
        f"{frame_to_markdown(lock)}\n"
    )


def run_sensitivities(
    settings: Settings,
    *,
    aligned: AlignedVolumes,
    monthly_oespi: pd.DataFrame,
    anchors: Anchors,
    w_peak: float,
    cfg: StrategyCfg,
    prices: pd.DataFrame | None = None,
    calendar_df: pd.DataFrame | None = None,
    consumer_cfg: ConsumerProfileCfg | None = None,
) -> str:
    """Write ``reports/strategies/sensitivity_matrix.md``.

    Implements: ST-303, D-14.
    """
    prices, calendar_df = _resolve_calendar_prices(
        settings, prices=prices, calendar_df=calendar_df, aligned=aligned
    )
    consumer_cfg = consumer_cfg or load_consumer_profile()
    body = render_sensitivity_markdown(
        premium_block(aligned, monthly_oespi, anchors, w_peak, cfg),
        flat_profile_block(prices, calendar_df, consumer_cfg, monthly_oespi, anchors, w_peak, cfg),
        lock_window_block(aligned, monthly_oespi, anchors, w_peak, cfg),
    )
    path = strategies_dir(settings) / "sensitivity_matrix.md"
    write_markdown(path, body)
    return body
