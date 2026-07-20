# Coding Conventions

**Analysis Date:** 2026-07-20

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (`timeutil.py`, `forward_risk.py`, `oespi_reconcile.py`)
- Test files: `test_<area>.py` under `tests/unit/` (`test_timeutil.py`, `test_stubs_fail_loudly.py`)
- Scripts: `snake_case.py` under `scripts/` (`check_no_token_in_code.py`, `generate_ssot.py`)
- Config: `snake_case.yaml` under `config/` (`settings.yaml`, `consumer_profile.yaml`)
- Package layout: `src/epra/<layer>/` — `common`, `ingest`, `consumer`, `analytics`, `strategies`, `report`

**Functions:**
- `snake_case` for all functions (`to_utc`, `load_settings`, `build_profile`, `run_gates`)
- No special async prefix (project is sync I/O)
- CLI entrypoints named `main(argv: Sequence[str] | None = None) -> int`
- Pipeline entrypoints often named `run(settings: Settings) -> None` (analytics/strategies)
- Private helpers: leading underscore (`_read_yaml`, `_interpolate_hex`, `_MSG`)

**Variables:**
- `snake_case` for locals and parameters
- `UPPER_SNAKE_CASE` for module constants (`PEAK_START_HOUR`, `FIGSIZE`, `LOG_FORMAT`, `STRATEGY_COLORS`)
- Physical quantities include units in the name (`price_eur_mwh`, `annual_consumption_mwh`, `fixed_premium_eur_mwh`) — never bare `price`
- Keyword-only args after `*` when optional flags matter (`is_holiday: bool = False`, `read_only: bool = False`)

**Types:**
- Pydantic models: `PascalCase` ending in `Cfg` for config (`Settings`, `ZoneCfg`, `ConsumerProfileCfg`)
- Frozen base: `_Frozen` with `ConfigDict(frozen=True, extra="forbid")` in `src/epra/common/config.py`
- Prefer `X | None` / `list[str]` (PEP 604 / builtins) over `Optional` / `List`
- Use `from __future__ import annotations` at the top of every module

## Code Style

**Formatting:**
- Ruff format (via `ruff-format` pre-commit hook in `.pre-commit-config.yaml`)
- Line length 100 (`[tool.ruff]` in `pyproject.toml`)
- Target Python 3.12
- Double quotes for strings (ruff format default)
- Trailing commas where ruff expects them

**Linting:**
- Ruff select: `E`, `F`, `W`, `I`, `UP`, `B`, `C4`, `SIM`, `RUF` (EN-002)
- Allowed confusables for spec math in docstrings: `×`, `−`, `α`, `β`
- mypy `--strict` on `src/epra` only; `ignore_missing_imports` for `entsoe.*`, `hmmlearn.*`, `arch.*`, `statsmodels.*`
- Zero `# type: ignore` without a reason comment; tests may use `# type: ignore[...]` for deliberate bad fixtures
- Run: `make lint` → `ruff check` + `ruff format --check` + `mypy`

**Function length:**
- Keep functions under ~60 lines (AGENTS.md W-3); pipelines are compositions, not monoliths
- Module length advisory ≤ 500 lines (`docs/EXECUTION_BLUEPRINT/07_QUALITY_STANDARDS.md`)

## Import Organization

**Order (ruff isort / I rules):**
1. `from __future__ import annotations`
2. Stdlib (`collections.abc`, `datetime`, `logging`, `pathlib`, `typing`)
3. Third-party (`pandas`, `pydantic`, `yaml`, `duckdb`)
4. First-party absolute (`from epra.common.config import Settings`)

**Grouping:**
- Blank line between stdlib / third-party / first-party
- No `import *`
- No relative imports beyond one package-local alias when needed; prefer absolute `epra.*`
- Heavy libs (`hmmlearn`, `arch`, `matplotlib`) stay inside the modules that use them — never in `common/`

**Path Aliases:**
- Not applicable — installable package `epra` via `src/` layout (`[tool.hatch.build.targets.wheel] packages = ["src/epra"]`)
- Import as `from epra.<layer>.<module> import ...`

**Layer ownership (do not cross):**
- `common/` — shared infra only; imports nothing from other `epra` packages
- `ingest/` — source → `data/raw/`
- `dbt/` — raw → marts
- `consumer` / `analytics` / `strategies` — marts → results
- `report/` — results → artifacts
- `scripts/` — CLI shells over `epra` functions

## Error Handling

**Patterns:**
- Fail fast with explicit exceptions and expected-vs-actual messages
- Invalid programmer/input state → `ValueError` (naive datetimes in `timeutil.py`, bad YAML shape)
- Missing/misconfigured secrets → `RuntimeError` (`entsoe_token()` in `config.py`)
- Unimplemented milestone stubs → `NotImplementedError` with milestone id in the message (`"M1 not implemented yet…"`)
- Validation gates → raise on first hard failure (EN-061); never warn-and-continue past a contract
- Scripts may `raise SystemExit(...)` or return non-zero exit codes for CLI failures (`oespi_reconcile.py`, `check_no_token_in_code.py`)

**Error Types:**
- Today: stdlib exceptions only in implemented code
- Prescribed for new packages (`07_QUALITY_STANDARDS.md`): package-specific subclasses (`IngestAuthError`, `ContractError`, `GateFailure`, …) with a package base — add when implementing M1+
- Never catch to swallow a contract failure; never widen a validation gate without an ADR (A-2)

**Secrets:**
- `ENTSOE_API_TOKEN` only via env / `.env` through `entsoe_token()` — never log, print, or commit (A-7)
- Pre-commit + `scripts/check_no_token_in_code.py` block `securityToken=` literals

## Logging

**Framework:**
- Stdlib `logging` via `epra.common.logging.setup()` (`src/epra/common/logging.py`)
- Format: `%(asctime)s %(levelname)s %(name)s %(message)s` (EN-060)
- Default level INFO to stdout; optional file handler for ingestion logs

**Patterns:**
- Per module: `logger = logging.getLogger(__name__)` (prescribed; use when adding ingest/pipeline code)
- Call `setup()` at pipeline boundaries; it is idempotent (replaces handlers, does not stack)
- One INFO per pipeline step with counts; per-request lines per ING-008
- No `print()` inside `src/epra/` — scripts may print user-facing CLI output
- Never log the ENTSO-E token

## Comments

**When to Comment:**
- Explain *why* (DST UTC subtraction pitfall, why window end is absent from config)
- Cite trap IDs and REQ IDs inline (`T-1`, `T-4`, `ING-030`, `RP-701`)
- Avoid restating obvious code

**Docstrings:**
- Module docstring: contract summary + "Implements: …" / "Implements (when built): …" REQ IDs (W-2)
- Public functions: one-line summary + `Implements: <REQ IDs>` where applicable
- Greppable: `grep -r "ING-063" src tests`
- No redundant `@param` prose for obvious typed signatures
- If reality forces a deviation: ADR (SPEC-08) + reference ADR in the docstring (A-1)

**TODO Comments:**
- Zero `TODO`/`FIXME` in merged code — open work lives in WBS / `docs/BUILD_LOG.md`
- Milestone stubs use `NotImplementedError` + module docstring, not TODO markers

## Function Design

**Size:**
- ≤ ~60 lines; extract helpers; one abstraction level per function

**Parameters:**
- Inject `Settings` / config objects — do not re-read YAML ad hoc (`load_settings` is the only YAML entry)
- Prefer explicit typed params; use keyword-only for flags
- New config keys: pydantic model + YAML + drift test in the same commit

**Return Values:**
- Explicit returns; early raise for guard clauses
- CLI `main` → `int` exit code; `__main__` blocks use `raise SystemExit(main())`
- Stubs raise; never return empty stand-ins that look like success

## Module Design

**Exports:**
- Named functions and types at module level — no default exports
- Package `__init__.py` files are short package docs, not barrel re-exports (see `src/epra/common/__init__.py`, `src/epra/ingest/__init__.py`)
- Import from the concrete module: `from epra.common.timeutil import to_utc`

**Barrel Files:**
- Do not add heavy re-export barrels; keep package inits documentation-only unless a clear public API is needed
- Avoid circular imports; layer law prevents `common` ↔ domain cycles

**Determinism:**
- Seeded stochastic steps only (e.g. `forward.seed == 42`); no wall-clock / locale / filesystem-order dependence in analytics
- Gaps stay `NULL` — never invent prices or indices (A-2)

---

*Convention analysis: 2026-07-20*
*Update when patterns change*
