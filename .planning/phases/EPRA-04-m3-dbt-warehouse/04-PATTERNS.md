# Phase 4: M3 dbt Warehouse - Pattern Map

**Mapped:** 2026-07-24
**Files analyzed:** ~30 new artifacts (dbt models/macros/tests/YAML + Python scripts/tests + governance docs)
**Analogs found:** 8 / 8 (all high-value targets have a strong role/data-flow match)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/bootstrap_fixture_warehouse.py` (D-04) | utility / CLI script (deterministic data synthesizer) | batch / file-I/O | `scripts/oespi_reconcile.py` (CLI shape) + `tests/fixtures/**` (lean-excerpt convention) | role-match (CLI shape) + convention-match (row cap) |
| build-report writer (new function, likely `src/epra/warehouse/report.py` or similar, invoked from `Makefile`/CLI) (D-02) | service (report writer) | batch / file-I/O | `src/epra/ingest/validate.py` (`GateResult`/`ValidationReport`/`_write_report`/`run_gates`) | exact (same report-writer family) |
| `tests/unit/test_marts_contract.py` (D-07) | test (contract/schema-drift test) | request-response (DB query → diff) | `tests/test_raw_contracts.py` (ING-070 contract drift guard) | exact |
| `tests/unit/test_bootstrap_fixture_warehouse.py` | test (module unit test, subprocess or direct-call style) | batch | `tests/unit/test_scripts.py` (subprocess-driven CLI script tests) | exact |
| `dbt/models/sources.yml`, `dbt/macros/generate_schema_name.sql`, `dbt/models/staging/*.sql`, `dbt/models/marts/*.sql`, `dbt/macros/month_spine.sql`, `dbt/macros/test_accepted_range.sql`, `dbt/tests/*.sql`, `dbt/contracts/marts_contract.yml` | model / config (dbt SQL+YAML) | transform / CRUD (SQL views→tables) | `dbt/dbt_project.yml`, `dbt/profiles.yml`, `dbt/seeds/dim_strategy.csv` (committed skeleton) | exact (in-repo skeleton is the starting point; RESEARCH.md §Architecture Patterns 1–7 has SQL shapes) |
| `Makefile` `transform:` target | config (build orchestration) | batch | Sibling stubbed targets in same `Makefile` (`ingest:`, `validate-ingest:`) | exact (un-stub in place) |
| `.github/workflows/ci.yml` `dbt-check` job | config (CI pipeline) | event-driven (CI trigger) | `lint:`/`test:` jobs in same file; EN-070 `-m "not live"` split | exact |
| `docs/ADR/ADR-009..011.md` | doc (governance) | — | `docs/ADR/ADR-001..008` (any one, e.g. `ADR-006_validation-gate-scope-local-year.md`) | exact (structural template, not read in full here — reuse heading structure: Context/Decision/Consequences/Spec deviations) |

## Pattern Assignments

### `scripts/bootstrap_fixture_warehouse.py` (utility, batch/file-I/O)

**Analogs:** `scripts/oespi_reconcile.py` (CLI shape) + `tests/fixtures/entsoe/*_2024-01.parquet` (lean-excerpt convention, ≤200 rows per M1 `_MAX_FIXTURE_ROWS`) + `src/epra/ingest/_io.py` (atomic parquet write convention, referenced but not re-read here — see `_io.write_month`'s `.tmp` + `os.replace` pattern already used project-wide for every parquet writer)

**Docstring / spec-ID citation convention** (`scripts/oespi_reconcile.py` lines 1-15):
```python
"""ÖSPI double-entry reconciliation (ING-101).

Workflow: ...

Usage: ``python scripts/oespi_reconcile.py [--dir data/manual]``
Exit 0 on successful reconciliation, 1 on mismatch or missing input.

Implements: ING-101.
"""
```
For the new script, mirror this exactly but cite `Implements: SG-06 (ADR-010), D-03, D-04, D-05, D-06.` and document the CI-vs-local dual-consumer role (D-06: same generator feeds both).

**CLI + guard-flag pattern** (`scripts/oespi_reconcile.py` lines 17-27, 70-84):
```python
import argparse
from collections.abc import Sequence
from pathlib import Path

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="data/manual", type=Path)
    args = parser.parse_args(argv)
    ...
    return 0  # or 1 on failure — never raise past main()

if __name__ == "__main__":
    sys.exit(main())
```
Apply this shape, adding a `--force` flag per `03_MODULES.md`'s module contract ("must refuse to clobber real ingested data by default" — RESEARCH Security Domain / Known Threat Patterns table). Guard logic: check `data/raw/**` non-empty and abort unless `--force` is passed, mirroring `oespi_reconcile.py`'s own fail-fast-on-missing-input style (lines 76-79 of that file: check existence, print actionable error, `return 1`).

**Fixture-row-cap convention to reuse (not code, a constant):** `tests/test_raw_contracts.py` line 79: `_MAX_FIXTURE_ROWS = 200` — the *hand-authored* fixture convention. D-04's generator differs (writes a full window, not a capped fixture) but the generator's own **unit test** should still assert its output is bounded/reasonable for CI runtime, echoing this cap philosophy in spirit (document the deliberate exception per D-04's ADR-010).

**Determinism/seeding convention:** no existing generator module in this repo seeds; use Python stdlib `random.Random(seed)` or `numpy.random.default_rng(seed)` with a fixed module-level constant, following the "seed value is free (Claude's Discretion)" note in CONTEXT.md — but expose it as a named constant at module top (matches this repo's constant style, e.g. `validate.py` lines 137-176 `_PRICE_MIN_EUR_MWH`, `_ANNUAL_MEAN_RANGE_EUR_MWH` etc. — module-level `_CONSTANT` naming, ALL_CAPS with leading underscore for internal-only).

**Atomic write reminder:** every new parquet writer in this repo must go through `epra.ingest._io.write_month` (or an equivalent `.tmp` + `os.replace` pattern) — do not hand-roll a second parquet-writing path. `write_month`'s signature and dispatch-by-`key_column` behavior (`ts_utc` vs `date`) is directly reusable for the `data/raw/**` + `data/processed/**` synthetic writes D-04 requires.

---

### Build-report writer (D-02, `reports/warehouse/dbt_build_<date>.md`)

**Analog:** `src/epra/ingest/validate.py` — direct structural reuse of `GateResult`/`ValidationReport`/`_write_report`/`run_gates`.

**Module docstring + Implements citation convention** (lines 1-36):
```python
"""Ingestion validation gates — ``make validate-ingest`` (M1/M2).

Binding contract: SPEC-01 §8 ...
Results are written to ``reports/ingestion/validation_<date>.md``.

Gate summary (fail-fast per EN-061 — a failed gate raises, never warns):
- ING-080 ...
...
Implements: ING-080, ..., ING-111 (M2).
"""
```
For the M3 report, cite `Implements: D-02, D-05, D-06 (stand-in flags), DM-060..066 (test pass/fail counts).`

**Result/Report dataclass pattern** (lines 66-131) — reuse verbatim shape, adjust field semantics (dbt test results instead of gate predicates):
```python
@dataclass(frozen=True)
class GateResult:
    gate_id: str
    passed: bool
    summary: str
    evidence: pd.DataFrame | None = None

    def render_markdown(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"### {self.gate_id} — {status}", "", self.summary]
        if self.evidence is not None and not self.evidence.empty:
            lines += ["", "```", self.evidence.to_string(index=False), "```"]
        return "\n".join(lines)

@dataclass
class ValidationReport:
    results: list[GateResult] = field(default_factory=list)

    def add(self, result: GateResult) -> None: ...
    @property
    def all_passed(self) -> bool: ...
    def render_markdown(self, *, run_date: date | None = None) -> str:
        run_date = run_date or date.today()
        overall = "ALL GATES PASSED" if self.all_passed else "GATE FAILURE(S) — see below"
        header = [f"# Ingestion validation report — {run_date:%Y-%m-%d}", "", f"**Overall: {overall}**"]
        body = [result.render_markdown() for result in self.results]
        return "\n\n".join([*header, *body]) + "\n"
```
For the M3 build report, rename conceptually to e.g. `ModelBuildResult`/`BuildReport` — one row per dbt model or per DM-06x test — but the exact same `render_markdown`/`raise_if_failed`-style aggregation applies. Include per-year hourly row counts, month coverage, and 2022-08 reconciliation delta as `evidence` DataFrames (same `pd.DataFrame.to_string(index=False)` fenced-code rendering, lines 87-89).

**Report path + write pattern** (`_write_report`, lines 887-895):
```python
def _write_report(report: ValidationReport, settings: Settings) -> Path:
    reports_root = settings.paths.reports
    reports_root = reports_root if reports_root.is_absolute() else REPO_ROOT / reports_root
    ingestion_dir = reports_root / "ingestion"
    ingestion_dir.mkdir(parents=True, exist_ok=True)
    report_path = ingestion_dir / f"validation_{date.today():%Y-%m-%d}.md"
    report_path.write_text(report.render_markdown(), encoding="utf-8")
    return report_path
```
Direct copy-adapt: swap `"ingestion"` → `"warehouse"`, `"validation_"` → `"dbt_build_"`. Uses `settings.paths.reports` (already a `Settings` field per `epra.common.config`) — reuse, don't invent a new path field.

**Query-the-warehouse-after-build pattern:** use `epra.common.db.connect(settings, read_only=True)` (see `src/epra/common/db.py` lines 25-29) to pull the DM-06x sanity numbers (row counts, reconciliation delta) after `dbt build` completes — same read-only-connection idiom the D-07 contract test also uses.

**CLI `main()` + exit-code convention** (lines 940-965):
```python
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m epra.ingest.validate", description="...")
    parser.parse_args(argv)
    settings = load_settings()
    logfile = settings.paths.reports / "ingestion" / f"validate_{date.today():%Y-%m-%d}.log"
    common_logging.setup(logfile=logfile)
    try:
        run_gates(settings)
    except GateFailure as exc:
        logger.error("validation failed: %s", exc)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```
Reuse this exact `main()`/logging/exit-code shape for the build-report script (or CLI subcommand wired into `make warehouse`/`transform`).

---

### `tests/unit/test_marts_contract.py` (test, request-response / schema-diff)

**Analog:** `tests/test_raw_contracts.py` (ING-070 contract drift guard) — same conceptual role: fail loudly on drift between a committed contract and the actual artifact.

**Module docstring + citation convention** (lines 1-31):
```python
"""ING-070 raw contract drift guards.

Opens each committed §7 fixture parquet under `tests/fixtures/<source>/` and
asserts the exact column names, dtypes, and ... SPEC-01 §7 specifies. ...

Implements: ING-070.
"""
```
For the new test: `"""D-07 marts schema-contract drift guard. Diffs information_schema.columns for schema='marts' against the hand-authored dbt/contracts/marts_contract.yml (SPEC-02 §5). Implements: D-07, DM-060."""`

**Contract-table-as-module-constant pattern** (lines 52-61):
```python
_CONTRACTS: dict[str, tuple[list[str], set[str] | None]] = {
    "entsoe_prices_at": (["ts_utc", "price_eur_mwh", "resolution", "zone"], {"AT"}),
    ...
}
```
Adapt: load `dbt/contracts/marts_contract.yml` via `yaml.safe_load` (RESEARCH Pattern 6 / Security Domain: **always `safe_load`, never bare `load`**) rather than hardcoding a Python dict — the contract lives in YAML per D-07, but the *comparison* mechanics (per-table expected column list/order, `pytest.mark.parametrize` over table names) directly mirror this file's structure.

**Parametrized-per-dataset test pattern** (lines 86-95, 99-103):
```python
@pytest.mark.parametrize("dataset", sorted(_CONTRACTS))
def test_fixture_committed_and_bounded(dataset: str) -> None:
    path = _fixture_path(dataset)
    assert path.exists(), f"missing committed fixture: {path}"
    ...

@pytest.mark.parametrize("dataset", sorted(_CONTRACTS))
def test_fixture_exact_column_layout(dataset: str) -> None:
    own_columns, _zones = _CONTRACTS[dataset]
    frame = pd.read_parquet(_fixture_path(dataset))
    assert list(frame.columns) == [*own_columns, *_PROVENANCE_COLUMNS]
```
Apply directly: `@pytest.mark.parametrize("mart", sorted(contract))` iterating the 6 marts, asserting `information_schema.columns` name+type list matches the YAML per D-07's "editing any mart column name/type breaks it" requirement (RESEARCH Open Question 2 recommends name+type).

**DB access convention:** use `epra.common.db.connect(settings, read_only=True)` (see `db.py` above) — do not open a raw `duckdb.connect()` call; go through the shared helper, consistent with every other DB-touching module in this repo.

**REPO_ROOT convention** (`test_raw_contracts.py` line 40, 42):
```python
from epra.common.config import REPO_ROOT
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"
```
Reuse for locating `dbt/contracts/marts_contract.yml`: `CONTRACT_PATH = REPO_ROOT / "dbt" / "contracts" / "marts_contract.yml"`.

---

### `tests/unit/test_bootstrap_fixture_warehouse.py` (test, batch)

**Analog:** `tests/unit/test_scripts.py` (subprocess-driven CLI script test style).

**Subprocess-runner + fixture-tmp_path pattern** (lines 1-20, 40-47):
```python
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, cwd=REPO_ROOT, check=False,
    )

def test_oespi_reconcile_accepts_matching_entries(tmp_path: Path) -> None:
    ...
    result = _run("oespi_reconcile.py", "--dir", str(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
```
Apply directly for `bootstrap_fixture_warehouse.py`: run via subprocess against a `tmp_path`-redirected `data/` root (or call `main()`/the generator function directly in-process if the script exposes a testable function, consistent with `test_scripts.py`'s pattern of testing exit codes + stdout content + resulting file existence). Also assert the **guard behavior**: running twice without `--force` against a populated dir returns 1 (mirrors `test_oespi_reconcile_requires_both_entries`'s "missing input → return 1, actionable message" style, lines 62-65).

**Determinism assertion (new, no direct analog):** assert running the generator twice with the same seed produces byte-identical output (hash the written parquet, or compare DataFrames) — this is the one genuinely new assertion class this test needs; no existing test in the repo checks determinism directly, but `tests/unit/test_calendar.py`/`test_geosphere.py` (Community 92/64 per graph) may have adjacent "deterministic output" assertions worth a quick look at implementation time if the planner wants a second analog.

---

### dbt models/macros/tests/YAML (D-01–D-08, T3.01–T3.06)

**Analog:** the already-committed `dbt/` skeleton — no Python analog needed; RESEARCH.md §Architecture Patterns 1–7 (already read, not re-extracted here) has the concrete SQL/YAML shapes for `sources.yml`, `generate_schema_name.sql`, `month_spine.sql`, `test_accepted_range.sql`, the four singular tests, and the contract-diff pytest shape.

**Skeleton files confirmed present and correct** (read directly, not re-quoted — see `dbt/dbt_project.yml`, `dbt/profiles.yml`, `dbt/seeds/dim_strategy.csv` per CONTEXT.md "Reusable Assets"): materializations (`staging`→view, `marts`→table), schema names, relative warehouse path, all 6 strategy seed rows. Do not modify these three files; only add new files under `models/`, `macros/`, `tests/`, `contracts/`.

**Spec-ID citation convention for dbt YAML** (project-wide convention, per CONTEXT.md "Established Patterns" — M1/M2 used `Implements: ING-xxx` Python docstrings): mirror as YAML `description:` fields citing `DM-xxx`, e.g.:
```yaml
models:
  - name: fct_price_hourly
    description: "SPEC-02 §5 DM-040. Implements DM-060 (keys), DM-061 (ranges), DM-062 (row counts)."
```

---

### `Makefile` `transform:` target (config, batch)

**Analog:** sibling live targets in the same file (`ingest:`, `validate-ingest:`, lines 26-30 of `Makefile`):
```makefile
ingest:              ## M1 — SPEC-01 §4: incremental 45-day refresh (ING-041)
	$(UV) run python -m epra.ingest.entsoe --incremental

validate-ingest:     ## M1/M2 — SPEC-01 §§8-11 gates → reports/ingestion/
	$(UV) run python -m epra.ingest.validate
```
**Current stub to replace** (lines 42-43):
```makefile
transform:           ## M3 — dbt build (models + tests)
	@echo "ERROR: 'make transform' not implemented yet (M3 — SPEC-02)." >&2; exit 1
```
Replace body with `cd dbt && $(UV) run dbt build` (RESEARCH's own recommendation, "Wave 0 Gaps" list item), keeping the same `##`-comment doc-line convention. Leave `all:`/`refresh:` wiring (lines 63-65) untouched — `transform` is already a dependency there.

---

### `.github/workflows/ci.yml` `dbt-check` job (config, event-driven)

**Analog:** `lint:`/`test:` jobs in the same file (lines 13-34), plus the commented-out placeholder already present at line 36:
```yaml
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - run: uv venv && uv pip install -e ".[dev]"
      # EN-070: no network in CI tests; live suite excluded by marker.
      - run: uv run pytest -m "not live"

  # dbt-check:   # M3 — dbt build against tests/fixtures mini-warehouse (EN-080 job 3)
  # ssot-check:  # M6 — scripts/check_ssot_consistency.py (EN-080 job 4, GV-303)
```
New job: same `runs-on`/`checkout`/`setup-uv` steps, then add `run: uv run python scripts/bootstrap_fixture_warehouse.py` (D-04, network-free) followed by `run: cd dbt && uv run dbt build`. Uncomment/replace the `# dbt-check:` placeholder line, keep it as a genuinely separate job (not folded into `test:`) so it can be made a required check independently, matching the file's own job-per-concern structure. Update the top-of-file comment (line 2: "Job 3 (dbt fixture build) arrives with M3") once implemented.

---

## Shared Patterns

### Report-writer framework (`GateResult`/`ValidationReport`)
**Source:** `src/epra/ingest/validate.py` lines 66-131, 887-895
**Apply to:** the D-02 build-report script — reuse the dataclass + markdown-rendering + write-to-`reports/<subdir>/` shape wholesale.

### Contract-table-as-YAML + parametrized pytest diff
**Source:** `tests/test_raw_contracts.py` lines 52-61, 86-136
**Apply to:** `tests/unit/test_marts_contract.py` — same parametrize-over-dataset-name idiom, swapped to parametrize-over-mart-name reading from `dbt/contracts/marts_contract.yml` instead of a hardcoded dict.

### CLI script shape (`argparse` + `main(argv) -> int` + `sys.exit`/`raise SystemExit`)
**Source:** `scripts/oespi_reconcile.py` lines 17-27, 70-84; `src/epra/ingest/validate.py` lines 940-965
**Apply to:** `scripts/bootstrap_fixture_warehouse.py` — every new CLI script in this repo follows this exact `main(argv: Sequence[str] | None = None) -> int` + `if __name__ == "__main__": sys.exit(main())` (or `raise SystemExit(main())`) shape, never `print`+bare `exit()`.

### DuckDB access via shared helper
**Source:** `src/epra/common/db.py` lines 19-29
**Apply to:** build-report script and `test_marts_contract.py` — always `epra.common.db.connect(settings, read_only=True)`, never a raw `duckdb.connect(...)` call.

### Subprocess-based script testing
**Source:** `tests/unit/test_scripts.py` lines 13-20, 40-47
**Apply to:** `tests/unit/test_bootstrap_fixture_warehouse.py` — `_run()`-style subprocess helper against `tmp_path`, asserting `returncode`, stdout content, and resulting file state.

### `Implements: XXX-nnn` spec-ID citation
**Source:** every M1/M2 module docstring (e.g. `validate.py` line 34-35, `oespi_reconcile.py` line 14)
**Apply to:** every new Python file's module docstring (cite `D-0x`/`ADR-0xx`) and every new dbt model/macro YAML `description:` field (cite `DM-xxx`), per CONTEXT.md's "Established Patterns" note.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `docs/ADR/ADR-009..011_*.md` | doc | — | Not read in full this pass (out of code-pattern scope) — planner should open one existing `docs/ADR/ADR-0xx_*.md` (e.g. `ADR-006_validation-gate-scope-local-year.md`, already cited in CONTEXT.md canonical refs) directly for the Context/Decision/Consequences/Spec-deviations heading template; trivial structural reuse, no extraction needed here. |
| Determinism/seed-hash assertion in `test_bootstrap_fixture_warehouse.py` | test | — | No existing test in this repo asserts byte-identical regeneration under a fixed seed; nearest adjacent candidates (`tests/unit/test_calendar.py`, `tests/unit/test_geosphere.py`) were not opened this pass — worth a quick look at implementation time but not blocking. |

## Metadata

**Analog search scope:** `src/epra/ingest/`, `src/epra/common/`, `tests/`, `tests/unit/`, `scripts/`, `Makefile`, `.github/workflows/ci.yml`, `dbt/` (skeleton only)
**Files scanned/read in full or in relevant excerpt:** `src/epra/ingest/validate.py`, `tests/test_raw_contracts.py`, `tests/unit/test_io.py` (partial), `tests/unit/test_scripts.py`, `scripts/oespi_reconcile.py`, `scripts/generate_golden_metrics.py`, `src/epra/common/db.py`, `Makefile`, `.github/workflows/ci.yml`
**Pattern extraction date:** 2026-07-24
