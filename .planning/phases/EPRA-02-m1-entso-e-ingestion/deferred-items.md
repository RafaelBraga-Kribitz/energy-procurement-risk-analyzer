# Deferred Items — EPRA-02 M1 ENTSO-E Ingestion

Out-of-scope discoveries logged during plan execution. Not fixed per the
executor's scope boundary (only auto-fix issues directly caused by the
current task's changes).

## From 02-02 (raw parquet writer `_io`)

- **`tests/unit/test_config.py::test_entsoe_token_fails_fast_when_unset` fails
  in this environment.** Pre-existing, unrelated to `_io.py`/`test_io.py`
  (last touched in the M0 bootstrap commit `c043933`, before any Phase 2
  plan). Root cause: a real `ENTSOE_API_TOKEN` is present in the repo's
  `.env` file (per STATE.md, the token was added 2026-07-21 for M1
  backfill); `monkeypatch.delenv("ENTSOE_API_TOKEN")` removes it from
  `os.environ`, but `entsoe_token()` then calls `load_dotenv(REPO_ROOT /
  ".env")`, which repopulates it from `.env` since the var is no longer
  present in the environment — so `entsoe_token()` returns the real token
  instead of raising `RuntimeError`. Needs either a `monkeypatch` of
  `load_dotenv`/the `.env` path, or a `tmp_path`-redirected env file, in
  `test_config.py` — out of scope for `02-02` (that file is not in this
  plan's `files_modified`).

## From 02-05 (ingest orchestration, CLI, Makefile)

- **`make lint` fails on `ruff format --check tests/unit/test_aggregate_hourly.py`.**
  Pre-existing, last touched in the `02-04` commit `b05024c` (this plan's
  `files_modified` never lists it and no diff was made to it here). `ruff
  format` would reformat it; not fixed — out of scope for `02-05`.
- **`tests/unit/test_config.py::test_entsoe_token_fails_fast_when_unset` still
  fails** in this environment for the same `02-02`-logged reason above;
  reconfirmed unaffected by `02-05`'s changes.

## From 02-06 (validation gate framework, `validate-ingest`)

- **`make lint` still fails on `ruff format --check tests/unit/test_aggregate_hourly.py`**
  and **`tests/unit/test_config.py::test_entsoe_token_fails_fast_when_unset` still
  fails** — both reconfirmed unaffected by this plan's changes (`git status`/`git
  diff` show zero delta on either file before or after 02-06's commits).
