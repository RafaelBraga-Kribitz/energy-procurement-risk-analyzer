# 08 — DESIGN PATTERNS: exactly where each belongs

The codebase is deliberately function-first. Patterns below are prescriptive:
use them where named, and do not import ceremony (class hierarchies, DI
frameworks) anywhere else.

| Pattern | Where it belongs | Why / shape |
|---------|------------------|-------------|
| **Functional core / imperative shell** | Everywhere; canonical in `consumer.profile`, `strategies.*`, `analytics.*` | Pure computation functions on frames (unit-testable, deterministic); thin `run()`/CLI shells do I/O. The shell contains zero business logic. |
| **Pure functions** | All formula code: weights, gate checks, anchors, strategy costs, summaries | No I/O, no mutation of inputs, no clock/env access. This is what makes goldens and determinism tests possible. |
| **Configuration objects** | `epra.common.config` pydantic models passed down; never re-read YAML | Already implemented; extend the models, never bypass them (EN-040, LP-002, ST-003). |
| **Pipeline (explicit staged)** | Makefile targets = stages; inside M1: fetch → parse → frame → persist | Each stage's output contract is a SPEC table; stages composable and re-runnable (EN-050). |
| **Repository (data access)** | `strategies`/`analytics` mart readers (T5.01/T6.01): all SQL in one reader layer per package | Modules consume frames, never write SQL inline mid-computation; keeps the mart interface swappable and the SQL greppable. |
| **Strategy (dispatch table, not classes)** | `strategies.retrospective`: `{"S1": cost_s1, "S2": cost_s2, ...}` keyed by `dim_strategy` ids | Four fixed families (O-7); a dict of pure functions beats an ABC hierarchy at this size. Adding a class hierarchy here is over-engineering (AP-13). |
| **Factory (tiny)** | `report` kit `new_figure()/finalize()`; profile selection by `profile_name` | Centralizes RP-70x conformity and LP-030 variant creation. |
| **Builder** | NOT used | Config objects + pure functions cover construction; a Builder would be ceremony. |
| **Dependency injection (manual, by argument)** | Pass `Settings`/frames/RNG into functions; no DI container | `simulate(cells, rng_seed=…)` — the seed/inputs are arguments, so tests inject; nothing global. |
| **Retry** | ONLY `ingest._fetch` (tenacity, ING-006) | Retrying anywhere else hides real failures (EN-061). |
| **Caching** | ONLY `ingest` HTTP cache (ING-009) + `@cache` on config loaders | No memoization inside computation paths — recompute; determinism beats speed at this scale. |
| **Circuit breaker** | NOT used (ADR required if ENTSO-E instability ever demands it) | Retry + fail-fast suffices for a monthly batch pipeline. |
| **State machine** | Only conceptually: milestone gates ([10_VALIDATION_GATES.md](10_VALIDATION_GATES.md)); HMM states are data, not code states | No workflow-engine code. |
| **Composition over inheritance** | Whole repo: zero inheritance except pydantic BaseModel/frozen dataclasses | Any new class hierarchy needs a reason in review; default is functions + dataclasses. |
| **Contract tests** | Raw parquet (ING-070), mart schemas (T3.05), exports (DM-070) | Frozen interface = committed schema + a test that diffs reality against it. This is the project's central integration pattern. |
| **Golden master** | Profile checksum (LP-040), strategy matrix (ST-601) | Regenerated only by script + human approval (EN-072). |
