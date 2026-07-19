"""Export marts to exports/*.csv for Power BI (M7).

Not yet implemented. Binding contract: SPEC-02 §7 (file list + source marts,
DM-070 contract tests). CSVs are UTF-8, ISO dates, ``.`` decimal. Power BI
reads ONLY from exports/ — never from DuckDB directly.

Implements (when built): DM-070, SPEC-02 §7 table.
"""

from __future__ import annotations

import sys

sys.exit("not implemented yet — M7 (SPEC-02 §7 / DM-070); see module docstring")
