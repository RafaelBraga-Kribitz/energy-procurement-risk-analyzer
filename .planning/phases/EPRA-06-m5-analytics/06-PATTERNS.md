# Phase 6: M5 Analytics - Pattern Map

**Mapped:** 2026-09-02
**Files analyzed:** analytics stubs, `epra.common.db`, `epra.report.style`/`format`, `warehouse.report.main`, `consumer.profile.main`, `fct_price_hourly.sql`, Makefile, stub tests
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Closest Analog | Match Quality |
|---|---|---|---|
| `src/epra/analytics/_kit.py` | shared I/O + SQL loaders | `epra.warehouse.report` (read-only connect) + `profile._atomic_write_parquet` | exact |
| `src/epra/analytics/__main__.py` / `cli.py` | orchestrator A1→A2→A4→A3 | `python -m epra.consumer.profile` | exact |
| `descriptive.py` / `spread.py` / `weather.py` / `regimes.py` | domain `run` + pure functions | stubs already named `run(settings)` | exact |
| `tests/unit/test_analytics_*.py` | synthetic frames + chart artists | `test_profile.py` (pure functions) + matplotlib object asserts (new) | close |
| `Makefile` `analyze:` | operator | `profile:` one-liner | exact |
| `tests/unit/test_stubs_fail_loudly.py` | drop M5 rows as `run` lands | file's own comment | exact |
| `ssot_inputs_analytics.parquet` writer | producer file | `write_profile_outputs` SSOT block | exact |

## Pattern Assignments

### Mart load (warehouse.report)

```python
con = connect(settings, read_only=True)
try:
    frame = con.execute("select ... from marts.fct_price_hourly").fetchdf()
finally:
    con.close()
if frame.empty:
    raise RuntimeError("SQL returned empty: ...")
```

Pin SQL strings as module constants so the error can reprint them.

### PNG + RP-702

```python
import matplotlib
matplotlib.use("Agg")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
# ...
fig.text(0.01, 0.01, SOURCE_NOTE, fontsize=8)
fig.text(0.99, 0.01, "VERIFIED", ha="right", fontsize=8)
fig.savefig(path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
```

Tests: `ax.get_xlabel()`, `fig.texts` joined, `fig.get_size_inches()`.

### SSOT producer (profile)

Same columns; `tag="VERIFIED"`; atomic replace of the whole analytics producer file at the end of `python -m epra.analytics` (modules append in-memory rows; kit writes once) **or** each module read-modify-write. Recommendation: in-memory `list[dict]` on a small context object passed through `run`, `__main__` writes once — avoids torn parquet if A3 fails.

### HMM

```python
os.environ["OMP_NUM_THREADS"] = "1"  # and MKL/OPENBLAS/NUMEXPR
# then GaussianHMM(... random_state=seed).fit(X)
```

`X` shape `(n_days, 1)` float64 z-scored `d_t`. Relabel by `np.argsort(std_per_state)`.

### AN-304 skip

```python
if coverage_incomplete:
    pytest.skip("AN-304 needs complete 2019 and 2021-09-01..2023-06-30")
```

`regimes.check_an304` returns a result object; CLI maps `passed=False` to exit 1; missing coverage maps to skip in pytest and to a logged skip in CLI **only when years are absent** — if years are present and fractions fail, exit 1.

### Makefile

```make
analyze:
	$(UV) run python -m epra.analytics
```

### Stub deletion

Remove M5 `descriptive.run` / `spread.run` / `regimes.run` / `weather.run` rows when those functions no longer raise — T5.02/03/04/05 commits respectively, or all at T5.07 if earlier plans keep `run` raising until wired. Prefer delete in the same commit that implements each `run()`.
