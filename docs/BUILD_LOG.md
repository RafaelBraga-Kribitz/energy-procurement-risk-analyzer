# BUILD_LOG (append-only, per AGENTS.md W-5)

One entry per milestone: date, what shipped, gate evidence, open questions.

---

## 2026-07-19 — M0 Bootstrap (complete) + breadth foundation

**Shipped**

- Repo layout exactly per SPEC-07 §2 (empty dirs with `.gitkeep`); git initialized.
- `pyproject.toml`: pinned deps per SPEC-07 §3, ruff (line 100), `mypy --strict`
  on `src/epra`, pytest with `--cov-fail-under=80` (EN-071); `uv.lock` committed
  (EN-030).
- Makefile per SPEC-07 §5 — `setup/lint/test` real; all pipeline targets fail
  loudly with their milestone ("not implemented", per AGENTS.md M0).
- `.pre-commit-config.yaml` (EN-003) incl. implemented
  `scripts/check_no_token_in_code.py` token guard (tested).
- CI `ci.yml` with lint + test jobs (EN-080 jobs 1–2; jobs 3–4 land with M3/M6).
- Config layer: `config/settings.yaml` (EN-040), `config/consumer_profile.yaml`
  (SPEC-03 §6 verbatim), `config/strategies.yaml` (SPEC-05 §8 verbatim), all
  loaded through validated pydantic models in `epra.common.config`
  (`load_settings` / `load_consumer_profile` / `load_strategy_config` /
  `entsoe_token` fail-fast per ING-021).
- `epra.common` implemented: `logging` (EN-060), `timeutil` (UTC/Vienna doctrine,
  peak-hour rule ING-110, DST hour counts), `db` (DuckDB helper, DM-001).
- `epra.report.format` (RP-703) and `epra.report.style` (RP-701/704, Okabe-Ito,
  fixed strategy colors) implemented and tested.
- `scripts/oespi_reconcile.py` (ING-101) implemented and tested — the M2 human
  transcription workflow is unblocked.
- Every other module exists as a typed stub whose docstring carries its binding
  spec contract + REQ IDs and whose body raises `NotImplementedError` naming its
  milestone (tested: `tests/unit/test_stubs_fail_loudly.py`).
- dbt skeleton: `dbt_project.yml`, committed `profiles.yml` (relative DuckDB
  path), `seeds/dim_strategy.csv` (SPEC-02 §4 verbatim), `dbt/README.md` M3 map.
- Governance: ADR-001 (light governance; governance-bootstrap kit NOT vendored —
  Charter O-5 / SPEC-08 §7), ADR-002 (typing stubs for mypy strict).
  README + LIMITATIONS skeletons with zero untagged/unSSOT'd numbers.

**Gate evidence** (M0: `make setup && make lint && make test`)

- `uv run ruff check` / `ruff format --check` / `mypy` — recorded in the M0
  commit; see CI once a remote exists.
- `uv run pytest` — all tests green, coverage above the 80% gate.

**Open questions / next steps (in build order)**

> Superseded in detail by `docs/EXECUTION_BLUEPRINT/` (2026-07-19, second
> entry below) — items remain valid; the blueprint decomposes them into tasks.

1. **Human, day-0 (R-1):** request the ENTSO-E API token now (SPEC-01 §2) —
   M1 blocks on it; M2 (GeoSphere/ÖSPI/calendar, no auth) can proceed meanwhile.
2. **Human/M2:** transcribe ÖSPI twice (entry1/entry2), run
   `python scripts/oespi_reconcile.py`; series/methodology choice needs an ADR
   (ING-102).
3. **M1 agent:** build `ingest/entsoe.py` + `ingest/validate.py` per module
   docstrings; fixtures first (EN-070), incl. the 15-min aggregation fixture
   (ING-062) and DST fixtures.
4. **M2 agent:** GeoSphere discovery (ING-091) writes `station_id` into
   `config/settings.yaml` + ADR-003; then flip
   `test_settings_geosphere_station_pending_discovery` to assert the chosen id.
5. **M3:** dbt models per `dbt/README.md`; add CI job 3 (fixture warehouse).
6. No remote configured yet — when the GitHub repo exists, push `main`, protect
   it with CI, and add the `ENTSOE_API_TOKEN` secret (EN-041); `refresh.yml`
   (EN-081..083) lands with M7.

---

## 2026-07-19 — Execution Blueprint (planning deliverable, owner-requested)

**Shipped:** `docs/EXECUTION_BLUEPRINT/00..14` — the repository's execution
operating manual: master plan with authority hierarchy + global DoR/DoD +
agent session protocol; phase roadmap with entry/exit/rollback; full WBS
(TP.01–TP.02, T1.01–T7.07, ~47 session-sized tasks with objectives, deps,
validation, acceptance criteria); module/class/function contracts; dependency
graphs + critical path + token-window parallel plan; per-milestone
implementation guides (client strategy, TZ recipes, investigation protocols,
bootstrap vectorization equivalence, SSOT/checker designs); checklists;
measurable quality + coding standards; pattern/anti-pattern catalogs (AP-01..22);
consolidated gate matrix; runnable DL-1..10 release script; extended risk
register (RB-9..18); traceability matrix; and 18 registered specification gaps
(SG-01..18) each with a proposed decision pending ADR adoption.

**Governance note:** the blueprint is a planning artifact subordinate to
Charter > SPEC > ADR (declared in 00_MASTER_PLAN §0.1); it introduces no new
gates, CI jobs, or ceremony (Charter O-5 respected).

**Open questions:** SG-01..SG-18 proposals await ADR adoption at their
scheduled tasks; token ETA ~2026-07-22 (TP.01); ÖSPI transcription (T2.05)
can start any time.
