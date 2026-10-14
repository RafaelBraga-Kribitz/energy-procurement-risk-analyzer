"""A3 — Volatility regimes: HMM + GARCH complement (SPEC-04 A3).

Basis series: DAILY arithmetic differences of the base price,
``d_t = price_base(t) − price_base(t−1)`` in EUR/MWh — NOT log returns, because
prices can be ≤ 0 (trap T-3).

- AN-301 realized volatility: rolling 30-day std of ``d_t`` with the price.
- AN-302 HMM: GaussianHMM(3, 'full', n_iter=500) on z-scored ``d_t``, ten
  restarts ``random_state=42..51``, best log-likelihood kept, states labelled
  calm/elevated/crisis by ascending state std.
- AN-303 GARCH(1,1), constant mean, on ``d_t`` (rescaled by 1/10 only if the
  optimizer flags the scale); persistence α+β to SSOT, reported as-is.
- AN-304 sanity gate (M5 exit): ≥ 70 % of 2021-09-01..2023-06-30 days in the
  top-2 states, ≥ 60 % of 2019 days calm. A failure raises; widening needs an ADR.

The daily regime labels are written to ``data/processed/regimes_daily.parquet``
for SPEC-05 ST-401 step 4 (no-crisis bootstrap pool).

Implements: AN-301..304.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from arch import arch_model
from arch.univariate.base import DataScaleWarning  # type: ignore[attr-defined]
from hmmlearn.hmm import GaussianHMM

from epra.analytics._shared import analytics_dir, md_table, query, write_markdown
from epra.common.config import Settings, resolve_repo_path
from epra.common.provenance import is_fixture_run
from epra.common.ssot import SsotRow, write_ssot_rows
from epra.report.figure import new_figure, save_figure
from epra.report.style import OKABE_ITO

DAILY_SQL = """
select
    fpd.date_local,
    fpd.price_base_eur_mwh
from marts.fct_price_daily as fpd
where fpd.price_base_eur_mwh is not null
order by fpd.date_local
"""

REGIME_LABELS = ("calm", "elevated", "crisis")
REGIME_COLORS = {
    "calm": OKABE_ITO["bluish_green"],
    "elevated": OKABE_ITO["orange"],
    "crisis": OKABE_ITO["vermillion"],
}
HMM_SEEDS = range(42, 52)  # AN-302: 10 restarts
ROLLING_DAYS = 30  # AN-301
GARCH_RESCALE = 10.0  # AN-303
CRISIS_WINDOW = (date(2021, 9, 1), date(2023, 6, 30))  # AN-304
CRISIS_MIN_SHARE = 0.70  # AN-304
CALM_YEAR = 2019  # AN-304
CALM_MIN_SHARE = 0.60  # AN-304
REGIMES_FILE = "regimes_daily.parquet"


class RegimeGateFailure(RuntimeError):
    """AN-304 failed: investigate standardization/restarts; never widen silently."""


@dataclass(frozen=True)
class GateResult:
    """AN-304 shares and verdict."""

    crisis_top2_share: float
    calm_2019_share: float

    @property
    def passed(self) -> bool:
        return self.crisis_top2_share >= CRISIS_MIN_SHARE and self.calm_2019_share >= CALM_MIN_SHARE


def daily_differences(daily: pd.DataFrame) -> pd.DataFrame:
    """``d_t`` in EUR/MWh (arithmetic, T-3) and the 30-day realized vol (AN-301)."""
    out = daily.assign(date_local=pd.to_datetime(daily["date_local"]))
    out["d_t"] = out["price_base_eur_mwh"].diff()
    out["realized_vol"] = out["d_t"].rolling(ROLLING_DAYS).std()
    return out.dropna(subset=["d_t"]).reset_index(drop=True)


def fit_hmm(d_t: np.ndarray) -> np.ndarray:
    """Best-of-ten seeded GaussianHMM; returns labels ordered by state std.

    Implements: AN-302, AN-705 (fixed seeds ⇒ exact determinism).
    """
    z = ((d_t - d_t.mean()) / d_t.std()).reshape(-1, 1)
    best: GaussianHMM | None = None
    best_ll = -np.inf
    for seed in HMM_SEEDS:
        model = GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=seed)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(z)
        ll = model.score(z)
        if ll > best_ll:
            best, best_ll = model, ll
    assert best is not None
    states = best.predict(z)
    order = np.argsort(np.sqrt(best.covars_.reshape(3)))
    rank = {int(state): idx for idx, state in enumerate(order)}
    return np.array([REGIME_LABELS[rank[int(s)]] for s in states])


def fit_garch(d_t: pd.Series) -> tuple[float, float, pd.Series, float]:
    """GARCH(1,1) const mean: (alpha, beta, conditional vol in EUR/MWh, scale).

    Implements: AN-303.
    """
    scale = 1.0
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        res = arch_model(d_t, mean="Constant", vol="GARCH", p=1, q=1, rescale=False).fit(disp="off")
    if any(issubclass(w.category, DataScaleWarning) for w in caught):
        scale = GARCH_RESCALE
        res = arch_model(d_t / scale, mean="Constant", vol="GARCH", p=1, q=1, rescale=False).fit(
            disp="off"
        )
    params = res.params
    cond_vol = pd.Series(np.asarray(res.conditional_volatility) * scale, index=d_t.index)
    return float(params["alpha[1]"]), float(params["beta[1]"]), cond_vol, scale


def regime_gate(frame: pd.DataFrame) -> GateResult:
    """AN-304 shares on the labelled daily frame."""
    dates = frame["date_local"].dt.date
    crisis = frame[(dates >= CRISIS_WINDOW[0]) & (dates <= CRISIS_WINDOW[1])]
    calm_year = frame[frame["date_local"].dt.year == CALM_YEAR]
    top2 = crisis["regime"].isin(["elevated", "crisis"]).mean() if len(crisis) else 0.0
    calm = (calm_year["regime"] == "calm").mean() if len(calm_year) else 0.0
    return GateResult(float(top2), float(calm))


def regime_stats(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-regime occupancy %, mean |d_t| and mean price level (AN-302)."""
    stats = frame.groupby("regime").agg(
        days=("d_t", "size"),
        mean_abs_d_t=("d_t", lambda s: s.abs().mean()),
        mean_price=("price_base_eur_mwh", "mean"),
    )
    stats = stats.reindex(list(REGIME_LABELS)).dropna(how="all")
    stats.insert(1, "occupancy_pct", 100.0 * stats["days"] / stats["days"].sum())
    return stats.reset_index().astype({"days": int})


def _realized_vol_chart(frame: pd.DataFrame, settings: Settings) -> None:
    fig, ax = new_figure()
    ax.plot(
        frame["date_local"],
        frame["price_base_eur_mwh"],
        color="#333333",
        lw=0.9,
        label="Daily base price",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Daily base price (EUR/MWh)")
    ax2 = ax.twinx()
    ax2.plot(
        frame["date_local"],
        frame["realized_vol"],
        color=OKABE_ITO["vermillion"],
        lw=1.4,
        label="30-day realized volatility",
    )
    ax2.set_ylabel("Std of daily price change, 30 days (EUR/MWh)")
    ax2.spines["right"].set_visible(True)
    fig.legend(loc="upper left", bbox_to_anchor=(0.06, 0.86), frameon=False)
    save_figure(
        fig,
        analytics_dir(settings) / "a3_realized_vol.png",
        title="Volatility exploded with the price level in 2022 and has not fully normalized",
        subtitle="AT daily base price (left) and 30-day realized volatility of daily changes "
        "(right)",
        fixture=is_fixture_run(settings),
    )


def _regime_chart(frame: pd.DataFrame, settings: Settings) -> None:
    fig, ax = new_figure()
    top = float(frame["price_base_eur_mwh"].max()) * 1.05
    for label in REGIME_LABELS:
        mask = (frame["regime"] == label).to_numpy()
        ax.fill_between(
            frame["date_local"],
            0,
            top,
            where=mask,
            step="mid",
            color=REGIME_COLORS[label],
            alpha=0.25,
            lw=0,
            label=f"{label} regime",
        )
    ax.plot(
        frame["date_local"],
        frame["price_base_eur_mwh"],
        color="#222222",
        lw=0.9,
        label="Daily base price",
    )
    ax.set_ylim(min(0.0, float(frame["price_base_eur_mwh"].min()) * 1.05), top)
    ax.set_xlabel("Date")
    ax.set_ylabel("Daily base price (EUR/MWh)")
    ax.legend(ncol=4, frameon=False, loc="upper left")
    save_figure(
        fig,
        analytics_dir(settings) / "a3_regimes.png",
        title="A hidden-Markov model separates calm, elevated and crisis volatility regimes",
        subtitle="3-state Gaussian HMM on daily price changes (best of 10 seeded restarts)",
        fixture=is_fixture_run(settings),
    )


def _garch_chart(
    frame: pd.DataFrame, cond_vol: pd.Series, scale: float, settings: Settings
) -> None:
    fig, ax = new_figure()
    ax.plot(
        frame["date_local"],
        cond_vol.to_numpy(),
        color=OKABE_ITO["blue"],
        lw=1.0,
        label="GARCH(1,1) conditional volatility",
    )
    ax.plot(
        frame["date_local"],
        frame["realized_vol"],
        color=OKABE_ITO["vermillion"],
        lw=1.4,
        label="30-day realized volatility",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Volatility of daily price change (EUR/MWh)")
    ax.legend(frameon=False)
    note = f" (fitted on d_t/{scale:.0f}, shown rescaled)" if scale != 1.0 else ""
    save_figure(
        fig,
        analytics_dir(settings) / "a3_garch_vs_realized.png",
        title="GARCH and realized volatility tell the same story: shocks persist",
        subtitle=f"GARCH(1,1) conditional std vs 30-day realized std{note}",
        fixture=is_fixture_run(settings),
    )


def interpretation(stats: pd.DataFrame, gate: GateResult, persistence: float) -> str:
    """AN-302/303 paragraph from the computed numbers."""
    price = dict(zip(stats["regime"], stats["mean_price"].astype(float), strict=True))
    crisis_price = price.get("crisis", float("nan"))
    calm_price = price.get("calm", float("nan"))
    integrated = (
        "at or above one, i.e. near-integrated: shocks effectively do not decay"
        if persistence >= 1.0
        else "close to one, so a volatility shock decays only slowly"
    )
    return (
        "## Interpretation\n\n"
        f"The three-state model assigns {gate.crisis_top2_share:.0%} of the days between "
        f"September 2021 and June 2023 to the elevated or crisis state and "
        f"{gate.calm_2019_share:.0%} of 2019 to the calm state, so the regimes line up with "
        f"what market participants lived through. Crisis days averaged a base price of "
        f"{crisis_price:.1f} EUR/MWh against {calm_price:.1f} EUR/MWh in calm days: in this "
        f"market high prices and high volatility arrive together. The GARCH persistence "
        f"α+β is {persistence:.3f}, {integrated}. For procurement this means risk is "
        f"clustered: a buyer exposed to spot does not face independent good and bad days "
        f"but long stretches of turbulence, which is why the forward-risk simulation draws "
        f"whole historical months together and reports a no-crisis variant alongside the "
        f"unconditional one."
    )


def regimes_path(settings: Settings) -> Path:
    """``data/processed/regimes_daily.parquet`` (input to ST-401 step 4)."""
    return resolve_repo_path(settings.paths.data_processed) / REGIMES_FILE


def run(settings: Settings) -> GateResult:
    """Produce all A3 artifacts; raise on an AN-304 failure (AN-702).

    Implements: AN-301..304, AN-703, AN-705.
    """
    frame = daily_differences(query(settings, DAILY_SQL))
    frame["regime"] = fit_hmm(frame["d_t"].to_numpy())
    alpha, beta, cond_vol, scale = fit_garch(frame["d_t"])
    gate = regime_gate(frame)
    stats = regime_stats(frame)

    _realized_vol_chart(frame, settings)
    _regime_chart(frame, settings)
    _garch_chart(frame, cond_vol, scale, settings)
    path = regimes_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame[["date_local", "regime"]].to_parquet(path, index=False)

    verdict = "PASS" if gate.passed else "FAIL"
    write_markdown(
        settings,
        "a3_regime_stats.md",
        "A3 — Volatility regimes",
        [
            "Basis: daily arithmetic change of the AT base price, d_t in EUR/MWh (not log "
            "returns — prices can be ≤ 0). HMM fitted on z-scored d_t.",
            "",
            md_table(
                stats.rename(
                    columns={
                        "mean_abs_d_t": "mean_abs_d_t_eur_mwh",
                        "mean_price": "mean_price_eur_mwh",
                    }
                )
            ),
            "",
            f"GARCH(1,1): α = {alpha:.4f}, β = {beta:.4f}, persistence α+β = "
            f"{alpha + beta:.4f}" + (f" (fitted on d_t/{scale:.0f})." if scale != 1.0 else "."),
            "",
            f"**AN-304 sanity gate: {verdict}** — top-2 share 2021-09..2023-06 = "
            f"{gate.crisis_top2_share:.1%} (≥ {CRISIS_MIN_SHARE:.0%}); calm share 2019 = "
            f"{gate.calm_2019_share:.1%} (≥ {CALM_MIN_SHARE:.0%}).",
            "",
            interpretation(stats, gate, alpha + beta),
        ],
    )
    write_ssot_rows(
        [
            SsotRow(
                "garch_persistence",
                round(alpha + beta, 6),
                "ratio",
                "VERIFIED",
                "analytics/regimes.py",
            )
        ],
        "analytics_a3",
        settings,
    )
    if not gate.passed:
        raise RegimeGateFailure(
            f"AN-304 failed: top-2 share {gate.crisis_top2_share:.1%}, "
            f"calm-2019 share {gate.calm_2019_share:.1%} — investigate, do not widen"
        )
    return gate
