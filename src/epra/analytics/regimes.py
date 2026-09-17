"""A3 — Volatility regimes: HMM + realized vol (SPEC-04 AN-301..304).

``d_t`` is the arithmetic daily difference of ``price_base_eur_mwh`` (not log).
HMM: GaussianHMM(3, full, n_iter=500), seeds 42..51, max LL, lower seed on
tie, states labeled calm/elevated/crisis by ascending std. GARCH overlay is
06-06.

Implements: AN-301, AN-302, AN-304, AN-705, D-06, D-09, D-10, T-3.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Final, Literal, cast

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from matplotlib import pyplot as plt
from matplotlib.dates import date2num
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from epra.analytics._kit import (
    analytics_dir,
    frame_to_markdown,
    load_price_daily,
    save_png,
    write_markdown,
)
from epra.common.config import Settings
from epra.report.format import format_eur_mwh, format_pct
from epra.report.style import FIGSIZE, OKABE_ITO

logger = logging.getLogger(__name__)

PRODUCED_BY: Final = "epra.analytics.regimes"
PRICE_COL: Final = "price_base_eur_mwh"
LABELS: Final[tuple[str, ...]] = ("calm", "elevated", "crisis")
RESTART_SEEDS: Final[tuple[int, ...]] = tuple(range(42, 52))
CRISIS_WINDOW_START: Final = date(2021, 9, 1)
CRISIS_WINDOW_END: Final = date(2023, 6, 30)
AN304_TOP2_MIN: Final = 0.70
AN304_CALM_2019_MIN: Final = 0.60
COVERAGE_FRACTION: Final = 0.90
REGIME_COLORS: Final[dict[str, str]] = {
    "calm": OKABE_ITO["bluish_green"],
    "elevated": OKABE_ITO["yellow"],
    "crisis": OKABE_ITO["vermillion"],
}

An304Status = Literal["pass", "fail", "skip"]
RegimeName = Literal["calm", "elevated", "crisis"]


@dataclass(frozen=True)
class HmmFit:
    """Best-of-10-restart Gaussian HMM on z-scored ``d_t``.

    State 0 in ``state_sequence`` is calm (lowest std). Implements: AN-302.
    """

    state_sequence: np.ndarray
    labels: np.ndarray
    state_order_by_std: tuple[int, ...]
    log_likelihood: float
    restart_seed_used: int
    n_components: int
    covariance_type: str
    n_iter: int


@dataclass(frozen=True)
class An304Result:
    """AN-304 gate: skip if coverage incomplete; fail closed otherwise.

    Implements: AN-304, D-06.
    """

    status: An304Status
    reason: str
    crisis_window_top2_share: float | None
    calm_2019_share: float | None


def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _as_float(value: object) -> float:
    return float(cast(Any, value))


def _mpl_x(ts: pd.Timestamp) -> float:
    convert: Any = date2num
    return float(convert(ts.to_pydatetime()))


def _pin_blas_threads() -> None:
    """Single-thread BLAS before constructing GaussianHMM (AN-705).

    Implements: D-09.
    """
    for key in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[key] = "1"


def daily_diff(daily: pd.DataFrame) -> pd.DataFrame:
    """Arithmetic first difference of base price by ``date_local``.

    Implements: AN-301, AN-302, T-3.
    """
    if PRICE_COL not in daily.columns or "date_local" not in daily.columns:
        raise ValueError("daily frame needs date_local and price_base_eur_mwh")
    ordered = daily.copy()
    ordered["date_local"] = pd.to_datetime(ordered["date_local"]).dt.normalize()
    ordered = ordered.sort_values("date_local").drop_duplicates("date_local")
    if ordered.empty:
        empty = ordered.iloc[0:0].copy()
        empty["d_t"] = pd.Series(dtype="float64")
        return empty
    idx = pd.date_range(ordered["date_local"].min(), ordered["date_local"].max(), freq="D")
    base = ordered.set_index("date_local")[PRICE_COL].astype("float64").reindex(idx)
    out = pd.DataFrame({PRICE_COL: base, "d_t": base.diff()})
    out.index.name = "date_local"
    out = out.reset_index()
    return out.dropna(subset=["d_t", PRICE_COL]).reset_index(drop=True)


def zscore(values: np.ndarray) -> np.ndarray:
    """Full-sample z-score of ``d_t``.

    Implements: AN-302.
    """
    arr = np.asarray(values, dtype=np.float64)
    mean = float(arr.mean())
    std = float(arr.std(ddof=0))
    if std == 0.0:
        return np.zeros_like(arr)
    return (arr - mean) / std


def _state_stds(x: np.ndarray, states: np.ndarray, n_states: int) -> np.ndarray:
    stds = np.zeros(n_states, dtype=np.float64)
    for k in range(n_states):
        sl = x[states == k]
        stds[k] = float(sl.std(ddof=0)) if sl.size else np.inf
    return stds


def fit_hmm(dt_std: np.ndarray) -> HmmFit:
    """Ten seeded restarts; keep max LL, lower seed on a tie; remap by std.

    Implements: AN-302, AN-705, D-09.
    """
    _pin_blas_threads()
    x = np.asarray(dt_std, dtype=np.float64).reshape(-1, 1)
    best_model: GaussianHMM | None = None
    best_ll = -np.inf
    best_seed = RESTART_SEEDS[-1]
    for seed in RESTART_SEEDS:
        model = GaussianHMM(
            n_components=3,
            covariance_type="full",
            n_iter=500,
            random_state=seed,
        )
        model.fit(x)
        ll = float(model.score(x))
        if best_model is None or ll > best_ll or (ll == best_ll and seed < best_seed):
            best_model = model
            best_ll = ll
            best_seed = seed
    assert best_model is not None
    raw = np.asarray(best_model.predict(x), dtype=np.int64)
    stds = _state_stds(x.reshape(-1), raw, 3)
    order = tuple(int(i) for i in np.argsort(stds))
    remap = {old: new for new, old in enumerate(order)}
    remapped = np.array([remap[int(s)] for s in raw], dtype=np.int64)
    labels = np.array(LABELS, dtype=object)[remapped]
    return HmmFit(
        state_sequence=remapped,
        labels=labels,
        state_order_by_std=order,
        log_likelihood=best_ll,
        restart_seed_used=best_seed,
        n_components=3,
        covariance_type="full",
        n_iter=500,
    )


def realized_vol(d_t: pd.Series, window: int = 30) -> pd.Series:
    """Rolling std of arithmetic ``d_t``.

    Implements: AN-301.
    """
    return d_t.astype("float64").rolling(window=window, min_periods=window).std()


def _in_window(dates: pd.Series, start: date, end: date) -> pd.Series:
    d = pd.to_datetime(dates)
    return (d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))


def _coverage_ok(dates: pd.Series, start: date, end: date) -> bool:
    needed = (end - start).days + 1
    n = int(_in_window(dates, start, end).sum())
    return n >= COVERAGE_FRACTION * needed


def check_an304(dates: pd.Series, labels: pd.Series) -> An304Result:
    """Skip if 2019 or crisis window incomplete; else fail closed on 70/60.

    Implements: AN-304, D-06.
    """
    dates = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
    lab = pd.Series(labels).astype(str).reset_index(drop=True)
    has_2019 = _coverage_ok(dates, date(2019, 1, 1), date(2019, 12, 31))
    has_crisis = _coverage_ok(dates, CRISIS_WINDOW_START, CRISIS_WINDOW_END)
    if not has_2019 or not has_crisis:
        missing = []
        if not has_2019:
            missing.append("2019")
        if not has_crisis:
            missing.append("2021-09-01..2023-06-30")
        return An304Result(
            status="skip",
            reason="AN-304 incomplete coverage: " + ", ".join(missing),
            crisis_window_top2_share=None,
            calm_2019_share=None,
        )
    crisis_mask = _in_window(dates, CRISIS_WINDOW_START, CRISIS_WINDOW_END)
    y2019 = dates.dt.year == 2019
    top2 = lab.isin(["elevated", "crisis"])
    crisis_share = float(top2.loc[crisis_mask].mean())
    calm_share = float((lab.loc[y2019] == "calm").mean())
    ok = crisis_share >= AN304_TOP2_MIN and calm_share >= AN304_CALM_2019_MIN
    reason = (
        f"crisis-window top-2 share={crisis_share:.3f} "
        f"(need {AN304_TOP2_MIN:.2f}); 2019 calm share={calm_share:.3f} "
        f"(need {AN304_CALM_2019_MIN:.2f})"
    )
    return An304Result(
        status="pass" if ok else "fail",
        reason=reason,
        crisis_window_top2_share=crisis_share,
        calm_2019_share=calm_share,
    )


def december_regime(year: int, dates: pd.Series, labels: pd.Series) -> RegimeName:
    """Majority HMM label among December days of ``year`` (calm wins ties).

    Implements: D-10.
    """
    d = pd.to_datetime(dates)
    lab = pd.Series(labels).astype(str)
    mask = (d.dt.year == year) & (d.dt.month == 12)
    if not bool(mask.any()):
        raise ValueError(f"no December {year} days in HMM timeline")
    counts = lab.loc[mask].value_counts().reindex(list(LABELS), fill_value=0)
    best: str = LABELS[0]
    best_n = -1
    for name in LABELS:
        n = _as_int(counts[name])
        if n > best_n:
            best = name
            best_n = n
    return cast(RegimeName, best)


def regime_stats_table(
    frame: pd.DataFrame,
    labels: np.ndarray,
) -> pd.DataFrame:
    """Occupancy, mean |d_t|, mean price level per labeled state.

    Implements: AN-302.
    """
    work = frame.copy()
    work["label"] = labels
    rows: list[dict[str, object]] = []
    n = len(work)
    for name in LABELS:
        sl = work.loc[work["label"] == name]
        rows.append(
            {
                "regime": name,
                "occupancy": (len(sl) / n) if n else float("nan"),
                "mean_abs_d_t": float(sl["d_t"].abs().mean()) if len(sl) else float("nan"),
                "mean_price": float(sl[PRICE_COL].mean()) if len(sl) else float("nan"),
                "n_days": len(sl),
            }
        )
    return pd.DataFrame(rows)


def figure_realized_vol(frame: pd.DataFrame) -> Figure:
    """Base price with twin-axis 30-day realized vol of ``d_t``.

    Implements: AN-301.
    """
    fig, ax_price = plt.subplots(figsize=FIGSIZE)
    dates = pd.to_datetime(frame["date_local"])
    ax_price.plot(
        dates,
        frame[PRICE_COL].astype("float64"),
        color=OKABE_ITO["blue"],
        label="price_base",
    )
    ax_vol = ax_price.twinx()
    ax_vol.plot(
        dates,
        realized_vol(frame["d_t"]),
        color=OKABE_ITO["vermillion"],
        label="rv_30",
        alpha=0.8,
    )
    ax_price.set_xlabel("date_local")
    ax_price.set_ylabel("EUR/MWh")
    ax_vol.set_ylabel("30-day std of d_t (EUR/MWh)")
    ax_price.legend(loc="upper left")
    ax_vol.legend(loc="upper right")
    fig.subplots_adjust(bottom=0.18)
    return fig


def _span_runs(
    dates: pd.Series, labels: np.ndarray
) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    d = list(pd.to_datetime(dates))
    labs = [str(x) for x in labels]
    if not d:
        return []
    runs: list[tuple[pd.Timestamp, pd.Timestamp, str]] = []
    start = d[0]
    current = labs[0]
    for ts, lab in zip(d[1:], labs[1:], strict=True):
        if lab != current:
            runs.append((start, ts, current))
            start = ts
            current = lab
    runs.append((start, d[-1], current))
    return runs


def figure_regimes(frame: pd.DataFrame, labels: np.ndarray) -> Figure:
    """Price line with colored regime bands.

    Implements: AN-302.
    """
    fig, ax = plt.subplots(figsize=FIGSIZE)
    dates = pd.to_datetime(frame["date_local"])
    for start, end, lab in _span_runs(dates, labels):
        ax.axvspan(
            _mpl_x(start),
            _mpl_x(end),
            color=REGIME_COLORS[lab],
            alpha=0.25,
            linewidth=0,
        )
    ax.plot(dates, frame[PRICE_COL].astype("float64"), color=OKABE_ITO["black"], label="price_base")
    ax.set_xlabel("date_local")
    ax.set_ylabel("EUR/MWh")
    ax.legend(
        handles=[Patch(facecolor=REGIME_COLORS[n], alpha=0.25, label=n) for n in LABELS],
        loc="upper left",
    )
    fig.subplots_adjust(bottom=0.18)
    return fig


def _format_regime_md(stats: pd.DataFrame) -> pd.DataFrame:
    out = stats.copy()
    out["occupancy"] = [format_pct(_as_float(v)) if pd.notna(v) else "" for v in out["occupancy"]]
    out["mean_abs_d_t"] = [
        format_eur_mwh(_as_float(v)) if pd.notna(v) else "" for v in out["mean_abs_d_t"]
    ]
    out["mean_price"] = [
        format_eur_mwh(_as_float(v)) if pd.notna(v) else "" for v in out["mean_price"]
    ]
    out["n_days"] = [str(_as_int(v)) for v in out["n_days"]]
    return out


def so_what_paragraph(stats: pd.DataFrame, gate: An304Result, *, seed: int) -> str:
    """Interpretation after the regime table (AN-704). Numbers from stats.

    Implements: AN-302, AN-704, RP-703.
    """
    calm = stats.loc[stats["regime"] == "calm"].iloc[0]
    crisis = stats.loc[stats["regime"] == "crisis"].iloc[0]
    return (
        "So what for a procurement manager. These regimes are estimated on arithmetic "
        "daily differences of the AT base price, not log returns, because day-ahead "
        "prices can be at or below zero and a log would be undefined. Calm occupancy "
        f"is {format_pct(_as_float(calm['occupancy']))} with mean absolute d_t "
        f"{format_eur_mwh(_as_float(calm['mean_abs_d_t']))}; crisis occupancy is "
        f"{format_pct(_as_float(crisis['occupancy']))} with mean absolute d_t "
        f"{format_eur_mwh(_as_float(crisis['mean_abs_d_t']))} and mean price "
        f"{format_eur_mwh(_as_float(crisis['mean_price']))}. The HMM used ten "
        f"restarts (seeds 42-51), kept seed {seed} by maximum log-likelihood with "
        "the lower seed on a tie, and labeled states by ascending within-state "
        "standard deviation (calm, elevated, crisis). AN-304 is a fail-closed "
        "sanity check on 2019 calm occupancy and 2021-09-01 to 2023-06-30 time in "
        f"the top two volatility states; this run status is {gate.status}: {gate.reason}. "
        "A skip is not a pass: fixture warehouses without 2019 cannot green the "
        "gate. December majority state (december_regime) is the input M6 uses for "
        "the no-crisis bootstrap variant, not a forecast."
    )


def render_regime_stats_md(
    stats: pd.DataFrame,
    gate: An304Result,
    *,
    seed: int,
) -> str:
    """Regime table plus AN-704 prose.

    Implements: AN-302, AN-704.
    """
    table = frame_to_markdown(_format_regime_md(stats))
    prose = so_what_paragraph(stats, gate, seed=seed)
    return (
        "# A3 HMM regime stats (AN-302)\n\n"
        "Basis: d_t = price_base_eur_mwh(t) minus price_base_eur_mwh(t-1), arithmetic.\n\n"
        f"{table}\n\n"
        f"{prose}\n"
    )


def run(settings: Settings, *, daily: pd.DataFrame | None = None) -> None:
    """Write AN-301/302 artifacts; AN-304 fail raises. GARCH is 06-06.

    Implements: AN-301, AN-302, AN-304, D-01, D-06.
    """
    frame_in = daily if daily is not None else load_price_daily(settings)
    diffed = daily_diff(frame_in)
    fit = fit_hmm(zscore(diffed["d_t"].to_numpy(dtype=np.float64)))
    stats = regime_stats_table(diffed, fit.labels)
    gate = check_an304(diffed["date_local"], pd.Series(fit.labels))
    if gate.status == "skip":
        logger.warning("%s", gate.reason)
    elif gate.status == "fail":
        raise RuntimeError(f"AN-304 failed: {gate.reason}")
    out = analytics_dir(settings)
    out.mkdir(parents=True, exist_ok=True)
    write_markdown(
        out / "a3_regime_stats.md",
        render_regime_stats_md(stats, gate, seed=fit.restart_seed_used),
    )
    save_png(figure_realized_vol(diffed), out / "a3_realized_vol.png")
    save_png(figure_regimes(diffed, fit.labels), out / "a3_regimes.png")
    logger.info(
        "A3 wrote HMM artifacts under %s seed=%s produced_by=%s",
        out,
        fit.restart_seed_used,
        PRODUCED_BY,
    )
