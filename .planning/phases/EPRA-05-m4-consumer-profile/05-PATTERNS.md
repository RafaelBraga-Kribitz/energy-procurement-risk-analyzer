# Phase 5: M4 Consumer Profile - Pattern Map

**Mapped:** 2026-09-02
**Files analyzed:** stub `profile.py`, calendar CLI, bootstrap atomic parquet, sources.yml calendar analog, Makefile stubs, warehouse stand-in flag, config/tests
**Analogs found:** 7 / 7 (every new artifact has an in-repo role match)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/epra/consumer/profile.py` (core) | domain service (pure compute) | batch / in-memory | `src/epra/ingest/calendar.py` `build_calendar` (calendar_df in, frame out, vectorized columns) | exact |
| `src/epra/consumer/profile.py` `main` | CLI | batch / file-I/O | `calendar.main` (`argparse`, load settings, write one parquet, return 0) | exact |
| `tests/unit/test_profile.py` | unit + property + golden | request-response | `tests/unit/test_calendar.py` (module-scoped `build_calendar` fixture, DST/holiday cases) | exact |
| `tests/golden/consumer_load_2023.sha256` | golden digest | — | none yet; checksum helper is new but stdlib `hashlib` | n/a (first golden) |
| `docs/ADR/ADR-012_*.md`, `ADR-013_*.md` | governance | — | `docs/ADR/ADR-006_validation-gate-scope-local-year.md` (Context/Decision/Consequences/Spec deviations) | exact |
| `dbt/models/sources.yml` consumer path | config | transform | same file, `raw_calendar.calendar` single-file `read_parquet` | exact |
| `scripts/bootstrap_fixture_warehouse.py` consumer writer | utility | file-I/O | `_atomic_write_parquet` already used for `calendar.parquet` | exact |
| `Makefile` `profile:` / `all:` | operator interface | batch | `calendar:` / `transform:` un-stub precedent (M2/M3) | exact |
| `src/epra/warehouse/report.py` `_STAND_IN_MARTS` | report copy | — | self (drop consumer after M4) | exact |
| `tests/unit/test_stubs_fail_loudly.py` | stub guard | — | delete M4 rows when functions exist (file's own comment) | exact |

## Pattern Assignments

### `build_calendar` → `build_profile` (pure core)

Reuse: typed public function, `Implements:` docstring, DataFrame in/out, UTC `ts_utc`, no I/O. Calendar already computed `date_local` / `hour_local` / `dow_local` / `is_holiday_at` / `year_local` / `month_local` / `is_peak_hour` — profile **must not** call `timeutil.is_peak_hour` again (D-01, ADR-011).

Tests: module-scoped calendar fixture with fixed `end` (`test_calendar.py` `_FIXED_END = date(2027, 12, 31)` is sufficient for 2019 peak share, 2022 maintenance Monday, 2023 golden, 2024 DST).

### CLI `calendar.main` → `profile.main`

```python
# calendar.py shape to copy
parser = argparse.ArgumentParser(prog="python -m epra.consumer.profile", ...)
parser.add_argument("--profile", default=None)  # override profile_name
# load yaml cfg; optional model_copy for flat_baseload
# read calendar parquet from settings.paths.data_raw / calendar / calendar.parquet
# write processed parquet via atomic helper
return 0
```

`if __name__ == "__main__": raise SystemExit(main())` — same as calendar.

### Atomic parquet — bootstrap `_atomic_write_parquet`

Do not use `_io.write_month` (raw provenance + monthly partitions). Copy the tmp+`os.replace` helper; processed files have **no** `ingested_at_utc`.

### `sources.yml` — calendar single file

Replace consumer glob with the same `read_parquet('../data/processed/consumer_load_hourly.parquet')` shape as calendar. Keep `../data/` prefix (M3 Pitfall 1).

### ADR template

Copy ADR-006 headings. ADR-012 cites SG-04 + 2022-08-01 Monday. ADR-013 cites SG-03 + 2019 + 1 pp test. Mark `14_SPEC_GAPS.md` rows adopted.

### Makefile un-stub

Same one-liner style as `calendar:` / `transform:`. Reorder `all:` per D-08.

### Stub-test deletion

`test_stubs_fail_loudly.py` module docstring: delete rows when implemented. Remove the two M4 tuples in the same commit as the real functions (T4.01 or T4.05 — prefer T4.01 when `build_profile` no longer raises, otherwise pytest collection of that file fails the suite).

## Anti-patterns (from RESEARCH pitfalls)

- `itertuples` / `apply` over hours
- YAML numbers in `src/`
- `write_month` for LP-003 output
- Parquet-file SHA as golden
- UTC-year peak share
- Leaving `transform` before `profile` in `all:`
