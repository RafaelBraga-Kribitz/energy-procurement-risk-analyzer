# Testing Patterns

**Analysis Date:** 2026-07-20

## Test Framework

**Runner:**
- pytest ≥ 8 (`[project.optional-dependencies] dev` in `pyproject.toml`)
- Config: `[tool.pytest.ini_options]` in `pyproject.toml`
- Coverage: `pytest-cov` with `--cov=epra --cov-fail-under=80 --cov-report=term-missing` (EN-071)

**Assertion Library:**
- pytest built-in `assert`
- `pytest.raises(..., match=...)` for exception contracts
- pydantic `ValidationError` for schema rejection tests

**Run Commands:**
```bash
make test                         # uv run pytest (full suite + coverage gate)
uv run pytest                     # same as make test
uv run pytest -m "not live"       # CI mode — exclude live API tests (EN-070)
uv run pytest tests/unit/test_timeutil.py   # single file
uv run pytest -k dst              # substring filter
uv run pytest --cov=epra --cov-report=html  # HTML coverage (optional local)
```

## Test File Organization

**Location:**
- Separate tree under `tests/` (not collocated with `src/`)
- Layout per SPEC-07: `tests/unit/`, `tests/fixtures/`, `tests/golden/`
- Today: unit tests live in `tests/unit/`; `tests/fixtures/` and `tests/golden/` hold `.gitkeep` until M1+ content lands
- No `conftest.py` yet — add when shared fixtures/helpers are needed

**Naming:**
- `test_<module_or_concern>.py` (`test_config.py`, `test_logging_and_db.py`, `test_scripts.py`)
- Test functions: `test_<behavior>` — state the behavior, not the function name (`test_dst_day_hour_counts`, not `test_local_hours`)
- Cite REQ / trap IDs in comments or docstring when pinning a gate (`ING-080`, `T-1`, `RP-701`)

**Structure:**
```
tests/
  unit/
    test_smoke.py              # M0 package import
    test_config.py             # YAML drift + validators
    test_timeutil.py           # DST / peak / UTC
    test_logging_and_db.py
    test_report.py             # format + style
    test_scripts.py            # CLI governance scripts via subprocess
    test_stubs_fail_loudly.py  # NotImplementedError contract for stubs
  fixtures/                    # committed parse inputs (ENTSO-E XML, etc.) — EN-070
  golden/                      # LP-040 / ST-601 checksums — human-approved regen (EN-072)
```

## Test Structure

**Suite Organization:**
```python
"""Timezone handling tests — trap T-1 is the most dangerous bug class."""

from datetime import UTC, date, datetime

import pytest

from epra.common.timeutil import VIENNA, local_hours_in_day, to_utc


def test_naive_datetimes_are_rejected() -> None:
    naive = datetime(2024, 1, 8, 12, 0)
    with pytest.raises(ValueError, match="naive"):
        to_utc(naive)


def test_dst_day_hour_counts() -> None:
    # ING-080 DST correctness: last Sunday of March = 23 h, October = 25 h.
    assert local_hours_in_day(date(2024, 3, 31)) == 23
    assert local_hours_in_day(date(2024, 10, 27)) == 25
```

**Patterns:**
- Flat `test_*` functions preferred for small modules; use `@pytest.mark.parametrize` for table-driven contracts (`test_stubs_fail_loudly.py`)
- Type-annotate test functions `-> None`
- Arrange/act/assert without mandatory comment labels; keep tests short and explicit
- Pin committed YAML / constants so accidental config edits fail loudly (`test_config.py` drift guards)
- Stub inventory: when a milestone ships, remove its rows from `STUBS` in `test_stubs_fail_loudly.py`

## Mocking

**Framework:**
- pytest built-ins: `monkeypatch`, `tmp_path`
- No `unittest.mock` / `pytest-mock` usage in current suite
- External process boundaries tested via `subprocess.run` (`test_scripts.py`)

**Patterns:**
```python
def test_entsoe_token_fails_fast_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENTSOE_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="ENTSOE_API_TOKEN"):
        entsoe_token()
    monkeypatch.setenv("ENTSOE_API_TOKEN", "real-looking-token-123")
    assert entsoe_token() == "real-looking-token-123"


def test_logging_setup_is_idempotent(tmp_path: Path) -> None:
    logfile = tmp_path / "sub" / "ingest_test.log"
    epra_logging.setup(logfile=logfile)
    # ... assert file contents ...
```

**What to Mock / Isolate:**
- Environment variables (`ENTSOE_API_TOKEN`) via `monkeypatch`
- Filesystem outputs via `tmp_path` (logs, warehouse path override, reconcile dirs)
- External APIs: never call in unit tests — use committed fixtures under `tests/fixtures/` (EN-070)
- Live API checks only under `@pytest.mark.live` (excluded in CI)

**What NOT to Mock:**
- Pure helpers (`timeutil`, `report.format`, `report.style`)
- Pydantic validation (exercise real models)
- Committed config YAML (load real files for drift tests)

## Fixtures and Factories

**Test Data:**
```python
# Inline helpers for mutation tests (test_config.py)
def _profile_dict() -> dict[str, object]:
    return load_consumer_profile().model_dump()


def test_day_shape_validator_rejects_wrong_length() -> None:
    bad = _profile_dict()
    bad["day_shapes"] = {**bad["day_shapes"], "weekday": [1.0] * 23}  # type: ignore[dict-item]
    with pytest.raises(ValidationError, match="24 values"):
        ConsumerProfileCfg.model_validate(bad)


# Script CLI tests craft CSV strings in tmp_path (test_scripts.py)
OESPI_HEADER = "month,oespi_base,oespi_peak,source_url,retrieved_at\n"
```

**Location:**
- Shared parse fixtures → `tests/fixtures/` (planned: `tests/fixtures/entsoe/` for PT15M, DST, A03 — EN-070 / ING-062)
- Golden checksums → `tests/golden/` (LP-040, ST-601); regenerate only via `scripts/generate_golden_metrics.py` + human approval (EN-072)
- Small factories: private helpers in the test module (`_profile_dict`, `_run`)
- Synthetic data must be hand-computable so expected values are obvious (`07_QUALITY_STANDARDS.md`)

## Coverage

**Requirements:**
- Hard gate: ≥ 80% line coverage on package `epra` (`--cov-fail-under=80`, EN-071)
- Advisory: aim ≥ 90% for `common`, `consumer`, `strategies` (`07_QUALITY_STANDARDS.md`)
- CI enforces coverage via the same pytest addopts

**Configuration:**
- `[tool.coverage.run] source = ["epra"]`
- Exclude lines: `pragma: no cover`, `if __name__ == "__main__":`, `if TYPE_CHECKING:`
- Stubbed milestone modules currently raise `NotImplementedError` — covered by `test_stubs_fail_loudly.py` until implemented

**View Coverage:**
```bash
uv run pytest                          # term-missing report in console
uv run pytest --cov-report=html
# open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- Scope: single module / pure function / config schema / formatter
- No network, no wall-clock dependence (EN-070)
- Examples: `tests/unit/test_timeutil.py`, `tests/unit/test_report.py`, `tests/unit/test_config.py`
- Budget: full suite advisory < 120 s (`07_QUALITY_STANDARDS.md`)

**Contract / Fixture Tests (M1+):**
- Parser paths on committed XML/GeoJSON under `tests/fixtures/`
- Schema/byte contracts for parquet columns and dbt marts (ING-070, DM schema YAML)
- Every gate gets a failing-case test

**Golden / Property Tests (M4/M6):**
- Bit-stable sha256 goldens for consumer profile (LP-040/042) and strategies (ST-601)
- Determinism: two runs → identical outputs (ST-603, AN-705, A-4)
- Golden regeneration: propose diff + WHY; human approves (AGENTS.md §2.6, EN-072)

**Integration / Live:**
- `@pytest.mark.live` for real ENTSO-E/GeoSphere hits — local only, excluded in CI
- CI job 3 (M3): `dbt build` against fixture mini-warehouse
- CI job 4 (M6): `scripts/check_ssot_consistency.py` (GV-303)
- Real-data gates (`make validate-ingest`) are Makefile targets, not default pytest

**E2E Tests:**
- Not a browser/app suite — pipeline E2E is `make all` / milestone gates with committed reports
- Script CLIs covered by subprocess unit tests (`tests/unit/test_scripts.py`)

## Common Patterns

**Exception contracts:**
```python
with pytest.raises(ValueError, match=r"\[0, 1\]"):
    style.hybrid_color(1.5)

with pytest.raises(NotImplementedError, match="M1"):
    entsoe.backfill(SETTINGS, date(2019, 1, 1), date(2019, 2, 1))
```

**Parametrize stubs:**
```python
@pytest.mark.parametrize(
    ("milestone", "func", "args"),
    STUBS,
    ids=[f"{m}-{f.__module__}.{f.__name__}" for m, f, _ in STUBS],
)
def test_stub_raises_not_implemented_naming_its_milestone(
    milestone: str, func: Callable[..., Any], args: tuple[Any, ...]
) -> None:
    with pytest.raises(NotImplementedError, match=milestone):
        func(*args)
```

**CLI / script testing:**
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

**Markers:**
- `live` — hits real external APIs; excluded in CI (`pytest -m "not live"`)

**TDD / regression policy:**
- W-1: for every REQ with a testable contract, test lands in the same commit as implementation
- EN-073: every bug found after M3 gets a regression test in the same fix PR
- Warning-clean runs; new warnings fixed or explicitly filtered with a comment

**Snapshot Testing:**
- Not used for charts — assert matplotlib object properties / constants, never pixel-diff (RP-70x / quality standards)
- Prefer explicit numeric and string assertions over snapshots

---

*Testing analysis: 2026-07-20*
*Update when test patterns change*
