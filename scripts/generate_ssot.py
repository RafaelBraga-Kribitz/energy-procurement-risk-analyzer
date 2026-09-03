"""Generate reports/NUMERIC_SSOT.md — the ONLY source of quoted numbers (M6).

Thin CLI shell around ``epra.report.ssot.assemble``. Does not recompute costs
and does not call simulate (D-03, D-16).

Implements: GV-301, GV-302.
"""

from __future__ import annotations

from epra.report.ssot import main

if __name__ == "__main__":
    raise SystemExit(main())
