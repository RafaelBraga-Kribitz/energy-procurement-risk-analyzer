"""CI gate GV-303: README/EXEC_SUMMARY numbers must match the SSOT (M6/M7).

Not yet implemented. Binding contract: SPEC-08 §3 (GV-303). Parses README.md
and reports/EXEC_SUMMARY.md for numeric literals adjacent to SSOT units (EUR,
EUR/MWh, %, hours, M) and verifies each matches an SSOT value within the
rounding documented HERE (README may round; SSOT holds full precision).
Non-result numerics (years, section numbers, config echoes) belong in
``scripts/ssot_whitelist.txt`` — every entry with an inline comment saying why.

Also enforces SSOT freshness for result-touching PRs (SPEC-08 §4):
``updated_at`` newer than the newest modified results file.

Implements (when built): GV-303.
"""

from __future__ import annotations

import sys

sys.exit("not implemented yet — M6/M7 (SPEC-08 §3 GV-303); see module docstring")
