# 09 — ANTI-PATTERNS: automatic PR rejection list

Each entry: what it looks like → what to do instead. Reviewers scan this list
per PR (checklist 6.2). "AP" ids are referenced in reviews.

| ID | Anti-pattern | Detection | Correct alternative |
|----|--------------|-----------|---------------------|
| AP-01 | **Invented/filled data** — interpolating a missing price, extrapolating ÖSPI, "reasonable defaults" for gaps | any fill logic outside ING-063/DM-020 | NULL stays NULL + documented exclusion (A-2, P-1) |
| AP-02 | **Gate massaging** — widening ranges, adding tolerances, try/except around a gate to keep pipeline green | diff on gate constants; except blocks near gates | investigate per guide protocols; widening only via ADR |
| AP-03 | **Magic numbers** — thresholds/factors/seeds inline in code | grep for numeric literals in `src/` outside tests/constants | config YAML or a named module constant with REQ ID comment (LP-002, ST-003) |
| AP-04 | **Hardcoded paths** — `"data/raw/…"` strings scattered | grep `data/` in `src/` outside `config.py` defaults | `settings.paths` only |
| AP-05 | **Ad-hoc timezone math** — `.tz_localize`, `.astimezone`, `+ timedelta(hours=1)` for TZ purposes outside `timeutil`/`dim_calendar` | grep tz calls | `timeutil` helpers; local attributes only from `dim_calendar` (DM-011, T-1) |
| AP-06 | **Hidden state / mutable globals** — module-level mutable caches, singletons carrying data between calls | module-level mutables | pass state as arguments; frozen dataclasses |
| AP-07 | **Silent failure / swallowed exceptions** — `except Exception: log.warning(...)`, bare except, warn-and-continue on contract violations | grep `except` blocks | raise with context (EN-061); warnings only for non-contract anomalies |
| AP-08 | **Lookahead leakage** — S3 price touching year-Y data, bootstrap seeing the future, calibration using post-2019 values | ST-503 test + review of every date filter | lock-window filters asserted by tests; document every date boundary |
| AP-09 | **Independent draws of coupled series** — bootstrapping prices and ÖSPI separately | review of ST-401 step 2 implementation | draw the month once, take both series from it (T-6) |
| AP-10 | **SSOT bypass** — typing a result number into README/EXEC/captions | GV-303 checker + review | copy from NUMERIC_SSOT.md only (A-6, E-3) |
| AP-11 | **Spec drift** — implementing "improved" formulas (log returns! different HMM! extra sensitivities!) | traceability check: behavior ↔ REQ ID | spec verbatim; disagreement → ADR proposal, never silent (A-1, T-3) |
| AP-12 | **Scope creep** — forecasting, apps, extra strategies, extra analytics, heavier governance | Charter §4.2 list | one line under README "Future work" and move on (A-3) |
| AP-13 | **Over-engineering** — class hierarchies for strategies, DI containers, plugin systems, premature abstractions | new ABCs/frameworks in diff | dispatch tables + pure functions ([08_PATTERNS.md](08_PATTERNS.md)) |
| AP-14 | **Copy-paste logic** — second implementation of peak-hour rule, ÖSPI translation, chart styling, gate framework | grep for formula fragments | single owner module (timeutil / calibration / report kit / validate) |
| AP-15 | **Notebook-driven production** — logic living in notebooks, results pasted from notebook runs | any `.ipynb` producing published numbers | notebooks are optional scratch (SPEC-07 §3), never load-bearing |
| AP-16 | **Unseeded/ambient randomness** — `np.random.*` module calls, `random.*`, seed from time | grep `np.random.` (must be `default_rng(seed)` only) | one seeded Generator passed explicitly (A-4, ST-401) |
| AP-17 | **Circular imports / layer violations** — analytics importing ingest, strategies importing analytics module code | import graph review (law in [04_DEPENDENCIES.md](04_DEPENDENCIES.md) §4.1) | data interfaces (marts/parquet), not code imports |
| AP-18 | **Config duplication** — same constant in YAML and code, or two YAMLs disagreeing | drift-guard tests in `test_config.py` | one owner file; tests pin spec-critical values |
| AP-19 | **Mixed-milestone PRs** — "while I was here" changes from another milestone | PR diff scan | one milestone, one PR (A-5); park extras as WBS notes |
| AP-20 | **Golden laundering** — regenerating goldens to make a failing change pass without explanation | golden file diff in PR without ADR/PR rationale | `generate_golden_metrics.py` + explicit diff + human approval (EN-072, AGENTS §2.6) |
| AP-21 | **Premature optimization** — chunk parallelization, caching layers, clever vectorization before a budget is exceeded | any perf work without a measured violation of §7.2 | measure first; budgets in [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md) |
| AP-22 | **Token leakage** — token in code, logs, fixtures, URLs, error messages, commit history | guard script + `_fetch` assertion | env-only (A-7); on any leak: STOP, tell human to rotate |
