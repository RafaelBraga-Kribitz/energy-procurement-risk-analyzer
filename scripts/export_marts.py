"""Export marts and results to exports/*.csv for Power BI (SPEC-02 §7, DM-070).

Power BI reads ONLY these files — never DuckDB — so the dashboard can be rebuilt
by anyone without the warehouse. CSVs are UTF-8, ISO dates, ``.`` decimal,
header row, written by DuckDB ``COPY`` from explicit-column SQL.

SPEC-02 §7 files: price_daily, price_monthly, generation_monthly,
procurement_cost_monthly, strategy_annual_summary, forward_risk_summary.
ADR-020 additions for the Power BI build kit: spread_monthly (RP-402),
dim_strategy,
data_quality_monthly, forward_paths (distribution visual), ssot (cards show
SSOT values only, A-6) and provenance (fixture vs real data flag, ADR-018).

Implements: DM-070, SPEC-02 §7, ADR-020 §4.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from epra.common.config import Settings, load_settings, resolve_repo_path
from epra.common.db import connect
from epra.common.provenance import is_fixture_run
from epra.common.ssot import read_ssot_rows
from epra.report.style import STRATEGY_COLORS, STRATEGY_LABELS

#: DM-070 export contract: file stem → exact column list (tested).
EXPORT_CONTRACT: dict[str, list[str]] = {
    "price_daily": [
        "date_local",
        "price_base_eur_mwh",
        "price_peak_eur_mwh",
        "price_min",
        "price_max",
        "price_std",
        "n_negative_hours",
        "tavg_c",
        "hdd_18",
        "cdd_22",
    ],
    "price_monthly": [
        "year_local",
        "month_local",
        "price_base_eur_mwh",
        "price_peak_eur_mwh",
        "price_offpeak_eur_mwh",
        "n_negative_hours",
        "oespi_base",
        "oespi_peak",
    ],
    "generation_monthly": [
        "year_local",
        "month_local",
        "psr_type",
        "psr_name",
        "gen_gwh",
        "share_of_total",
    ],
    "procurement_cost_monthly": [
        "year_local",
        "month_local",
        "strategy_id",
        "volume_mwh",
        "cost_eur",
        "unit_cost_eur_mwh",
    ],
    "strategy_annual_summary": [
        "year",
        "strategy_id",
        "volume_mwh",
        "cost_eur",
        "unit_cost_eur_mwh",
        "delta_vs_min_eur",
        "rank",
    ],
    "forward_risk_summary": ["variant", "strategy_id", "mean", "std", "p5", "p50", "p95", "cvar95"],
    "spread_monthly": ["year_local", "month_local", "spread_mean_eur_mwh", "share_at_above_de_pct"],
    "dim_strategy": [
        "strategy_id",
        "strategy_name",
        "strategy_label",
        "sort_order",
        "color_hex",
        "description",
    ],
    "data_quality_monthly": [
        "year_local",
        "month_local",
        "expected_hours",
        "priced_hours_at",
        "priced_hours_delu",
        "load_hours",
        "weather_days",
        "days_in_month",
        "coverage_at_pct",
        "n_dst_days",
        "n_hours_from_pt15m",
        "resolution",
        "n_negative_hours",
        "has_oespi",
    ],
    "forward_paths": ["variant", "path", "strategy_id", "cost_eur"],
    "ssot": ["key", "value", "unit", "tag", "produced_by"],
    "provenance": ["is_fixture", "data_last_month", "generated_on"],
}


def _label_rows() -> str:
    """SQL VALUES rows carrying the reader labels and colours (RP-704) to Power BI."""
    return ", ".join(
        f"('{sid}', '{STRATEGY_LABELS[sid]}', {i}, '{STRATEGY_COLORS[sid]}')"
        for i, sid in enumerate(STRATEGY_LABELS, start=1)
    )


def export_sql(settings: Settings) -> dict[str, str]:
    """One explicit-column SELECT per export (the SPEC-02 §7 table, in SQL).

    Implements: SPEC-02 §7.
    """
    processed = resolve_repo_path(settings.paths.data_processed).as_posix()

    def cols(name: str) -> str:
        return ", ".join(EXPORT_CONTRACT[name])

    return {
        "price_daily": f"select {cols('price_daily')} from marts.fct_price_daily "
        "where price_base_eur_mwh is not null order by date_local",
        "price_monthly": f"select {cols('price_monthly')} from marts.fct_price_monthly "
        "order by year_local, month_local",
        "generation_monthly": f"select {cols('generation_monthly')} "
        "from marts.fct_generation_monthly order by year_local, month_local, psr_type",
        "procurement_cost_monthly": f"select {cols('procurement_cost_monthly')} "
        "from marts.fct_procurement_cost_monthly order by year_local, month_local, strategy_id",
        "strategy_annual_summary": f"select {cols('strategy_annual_summary')} "
        f"from read_parquet('{processed}/strategy_annual_summary.parquet') "
        "order by year, strategy_id",
        "forward_risk_summary": f"select {cols('forward_risk_summary')} "
        f"from read_parquet('{processed}/forward_risk_summary.parquet') "
        "order by variant, strategy_id",
        "spread_monthly": "select year_local, month_local, "
        "avg(spread_at_delu_eur_mwh) as spread_mean_eur_mwh, "
        "100.0 * avg(case when spread_at_delu_eur_mwh > 0 then 1.0 else 0.0 end) "
        "as share_at_above_de_pct from marts.fct_price_hourly "
        "where spread_at_delu_eur_mwh is not null "
        "group by year_local, month_local order by year_local, month_local",
        "dim_strategy": "with labels (strategy_id, strategy_label, sort_order, color_hex) as "
        f"(values {_label_rows()}) select ds.strategy_id, ds.strategy_name, "
        "labels.strategy_label, labels.sort_order, labels.color_hex, ds.description "
        "from marts.dim_strategy as ds inner join labels "
        "on ds.strategy_id = labels.strategy_id order by labels.sort_order",
        "data_quality_monthly": f"select {cols('data_quality_monthly')} "
        "from marts.fct_data_quality_monthly order by year_local, month_local",
        "forward_paths": f"select {cols('forward_paths')} "
        f"from read_parquet('{processed}/forward_paths.parquet') "
        "order by variant, strategy_id, path",
    }


def _write_small_tables(settings: Settings, out: Path) -> None:
    """``ssot.csv`` (from the SSOT input rows) and ``provenance.csv``."""
    rows = read_ssot_rows(settings)
    rows[EXPORT_CONTRACT["ssot"]].to_csv(out / "ssot.csv", index=False)
    last = rows.loc[rows["key"] == "data_last_month", "value"]
    provenance = {
        "is_fixture": [is_fixture_run(settings)],
        "data_last_month": [last.iloc[0] if not last.empty else ""],
        "generated_on": [date.today().isoformat()],
    }
    pd.DataFrame(provenance).to_csv(out / "provenance.csv", index=False)


def export_all(settings: Settings) -> list[Path]:
    """Write every export; returns the written paths.

    Implements: DM-070, SPEC-02 §7.
    """
    out = resolve_repo_path(settings.paths.exports)
    out.mkdir(parents=True, exist_ok=True)
    con = connect(settings, read_only=True)
    written = []
    try:
        for name, sql in export_sql(settings).items():
            path = out / f"{name}.csv"
            con.execute(f"copy ({sql}) to '{path.as_posix()}' (header, delimiter ',')")
            written.append(path)
    finally:
        con.close()
    _write_small_tables(settings, out)
    return [*written, out / "ssot.csv", out / "provenance.csv"]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python scripts/export_marts.py`` (``make export``).

    Implements: DM-070.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    paths = export_all(load_settings())
    print(f"OK: {len(paths)} CSVs -> {paths[0].parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
