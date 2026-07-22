# Deferred Items — Phase EPRA-03 (m2-auxiliary-data)

Out-of-scope discoveries logged during plan execution (not fixed — scope
boundary rule: only auto-fix issues caused by the current task's changes).

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Formatting | `uv run ruff format --check src tests scripts` reports `tests/unit/test_io.py` would be reformatted. Pre-existing — file last touched by plan 03-01 (commit `58c69ca`), not modified by 03-02. | Open | 03-02 |
