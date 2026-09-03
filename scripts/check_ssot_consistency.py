"""CI gate GV-303: README/EXEC_SUMMARY numbers must match the SSOT (M6/M7).

Thin CLI shell around ``epra.report.ssot_check.check``. Rounding is
``Decimal`` ``ROUND_HALF_UP`` (ADR-016) — never Python ``round``.

Implements: GV-303, ADR-016, EN-080.
"""

from __future__ import annotations

from epra.report.ssot_check import main

if __name__ == "__main__":
    raise SystemExit(main())
