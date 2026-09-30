"""Generate reports/NUMERIC_SSOT.md — the ONLY source of quoted numbers (M6).

Not yet implemented. Binding contract: SPEC-08 §3 (GV-301..302). Reads computed
parquet/DuckDB outputs (never recomputes) and writes a single markdown table:
``key | value | unit | tag | produced_by | updated_at``. Minimum key set is
GV-302 verbatim. Tags per Charter §5 (VERIFIED / CALIBRATED / SIMULATED); a
VERIFIED value may never depend on a CALIBRATED input (E-2).

Implements (when built): GV-301, GV-302, E-3.
"""

from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point — fails loudly until its milestone lands (AGENTS.md M0 rule)."""
    raise NotImplementedError(
        "not implemented yet — M6 (SPEC-08 §3 GV-301/302); see module docstring"
    )


if __name__ == "__main__":
    raise SystemExit(main())
