# Phase 2: M1 ENTSO-E Ingestion — Pattern Map

**Mapped:** 2026-07-21  
**Files analyzed:** 16 new/modified targets for M1  
**Analogs found:** 14 / 16 (2 planned internals have spec-only contracts, no code yet)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/epra/ingest/_io.py` | utility | file-I/O | `src/epra/common/db.py` | role-match |
| `src/epra/ingest/_fetch.py` | service | request-response | `src/epra/common/config.py` (`entsoe_token`) + `scripts/check_no_token_in_code.py` | partial |
| `src/epra/ingest/entsoe.py` | service | batch + file-I/O | `src/epra/ingest/geosphere.py` (stub shell) | exact (shell) |
| `src/epra/ingest/validate.py` | service | batch + file-I/O | `scripts/oespi_reconcile.py` | role-match |
| `src/epra/ingest/exceptions.py` | utility | — | `src/epra/common/timeutil.py` (stdlib errors) | partial |
| `src/epra/common/config.py` | config | — | *(self — extend in place)* | exact |
| `src/epra/common/timeutil.py` | utility | transform | *(self — call, do not duplicate)* | exact |
| `src/epra/common/logging.py` | utility | — | *(self — call at pipeline boundary)* | exact |
| `Makefile` | config | batch | *(self — replace stub targets)* | exact |
| `tests/unit/test_io.py` | test | file-I/O | `tests/unit/test_logging_and_db.py` | exact |
| `tests/unit/test_fetch.py` | test | request-response | `tests/unit/test_scripts.py` | role-match |
| `tests/unit/test_entsoe.py` | test | transform | `tests/unit/test_timeutil.py` | role-match |
| `tests/unit/test_validate.py` | test | transform | `tests/unit/test_config.py` | role-match |
| `tests/test_raw_contracts.py` | test | file-I/O | `tests/unit/test_config.py` (drift guards) | role-match |
| `tests/fixtures/entsoe_*` | config | file-I/O | *(none — first fixtures)* | no analog |
| `tests/unit/test_stubs_fail_loudly.py` | test | — | *(self — remove M1 rows)* | exact |

---

## Pattern Assignments

### `src/epra/ingest/_io.py` (utility, file-I/O)

**Analog:** `src/epra/common/db.py` (path resolution + mkdir + atomic open)

**Imports pattern** (from `db.py` lines 10-14):

```python
from __future__ import annotations

from pathlib import Path

import duckdb

from epra.common.config import REPO_ROOT, Settings
```

Adapt: replace `duckdb` with `pandas` for parquet I/O; keep `REPO_ROOT` + `Settings` injection.

**Path resolution pattern** (from `db.py` lines 19-22):

```python
def warehouse_path(settings: Settings) -> Path:
    """Absolute path of the DuckDB warehouse file."""
    p = settings.paths.warehouse
    return p if p.is_absolute() else REPO_ROOT / p
```

Copy shape for `raw_month_path(dataset, month, settings)` → `settings.paths.data_raw` with §7 layout `data/raw/<dataset>/<YYYY>/<dataset>_<YYYY-MM>.parquet`.

**Directory creation pattern** (from `db.py` lines 27-28):

```python
    path = warehouse_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
```

Apply before every write; use temp-file-then-rename for ING-003 atomicity (prescribed in `docs/EXECUTION_BLUEPRINT/03_MODULES.md` §`_io`).

**Core pattern:** pure helpers + `Settings`-injected paths; no YAML reads; raise `ValueError` with expected-vs-actual on contract violations (naive `ts_utc`, out-of-month rows). Append ING-004 columns (`ingested_at_utc`, `source`, `request_hash`) here only.

---

### `src/epra/ingest/_fetch.py` (service, request-response)

**Analog:** `src/epra/common/config.py` (`entsoe_token`) + logging/idempotency from `logging.py`

**Secret accessor** (from `config.py` lines 162-175):

```python
def entsoe_token() -> str:
    """Return the ENTSO-E API token from the environment, failing fast (ING-021)."""
    load_dotenv(REPO_ROOT / ".env")
    token = os.environ.get("ENTSOE_API_TOKEN", "").strip()
    if not token or token == "your-token-here":
        raise RuntimeError(
            "ENTSOE_API_TOKEN is not set. Copy .env.example to .env and fill in the "
            "token obtained per SPEC-01 §2 (ING-020), or export the variable."
        )
    return token
```

Never log URLs containing the token; strip before ING-008 log lines (see `scripts/check_no_token_in_code.py` lines 18-19 for what counts as a violation).

**Logging setup at pipeline boundary** (from `logging.py` lines 16-39):

```python
def setup(level: int = logging.INFO, logfile: Path | None = None) -> None:
    """Configure root logging: INFO to stdout; optionally also to ``logfile``."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    # ... stream + optional file handler ...
    root.setLevel(level)
```

Ingestion CLI should call `setup(logfile=settings.paths.reports / "ingestion" / f"ingest_{date.today()}.log")`.

**Per-module logger** (prescribed in `.planning/codebase/CONVENTIONS.md`):

```python
import logging

logger = logging.getLogger(__name__)
```

**Retry/cache:** use `tenacity` (already in `pyproject.toml`); only in `_fetch` per `docs/EXECUTION_BLUEPRINT/08_PATTERNS.md`. Inject transport for tests (stub returning canned XML) — mirror `tests/unit/test_scripts.py` subprocess isolation pattern but prefer in-process mocks for speed.

**Frozen query object:** follow pydantic frozen models in `config.py` (`_Frozen` base, lines 27-28):

```python
class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
```

Use `@dataclass(frozen=True)` or `_Frozen` subclass for `EntsoeQuery` per `03_MODULES.md`.

---

### `src/epra/ingest/entsoe.py` (service, batch + file-I/O)

**Analog:** `src/epra/ingest/geosphere.py` (module shell) + `src/epra/common/timeutil.py` (month iteration)

**Module docstring + REQ traceability** (from `geosphere.py` lines 1-17):

```python
"""GeoSphere Austria ingestion — daily mean temperature, Graz (M2).

Not yet implemented. Binding contract: SPEC-01 §9. Key points:
...
Implements (when built): ING-090..094.
"""
```

Replace with real contract summary; flip "when built" to concrete REQ IDs once implemented (pattern from `config.py` lines 1-8).

**Stub shell → implement** (from `entsoe.py` lines 22-57):

```python
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from epra.common.config import Settings

_MSG = "M1 not implemented yet — build per SPEC-01 §§2-8 (see module docstring)"


def backfill(settings: Settings, start: date, end: date) -> None:
    """Full ingestion of all four ENTSO-E datasets for [start, end] (ING-040)."""
    raise NotImplementedError(_MSG)
```

Keep public signatures; replace body with orchestration: `load_settings()` already injected via `Settings`; call `timeutil.iter_month_starts`, `_fetch.fetch_entsoe`, parsers, `_io.write_month`. Remove `_MSG` raises.

**CLI entrypoint pattern** (from `geosphere.py` lines 43-49):

```python
def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.geosphere --start YYYY-MM-DD --end YYYY-MM-DD`` (ING-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
```

Use `argparse` like `scripts/oespi_reconcile.py` (lines 70-73) inside `main`; return `0` on success, `1` on user error.

**Timezone recipe** (call, do not reimplement — `timeutil.py` lines 25-36, 74-82):

```python
def to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("naive datetime passed to to_utc(); timestamps must be tz-aware")
    return ts.astimezone(UTC)


def iter_month_starts(start: date, end: date) -> Iterator[date]:
    current = month_start(start)
    last = month_start(end)
    while current <= last:
        yield current
        current = next_month(current)
```

Request boundaries: `pd.Timestamp(month_start, tz="Europe/Vienna")` per `05_IMPLEMENTATION_GUIDES.md` §5.1; persist via `to_utc()`.

**Data flow (prescribed):** CLI/Make → window mgmt → per-chunk `_fetch` → parse → per-month split → `_io.write_month` (`03_MODULES.md` §`entsoe`).

---

### `src/epra/ingest/validate.py` (service, batch + file-I/O)

**Analog:** `scripts/oespi_reconcile.py` (fail-fast CLI + structured output)

**Gate runner shell** (from `validate.py` lines 23-39):

```python
from __future__ import annotations

from collections.abc import Sequence

from epra.common.config import Settings

_MSG = "M1 not implemented yet — build per SPEC-01 §§8-11 (see module docstring)"


def run_gates(settings: Settings) -> None:
    """Run all applicable gates; raise on first hard failure (EN-061)."""
    raise NotImplementedError(_MSG)
```

Replace with: load raw parquet → pure `gate_ing_0xx()` functions → aggregate `GateResult` → write markdown report → `raise_if_failed()`.

**Fail-fast reconciliation pattern** (from `oespi_reconcile.py` lines 43-62):

```python
def reconcile(entry1: Path, entry2: Path, out: Path) -> int:
  mismatches: list[str] = []
  # ... collect violations ...
  if mismatches:
      print(f"RECONCILIATION FAILED — {len(mismatches)} mismatch(es):")
      for m in mismatches:
          print(f"  {m}")
      return 1
```

Adapt: gate failures raise `GateFailure` naming gate IDs (EN-061); report still lists every gate exactly once (`03_MODULES.md` §`validate`).

**Pure gate functions:** mirror `format.py` — stateless, no I/O inside gate checks:

```python
def format_eur_mwh(value: float) -> str:
    """Unit price with 1 decimal: 123.456 → ``123.5 EUR/MWh``."""
    return f"{value:,.1f} EUR/MWh"
```

Gate signature: `gate_ing_082(prices_hourly: pd.DataFrame) -> GateResult` with `summary` carrying expected-vs-actual.

**DST / peak helpers for ING-080:** call `timeutil.local_hours_in_day` and `timeutil.is_peak_hour` — do not re-type peak constants (`timeutil.py` lines 19-22, 52-57).

---

### `src/epra/ingest/exceptions.py` (utility)

**Analog:** stdlib usage in `timeutil.py` (explicit `ValueError` messages)

**Error pattern** (from `timeutil.py` lines 27-28):

```python
    if ts.tzinfo is None:
        raise ValueError("naive datetime passed to to_utc(); timestamps must be tz-aware")
```

Define package-specific subclasses per `.planning/codebase/CONVENTIONS.md`: `IngestError` base; `IngestAuthError`, `IngestTransportError`, `ContractError`, `GateFailure`, `NoDataError`. Each carries actionable context (gate id, HTTP status, column mismatch).

---

### `src/epra/common/config.py` (config — extend only if needed)

**Analog:** *(self)*

M1 settings already exist (`IngestCfg`, `ZoneCfg`, `entsoe_token`). Extension pattern when adding keys (`config.py` lines 134-145):

```python
def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return loaded


@cache
def load_settings(path: Path | None = None) -> Settings:
    """Load and validate ``config/settings.yaml`` (EN-040). Cached per path."""
    return Settings.model_validate(_read_yaml(path or REPO_ROOT / "config" / "settings.yaml"))
```

Any new key → pydantic model + `config/settings.yaml` + drift test in same commit (`tests/unit/test_config.py`).

---

### `Makefile` (config, batch)

**Analog:** *(self — replace stub targets)*

**Stub target pattern** (lines 24-31):

```makefile
backfill:            ## M1 — SPEC-01 §4: full 2019→latest ingestion (all sources)
	@echo "ERROR: 'make backfill' not implemented yet (M1 — SPEC-01 ING-040)." >&2; exit 1

ingest:              ## M1 — SPEC-01 §4: incremental 45-day refresh (ING-041)
	@echo "ERROR: 'make ingest' not implemented yet (M1 — SPEC-01 ING-041)." >&2; exit 1

validate-ingest:     ## M1/M2 — SPEC-01 §§8-11 gates → reports/ingestion/
	@echo "ERROR: 'make validate-ingest' not implemented yet (M1 — SPEC-01 §8)." >&2; exit 1
```

**Working target pattern** (from `setup` / `test` lines 10-21):

```makefile
setup:
	$(UV) venv --allow-existing
	$(UV) pip install -e ".[dev]"
	$(UV) run pre-commit install

test:
	$(UV) run pytest
```

Wire M1 as:

```makefile
backfill:
	$(UV) run python -m epra.ingest.entsoe --backfill

ingest:
	$(UV) run python -m epra.ingest.entsoe --incremental

validate-ingest:
	$(UV) run python -m epra.ingest.validate
```

Keep `UV ?= uv` and idempotent semantics (EN-050). Exit non-zero on failure.

---

### `tests/unit/test_io.py` (test, file-I/O)

**Analog:** `tests/unit/test_logging_and_db.py`

**Fixture + tmp_path pattern** (lines 28-37):

```python
def test_db_connect_creates_warehouse(tmp_path: Path) -> None:
    settings = load_settings()
    paths = settings.paths.model_copy(update={"warehouse": tmp_path / "wh" / "epra.duckdb"})
    settings = settings.model_copy(update={"paths": paths})
    con = db.connect(settings)
    try:
        assert con.execute("select 42").fetchone() == (42,)
    finally:
        con.close()
    assert db.warehouse_path(settings).exists()
```

Redirect `settings.paths.data_raw` to `tmp_path`; assert parquet dtypes, atomic replace, month-boundary rejection.

---

### `tests/unit/test_fetch.py` (test, request-response)

**Analog:** `tests/unit/test_scripts.py`

**Subprocess / isolation pattern** (lines 13-20):

```python
def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
```

Prefer in-process mocks for `_fetch`; use `monkeypatch` for env/token like `test_config.py` lines 108-117:

```python
def test_entsoe_token_fails_fast_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENTSOE_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="ENTSOE_API_TOKEN"):
        entsoe_token()
```

Mark live API tests `@pytest.mark.live` (defined in `pyproject.toml` lines 76-78); CI runs `pytest -m "not live"`.

---

### `tests/unit/test_entsoe.py` (test, transform)

**Analog:** `tests/unit/test_timeutil.py`

**Explicit REQ comments + boundary tests** (lines 37-49):

```python
def test_peak_hour_definition() -> None:
    # Charter glossary / ING-110: Mon-Fri 08:00-20:00 Europe/Vienna, non-holiday.
    monday = datetime(2024, 1, 8, 14, 0, tzinfo=VIENNA)
    assert is_peak_hour(monday)
    assert not is_peak_hour(monday.replace(hour=7))
```

Cover parsers: A03 forward-fill (ING-063), resolution inference (ING-060), 15-min mean-not-sum (ING-062), DST hour counts (ING-080). Use committed XML snippets under `tests/fixtures/`.

---

### `tests/unit/test_validate.py` (test, transform)

**Analog:** `tests/unit/test_config.py`

**Validator rejection pattern** (lines 83-87):

```python
def test_day_shape_validator_rejects_wrong_length() -> None:
    bad = _profile_dict()
    bad["day_shapes"] = {**bad["day_shapes"], "weekday": [1.0] * 23}
    with pytest.raises(ValidationError, match="24 values"):
        ConsumerProfileCfg.model_validate(bad)
```

One test per gate fail case with synthetic frames; happy-path synthetic data passes. Assert report markdown contains gate IDs.

---

### `tests/test_raw_contracts.py` (test, file-I/O)

**Analog:** `tests/unit/test_config.py` (committed-value drift guards)

**Drift guard pattern** (lines 21-26):

```python
def test_settings_zones_match_spec01_appendix_a() -> None:
    s = load_settings()
    assert s.zones["at"].eic == "10YAT-APG------L"
    assert s.zones["at"].code == "AT"
    assert s.zones["delu"].eic == "10Y1001A1001A82H"
```

Open one fixture parquet per dataset; assert exact column names and dtypes per SPEC-01 §7 (ING-070). No network.

---

### `tests/unit/test_stubs_fail_loudly.py` (test — modify)

**Analog:** *(self)*

Remove M1 rows (lines 25-30) once `entsoe` and `validate` are implemented:

```python
STUBS: list[tuple[str, Callable[..., Any], tuple[Any, ...]]] = [
    ("M1", entsoe.backfill, (SETTINGS, date(2019, 1, 1), date(2019, 2, 1))),
    ("M1", entsoe.ingest_incremental, (SETTINGS,)),
    ...
]
```

Keep M2+ stubs until their milestones ship.

---

## Shared Patterns

### Configuration injection
**Source:** `src/epra/common/config.py`  
**Apply to:** All ingest modules  
```python
@cache
def load_settings(path: Path | None = None) -> Settings:
    return Settings.model_validate(_read_yaml(path or REPO_ROOT / "config" / "settings.yaml"))
```
Pass `Settings` into every public function; never re-read YAML in ingest code.

### Timezone doctrine
**Source:** `src/epra/common/timeutil.py`  
**Apply to:** `entsoe.py`, `validate.py` (ING-080 DST checks)  
```python
VIENNA = ZoneInfo("Europe/Vienna")

def to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("naive datetime passed to to_utc(); timestamps must be tz-aware")
    return ts.astimezone(UTC)
```

### Logging
**Source:** `src/epra/common/logging.py`  
**Apply to:** `entsoe.py`, `_fetch.py`, `validate.py`  
```python
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
# Call setup() once at CLI entry; logger = logging.getLogger(__name__) per module
```

### CLI `main` contract
**Source:** `src/epra/ingest/geosphere.py` + `scripts/oespi_reconcile.py`  
**Apply to:** `entsoe.py`, `validate.py`  
```python
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # ...
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### TDD / stub lifecycle
**Source:** `tests/unit/test_stubs_fail_loudly.py` + `AGENTS.md` W-1  
**Apply to:** Every new module  
Implement + tests in same commit; delete corresponding `STUBS` rows; docstrings list `Implements: ING-xxx`.

### Secrets (A-7)
**Source:** `src/epra/common/config.py` + `scripts/check_no_token_in_code.py` + `.pre-commit-config.yaml`  
**Apply to:** `_fetch.py`, fixtures, tests  
Token only via `entsoe_token()`; pre-commit runs `check_no_token_in_code.py` on all text files.

### Functional core / imperative shell
**Source:** `docs/EXECUTION_BLUEPRINT/08_PATTERNS.md`  
**Apply to:** Parsers + gates (pure); CLI/backfill (I/O shell)  
Pure: `parse_publication_xml`, `gate_ing_082`. Shell: `backfill`, `run_gates`.

### Contract tests
**Source:** `docs/SPEC-01_data_ingestion.md` §7, ING-070  
**Apply to:** `tests/test_raw_contracts.py`, `tests/fixtures/`  
Committed fixtures ≤200 rows each; CI has no network (`ci.yml` line 34: `pytest -m "not live"`).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/epra/ingest/_io.py` | utility | file-I/O | Planned internal API in `03_MODULES.md`; closest is `db.py` path helper only |
| `src/epra/ingest/_fetch.py` | service | request-response | First HTTP client module; tenacity/cache pattern prescribed in SPEC-01, not yet in code |
| `tests/fixtures/entsoe_*` | config | file-I/O | `tests/fixtures/` empty until M1; generate once from real pulls per ING-070 |

Planner should follow `docs/EXECUTION_BLUEPRINT/03_MODULES.md` §`_io`/`_fetch`/`entsoe`/`validate` and `05_IMPLEMENTATION_GUIDES.md` §5.1 for these.

---

## Metadata

**Analog search scope:** `src/epra/common/`, `src/epra/ingest/`, `scripts/`, `tests/unit/`, `Makefile`, `config/`, `docs/EXECUTION_BLUEPRINT/`, `.planning/codebase/`  
**Files scanned:** 27 Python modules + 6 config/doc anchors  
**Pattern extraction date:** 2026-07-21  
**Upstream note:** No `CONTEXT.md` or `RESEARCH.md` in phase dir; scope taken from ROADMAP Phase 2, AGENTS.md M1, SPEC-01, EXECUTION_BLUEPRINT 03/05/08.
