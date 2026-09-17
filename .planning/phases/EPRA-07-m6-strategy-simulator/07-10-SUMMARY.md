---
phase: EPRA-07-m6-strategy-simulator
plan: 10
subsystem: strategies
tags: [st-601, makefile, build-log]

requires:
  - phase: EPRA-07-m6-strategy-simulator
    provides: assemble ssot_check forward_risk
provides:
  - synthetic ST-601 golden Makefile simulate/ssot BUILD_LOG M6
affects: [EPRA-07-m6-strategy-simulator verify-work]

key-files:
  created:
    - src/epra/strategies/_golden.py
    - tests/golden/strategy_annual_summary.json
    - tests/test_golden_strategies.py
    - tests/unit/test_strategies_gates.py
  modified:
    - scripts/generate_golden_metrics.py
    - Makefile
    - docs/BUILD_LOG.md
    - tests/unit/test_stubs_fail_loudly.py

key-decisions:
  - "Golden is synthetic engine contract (D-19); not Austrian market evidence"
  - "generate_golden_metrics.py returns 1 on dirty git status --porcelain"
  - "make simulate = retrospective then forward_risk; ssot = generate_ssot.py; no dbt"
  - "M7 charts stub remains; ST-602(a) real warehouse is operator"

requirements-completed: [ST-601, ST-405, ST-603, EN-050, D-03, D-19]

coverage:
  - id: D1
    description: "ST-601 JSON, dirty refuse, ST-405 identity, Makefile CLIs, M7-only stubs"
    requirement: "ST-601"
    verification:
      - kind: unit
        ref: "tests/test_golden_strategies.py"
        status: pass
    human_judgment: false
---

# Plan 07-10 Summary

Synthetic ST-601 golden, Makefile `simulate`/`ssot`, and BUILD_LOG M6 are in.
Full suite: **392 passed**, 2 skipped, coverage **92.55%**.
