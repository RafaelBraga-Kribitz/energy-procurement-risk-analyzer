# Phase 5: M4 Consumer Profile - Research

**Researched:** 2026-09-02
**Domain:** Deterministic vectorized pandas load-profile construction (calendar spine + YAML cfg → hourly MWh), atomic processed-parquet I/O, dbt source-path realignment from M3 monthly stand-in glob to SPEC-03 single file
**Confidence:** HIGH for project facts (read from committed files this session). HIGH for pandas/numpy indexing patterns already used in `calendar.py` / ingest tests. No new third-party libraries. No MCP doc tools required — this phase does not add packages.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `calendar_df` is the ING-110 frame (`build_calendar` / `calendar.parquet`), not DuckDB `dim_calendar`, not weather.
- **D-02:** SG-04 → ADR-012: first Monday `m ≥ Aug 1`; window `[m, m+6]`; 2022-08-01..07 is the edge-year test.
- **D-03:** Christmas extra factor is identity 1.0; do not mutate `config/consumer_profile.yaml`; grep `0.18|0.60|1.06` in `src/` stays empty.
- **D-04:** SG-03 → ADR-013: publish 2019 `consumer_peak_share`; max yearly |Δ| < 1 pp; value ∈ [0.42, 0.48].
- **D-05:** `data/processed/ssot_inputs_profile.parquet` columns `key, value, unit, tag, produced_by`.
- **D-06:** `flat_baseload` = same function / `--profile`; all weights 1.0; no second YAML; unknown name → `ValueError`.
- **D-07:** Commit `tests/golden/consumer_load_2023.sha256` in T4.04; EN-072 regen is a human stop.
- **D-08:** Single file `data/processed/consumer_load_hourly.parquet`; `sources.yml` + bootstrap writer; `all:` = `profile` then `transform`.
- **D-09:** Confirm LIMITATIONS §1 (LP-051); no LP-050 captions this phase.
- **D-10:** ADR-012 (T4.01), ADR-013 (T4.03). Next-free numbers confirmed this session: ADR-012 and ADR-013 are unused.

### Claude's Discretion (researched recommendations below)
- Vectorized pandas/numpy; 03_MODULES names; ~60-line functions.
- CLI flags; atomic processed write (reuse bootstrap `_atomic_write_parquet` pattern, do not call raw-only `write_month`).
- Checksum encoding: hash **payload bytes**, not a parquet file (pyarrow metadata is not a stability contract).
- LP-034 incomplete years: compute hypothetical full-year Σw via `build_calendar` for that year, then emit only `calendar_df` rows.

### Deferred (OUT OF SCOPE)
- LP-050 captions, NUMERIC_SSOT.md / `generate_ssot.py`, procurement stand-in, TP.02, a third named load shape.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-LP-01 | Deterministic calibrated consumer load (LP-001..042, LP-020/021/030/034) | Architecture Patterns 1–6 (weights, normalize, I/O, checksum, dbt path, CLI) |
| SC#1 | LP-040..042 green with persisted 2023 checksum | Pattern 4 + Validation map |
| SC#2 | Full local years sum to 50,000.00 ± 0.01 MWh | Pattern 2 (LP-034 Σw_full) |
| SC#3 | `consumer_peak_share` ready for SSOT | Pattern 5 (2019 row + producer parquet) |
</phase_requirements>

## Summary

M4 is a **pure pandas pipeline** plus a thin CLI/Makefile shell. SPEC-03 already locks the five-step algorithm and the YAML numbers (`config/consumer_profile.yaml` + `ConsumerProfileCfg` are done). `build_calendar` already supplies every column the engine needs, including ADR-011 `is_peak_hour`. The non-obvious HOW items are:

1. **Vectorized day_type / shape lookup** without a Python per-hour loop (03_MODULES performance contract; T4.01 grep AC).
2. **LP-034** when `calendar_df` is a partial local year: Σw must be the hypothetical full year. Recommendation: for each incomplete `year_local`, call `build_calendar(settings, end=date(year,12,31))`, filter that year, run `hourly_weights` on it, use that sum as the denominator; multiply only the rows present in the caller's `calendar_df`.
3. **Checksum stability:** hash sorted `load_mwh` float64 little-endian bytes (plus row count / first-last `ts_utc` as a debug suffix in the golden file if useful). Do **not** hash parquet files — `to_parquet` can embed writer metadata.
4. **D-08 is spec alignment, not a deviation:** SPEC-02 §5 already names `data/processed/consumer_load_hourly.parquet` as a single file. The M3 glob `consumer_load_hourly/**/*.parquet` was the stand-in `write_month` layout. Analog already in-repo: `raw_calendar.calendar` uses `read_parquet('../data/raw/calendar/calendar.parquet')`. Bootstrap already has `_atomic_write_parquet` for that file.
5. **No new dependencies.** pandas, numpy, pyarrow, holidays, pydantic, hashlib (stdlib) cover everything.

**Primary recommendation:** Keep `profile.py` a functional core (`day_type` masks → `hourly_weights` → `normalize_by_local_year` → `build_profile`) and a CLI `main()` that loads calendar parquet + cfg, writes three processed files (hourly, monthly, ssot_inputs). Un-stub `make profile` to `python -m epra.consumer.profile`. Update three existing consumers of the stand-in path in the same T4.03/T4.05 window: `sources.yml`, `bootstrap_fixture_warehouse.py` + its tests, and `warehouse.report._STAND_IN_MARTS` (drop `fct_consumer_load_hourly` once real output exists — procurement stays).

## Architectural Responsibility Map

| Capability | Primary tier | Secondary | Rationale |
|------------|--------------|-----------|-----------|
| Day-type + special windows + seasonal weights | Backend/Python (`profile.hourly_weights`) | Calendar columns from ingest | SPEC-03 steps 1–4; calendar owns holidays/peak |
| Per-year / partial-year normalization | Backend/Python (`normalize_by_local_year`) | `build_calendar` for Σw_full | LP-004 / LP-034 |
| Hourly/monthly parquet + SSOT producer | Backend/Python (CLI shell) | Atomic replace pattern from bootstrap | LP-003/021/020 |
| `fct_consumer_load_hourly` | Database (unchanged SQL) | `sources.yml` path only | SG-06 never-disable; D-08 path |
| CI stand-in until `make profile` | Bootstrap script | Same single-file path | dbt-check still green without M4 CLI |
| Operator entry | Makefile `profile:` | `all:` order swap | EN-050 |

## Standard Stack

### Core (already pinned)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| pandas | `>=2.2,<3` (lockfile resolved) | Frame ops, `np.select` / `.to_numpy` indexing | Already the ingest/calendar stack |
| numpy | `>=1.26,<3` | Shape lookup, checksum bytes | Avoid per-hour Python |
| pyarrow | `>=18,<26` (ADR-004) | Parquet engine | Same as ingest |
| holidays | `>=0.50` | Only via `build_calendar` (do not re-query in the weight hot path) | ING-110 |
| pydantic | `>=2.7` | `cfg.model_copy(update={"profile_name": "flat_baseload"})` | Frozen `ConsumerProfileCfg` |

**No new packages.** Do not add `hashlib` pins (stdlib). Do not import DuckDB in `profile.py`.

### Alternatives considered

| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| `np.select` day_type | `df.apply(day_type, axis=1)` | Violates 03_MODULES "no Python-level per-hour loops"; too slow and non-idiomatic |
| Hash parquet file bytes | Payload `float64.tobytes()` | File hash flakes on metadata; payload hash is the LP-040 bit-stability contract |
| Internal hour synthesis for LP-034 | Slice-only tests (always pass full years to `build_profile`) | Production CLI always has a full spine, but LP-034 is a unit contract on partial `calendar_df`; implementing Σw_full internally makes the test honest |
| `write_month` for processed hourly | `_atomic_write_parquet` single file | `write_month` is raw-layer + provenance columns + monthly partitions — wrong grain vs LP-003 / SPEC-02 §5 |
| Second YAML for flat_baseload | D-06 forbids it | SPEC-03 §5 |

## Architecture Patterns

### Pattern 1 — Vectorized weights (T4.01)

**What:** Boolean masks from calendar columns + precomputed 24-length numpy shape arrays + 12-length seasonal array.

```python
# Illustrative — implementer names follow 03_MODULES.
shapes = {k: np.asarray(cfg.day_shapes[k], dtype="float64") for k in ("weekday", "weekend", "shutdown")}
seasonal = np.array([cfg.seasonal_factors[m] for m in range(1, 13)], dtype="float64")
hours = calendar_df["hour_local"].to_numpy()
months = calendar_df["month_local"].to_numpy()
day_code = np.select(
    [shutdown_mask, holiday_mask | weekend_mask],
    [0, 1],  # map to shutdown / weekend; default weekday
    default=2,
)
# stack shapes (3, 24) and index [day_code, hours]
```

Shutdown dates: Christmas set union maintenance is **not** shutdown for day_type (maintenance keeps weekday/weekend). Christmas: parse `cfg.christmas_shutdown.start/end` (`"12-24"`, `"01-01"`) into per-year `date` sets spanning Y-12-24 .. (Y+1)-01-01.

Maintenance dates (ADR-012):

```python
def first_monday_on_or_after(d: date) -> date:
    return d + timedelta(days=(0 - d.weekday()) % 7)
# m = first_monday_on_or_after(date(year, 8, 1)); window = [m, m+timedelta(days=6)]
```

`special_factor`: shutdown dates → 1.0 (identity); maintenance → `cfg.maintenance.factor`; else 1.0. Vectorize with `np.where`.

`flat_baseload`: short-circuit `hourly_weights` to `ones(n)` (still run the same normalizer).

Unknown `profile_name`: `ValueError` naming the allowed set.

**Grep AC:** numerics only via `cfg.*`. Tests may mention 0.18 as *expected YAML values* in `tests/` — the grep is `src/` only.

### Pattern 2 — Normalization + LP-034 (T4.02)

For each `year_local` present in `calendar_df`:

- `w = hourly_weights(...)`
- `sum_w_rows = w.groupby(year).sum()`
- If the year is **complete** in `calendar_df` (min local ≤ Y-01-01 00:00 and max local ≥ Y-12-31 23:00, DST-aware: last UTC hour of 31 Dec), denominator = `sum_w_rows`.
- If **incomplete**, denominator = `hourly_weights(full_year_calendar, cfg).sum()` where `full_year_calendar = build_calendar(load_settings(), end=date(year, 12, 31))` filtered to `year_local == year`.
- `load = annual_consumption_mwh * w / denominator` aligned to original rows only.

Internal target: year sums within `1e-9` relative; gate is ±0.01 MWh (LP-004).

DST: do not invent hours — `build_calendar` already emits 23/25 UTC hours on DST dates. LP-041 asserts the profile has the same `ts_utc` set as `calendar_df`.

### Pattern 3 — Atomic processed writes (T4.03 / T4.05)

Copy `scripts/bootstrap_fixture_warehouse.py` `_atomic_write_parquet` (tmp + `os.replace`, `engine="pyarrow"`, `index=False`) into a small helper in `profile.py` (or a tiny `_processed_io.py` if length requires). Paths:

| File | Columns |
|------|---------|
| `settings.paths.data_processed / "consumer_load_hourly.parquet"` | `ts_utc, load_mwh` |
| `... / "consumer_load_monthly.parquet"` | `year_local, month_local, volume_mwh` |
| `... / "ssot_inputs_profile.parquet"` | `key, value, unit, tag, produced_by` |

Redirect `data_processed` in tests via `tmp_settings.paths.model_copy` — **extend `tmp_settings`** (today it does not redirect `data_processed`) or pass an explicit outdir in tests. Recommendation: extend `tmp_settings` to also set `data_processed` and `exports`/`warehouse` under `tmp_path` so M4–M7 tests stay isolated.

SSOT row: `key="consumer_peak_share"`, `value=float`, `unit="fraction"`, `tag="CALIBRATED"`, `produced_by="epra.consumer.profile"`. Peak share = `load_mwh[is_peak_hour].sum() / load_mwh.sum()` on **local year 2019** rows.

### Pattern 4 — Golden checksum (T4.04)

```python
def slice_checksum(profile: pd.DataFrame, year: int = 2023) -> str:
    sl = profile.loc[profile["year_local"] == year, ["ts_utc", "load_mwh"]].sort_values("ts_utc")
    payload = sl["load_mwh"].to_numpy(dtype="float64", copy=False)
    return hashlib.sha256(payload.tobytes()).hexdigest()
```

`build_profile` today returns only `ts_utc, load_mwh`. Tests should join year from the calendar (same index/order) **or** `build_profile` may keep calendar columns internally and drop them at the public boundary. Recommendation: public `build_profile` returns **exactly** LP-003 columns; tests pass the companion `calendar_df` into the checksum helper (`merge` on `ts_utc`).

Golden file: one hex digest + newline. LP-042: `cfg.model_copy(update={"annual_consumption_mwh": 50001.0})` → different digest.

### Pattern 5 — dbt source + bootstrap (T4.03)

`sources.yml` analog (already used for calendar):

```yaml
external_location: "read_parquet('../data/processed/consumer_load_hourly.parquet')"
```

Bootstrap `_write_processed_standins`: write consumer stand-in with `_atomic_write_parquet(frame, processed_root / "consumer_load_hourly.parquet")` instead of `_write_ts_utc_dataset`. Update `tests/unit/test_bootstrap_fixture_warehouse.py` `_read_dataset` for that name (single file, not glob). Procurement glob unchanged.

`warehouse.report._STAND_IN_MARTS`: after M4, only `fct_procurement_cost_monthly`. Update `test_warehouse_report.py` accordingly (T4.05).

### Pattern 6 — CLI + Makefile (T4.05)

Mirror `calendar.main`: `argparse`, `load_settings()`, `load_consumer_profile()`, optional `--profile`, optional `--end` unused if calendar file exists. Read `data/raw/calendar/calendar.parquet`. `--profile flat_baseload` → `cfg.model_copy(update={"profile_name": "flat_baseload"})`.

Makefile:

```make
profile:
	$(UV) run python -m epra.consumer.profile

all: profile transform analyze simulate ssot export report
```

Idempotency: second `make profile` byte-identical parquet (no `ingested_at_utc` on processed files).

Delete M4 rows from `test_stubs_fail_loudly.py` in the commit that un-stubs `build_profile` / `monthly_volumes`.

## Common Pitfalls

### Pitfall 1 — Per-hour Python loops
**What:** `for row in calendar_df.itertuples()` for day_type. **Avoid:** masks + numpy take. **Sign:** runtime ≫ 10 s on full spine (~80k hours).

### Pitfall 2 — Hardcoded YAML numerics
**What:** `0.18` / `0.60` / `1.06` in `src/` fail T4.01 AC. **Avoid:** only `cfg.day_shapes` / `cfg.maintenance.factor` / `cfg.seasonal_factors`. Identity `1.0` for non-special hours is allowed (not in the grep).

### Pitfall 3 — Double-dampening Christmas
**What:** multiply shutdown *shape* by `0.18` again or by `maintenance.factor`. **Avoid:** shutdown dates: shape=`shutdown`, special=1.0.

### Pitfall 4 — Maintenance as shutdown day_type
**What:** treating August maintenance as `day_type=shutdown`. **Spec:** maintenance keeps weekday/weekend; only Christmas (and any date in the shutdown window) overrides day_type.

### Pitfall 5 — LP-034 denominator = sum of partial rows
**What:** a 6-month slice would sum to ~25 GWh instead of months matching a 50 GWh year. **Avoid:** Pattern 2 hypothetical full-year Σw.

### Pitfall 6 — Hashing parquet files for LP-040
**What:** golden flakes on pyarrow version / `created_by` metadata. **Avoid:** hash float64 payload.

### Pitfall 7 — `all:` still runs `transform` first
**What:** warehouse keeps stand-in load after `make all`. **Avoid:** D-08 order.

### Pitfall 8 — `write_month` provenance columns on consumer parquet
**What:** extra `ingested_at_utc` columns break LP-003 schema and mart select. **Avoid:** processed helper writes only spec columns.

### Pitfall 9 — Peak share from UTC year 2019
**What:** T-1; 2019-01-01 00:00 Vienna is 2018-12-31 23:00 UTC. **Avoid:** group by `year_local` from calendar.

### Pitfall 10 — Bootstrap tests still glob `processed/consumer_load_hourly/**`
**What:** D-08 single file; `_read_dataset` would assert no files. **Avoid:** update helper in the same commit as the writer.

## Validation Architecture

See `05-VALIDATION.md` (seeded from this section).

| Req | Behavior | Test | Command |
|-----|----------|------|---------|
| LP-001 | Bit-stable given calendar+cfg | Two `build_profile` calls `equals` | pytest unit |
| LP-002 | No YAML literals in src | `rg` in T4.01 verify | shell |
| T4.01 rules | Dec25=Dec26 weights; 2022 Aug 1–7; holiday Monday weekend | `tests/unit/test_profile.py` | pytest |
| LP-004 | Full year 50000±0.01 | property on 2019–2023 | pytest |
| LP-034 | 6-month volumes match full-year months | fixture 2023 H1 | pytest |
| LP-020 | 2019 share in [0.42,0.48]; yearly Δ<1pp | unit | pytest |
| LP-021 | monthly grain | unit | pytest |
| LP-030 | flat weights 1.0 pre-norm; same annual | unit | pytest |
| LP-040 | ratio band, Aug&lt;Jul, Dec25=Dec26 load, sha256 | golden | pytest |
| LP-041 | no null/neg; DST 23/25; 1:1 hours | property | pytest |
| LP-042 | 50001 breaks checksum | meta | pytest |
| D-08 | sources.yml single file; bootstrap writes it | bootstrap tests + dbt-check | pytest / CI |

## Security Domain

No network, no secrets. Calendar/YAML are local files. `yaml.safe_load` already in `config.py`. Processed paths from `Settings`, not user path traversal (optional CLI outdir if added must stay under `data/processed` or tmp).

## Sources

### Primary (HIGH)
- `docs/SPEC-03_consumer_load_profile.md`, `docs/SPEC-02_data_model.md` §5 (`fct_consumer_load_hourly` single-file path)
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` §M4, `03_MODULES.md` consumer.profile, `05_IMPLEMENTATION_GUIDES.md` §5.4/§5.6, `14_SPEC_GAPS.md` SG-03/SG-04
- `.planning/phases/EPRA-05-m4-consumer-profile/05-CONTEXT.md`
- `src/epra/consumer/profile.py` (stub), `src/epra/common/config.py` (`ConsumerProfileCfg`), `src/epra/ingest/calendar.py`, `config/consumer_profile.yaml`
- `dbt/models/sources.yml` (calendar single-file analog; consumer glob to replace)
- `scripts/bootstrap_fixture_warehouse.py` (`_atomic_write_parquet`, `_write_processed_standins`)
- `tests/unit/test_calendar.py`, `test_bootstrap_fixture_warehouse.py`, `test_stubs_fail_loudly.py`, `test_warehouse_report.py`
- `Makefile` `profile:` / `all:`
- `docs/ADR/` listing — 001–011 present; 012/013 free

### Secondary
- None. No new libraries to legitimacy-check.

## Open Questions (resolved for planner)

1. **Checksum encoding** → payload float64 SHA-256 (Pattern 4).
2. **LP-034 incomplete calendar** → `build_calendar` full year for Σw (Pattern 2).
3. **SSOT `unit` string** → `"fraction"`.
4. **Stand-in report flag** → remove consumer mart in T4.05.

## Metadata

**Research date:** 2026-09-02
**Valid until:** this milestone (no third-party version risk)
