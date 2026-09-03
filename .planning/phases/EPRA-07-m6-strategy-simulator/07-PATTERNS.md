# Phase 7: M6 Strategy Simulator - Pattern Map

**Mapped:** 2026-09-03
**Files analyzed:** strategy stubs, `analytics/_kit.py`, `analytics/__main__.py`, `consumer/profile.py`, `regimes.december_regime`, `config.StrategyCfg`, `dbt` procurement source, `Makefile` simulate/ssot, `test_stubs_fail_loudly.py`, `bootstrap_fixture_warehouse.py` procurement writer
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Closest Analog | Match Quality |
|---|---|---|---|
| `src/epra/strategies/align.py` (or `_data.py`) | mart SQL + ST-101 | `analytics/_kit.py` loaders | exact |
| `calibration.py` | anchors dataclass | stub + ST-202 docstring | exact |
| `retrospective.py` | S1–S4 + `run`/`main` | `descriptive.run` + dispatch | exact |
| `forward_risk.py` | cells + simulate + summarize | 03_MODULES pins | exact |
| `epra/report/ssot.py` | concat + markdown | `write_ssot_rows` + kit markdown | close |
| `epra/report/ssot_check.py` | parse docs vs SSOT | new (stdlib re + Decimal) | new |
| `scripts/generate_ssot.py` | thin CLI | `scripts/` table in 03_MODULES | exact |
| `scripts/check_ssot_consistency.py` | thin CLI | same | exact |
| `scripts/generate_golden_metrics.py` | dirty-tree guard + JSON | EN-072 spirit / LP-040 writer | close |
| `tests/unit/test_strategies_*.py` | synthetic frames | `test_analytics_a1.py` | exact |
| `Makefile` `simulate:` / `ssot:` | operator | `analyze:` | exact |
| `docs/ADR/ADR-014..016` | gap adoption | ADR-013 | exact |
| dual-write parquet | replace stand-in | M4 `consumer_load_hourly.parquet` | close |
| `test_stubs_fail_loudly.py` | drop M6 rows as `run` lands | file's own comment | exact |

## Pattern Assignments

### Mart load (kit)

```python
con = connect(settings, read_only=True)
try:
    frame = con.execute(SQL).fetchdf()
finally:
    con.close()
if frame.empty:
    raise RuntimeError(f"SQL returned empty: {SQL}")
```

Pin SQL constants. Join in pandas, not in a giant SQL string, so unit tests inject frames.

### Aligner (ST-101)

```python
hourly = load.merge(prices, on="ts_utc", how="inner")
n_null = int(hourly["price_at_eur_mwh"].isna().sum())
hourly = hourly.dropna(subset=["price_at_eur_mwh"])
# monthly volume = groupby year_local, month_local sum load_mwh
```

`AlignedVolumes` frozen dataclass: `hourly: pd.DataFrame`, `monthly: pd.DataFrame`, `dropped_hours: int`.

### Dispatch table (not classes)

```python
COSTERS = {
    "S1": cost_s1_monthly,
    "S2": cost_s2_monthly,
    "S3": cost_s3_monthly,
    "S4_30": lambda h=0.30: cost_s4_monthly(h),
    ...
}
```

Prefer `cost_s4(aligned, p_s3_by_year, h)` once.

### PNG + ST-502

Reuse `analytics._kit.save_png` **or** a strategies wrapper that also `fig.text`s `ST502_SENTENCE`. Do not duplicate FIGSIZE/DPI/hex. Tests join `fig.texts`.

### SSOT producer (strategies)

Same columns as profile/analytics. `tag` is CALIBRATED (anchors, retrospective euros) or SIMULATED (forward P95/CVaR). Atomic write `ssot_inputs_strategies.parquet`.

### Assembler (T6.08)

```python
parts = [read(p) for p in sorted(processed.glob("ssot_inputs_*.parquet"))]
frame = pd.concat(parts).drop_duplicates("key", keep="last")  # last writer wins only if duplicate — prefer raise on duplicate keys
```

Raise on duplicate keys (GV-302 exactly once). Sort by key. `updated_at = max(mtime)` ISO-8601 UTC.

### Dual-write (D-05)

```python
# wipe glob dir so stand-in monthly files cannot mix
shutil.rmtree(proc / "procurement_cost_monthly", ignore_errors=True)
atomic_parquet(frame, proc / "strategy_costs_monthly.parquet")
dest = proc / "procurement_cost_monthly" / "strategy_costs_monthly.parquet"
# copy bytes or second atomic write of the same frame
```

year/month as int64.

### Makefile

```make
simulate:
	$(UV) run python -m epra.strategies.retrospective
	$(UV) run python -m epra.strategies.forward_risk

ssot:
	$(UV) run python scripts/generate_ssot.py
```

Missing warehouse: each CLI exits 1 like analytics `__main__`.

### Stub deletion

Remove `calibration.compute_anchors` / `retrospective.run|main` / `forward_risk.run|main` rows in the commit that un-stubs each. Keep M7 charts stub.

### Quantile / CVaR (ADR-015)

```python
p95 = float(np.quantile(costs, 0.95, method="linear"))
k = int(np.ceil(0.05 * n))
cvar = float(np.sort(costs)[-k:].mean())
```

### Half-up (ADR-016)

```python
from decimal import Decimal, ROUND_HALF_UP
q = Decimal("1").scaleb(-d)  # 10**(-d)
rounded = Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP)
```

### Golden script

Refuse if `git status --porcelain` non-empty. Write `tests/golden/strategy_annual_summary.json` from the synthetic engine helper used by tests — never from a fixture warehouse.

### HMM reuse

```python
from epra.analytics.regimes import daily_diff, december_regime, fit_hmm
```

Do not copy GaussianHMM construction.
