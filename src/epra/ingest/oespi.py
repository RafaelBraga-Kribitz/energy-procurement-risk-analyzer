"""ÖSPI loader — hand-curated monthly index CSV (M2).

Not yet implemented. Binding contract: SPEC-01 §10. Key points:

- There is NO machine API. The human transcribes the Austrian Energy Agency's
  published monthly values (Base + Peak, index base 2006 = 100) into
  ``data/manual/oespi_monthly.csv`` — TWICE (double-entry, ING-101), reconciled
  by ``scripts/oespi_reconcile.py`` (already implemented).
- Schema (ING-100): ``month,oespi_base,oespi_peak,source_url,retrieved_at``
  with ``month`` = YYYY-MM. Values are transcribed real data — never invented
  (A-2, P-1).
- Methodology break warning (ING-102): use ONE consistent series; the choice
  requires an ADR. Peak unavailability triggers ING-104 base-only fallback.
- Gates (ING-103): continuous months, positive values, 2022 peak ≥ 3× the 2019
  mean, month-over-month change within ±60%.

Implements (when built): ING-100, ING-102..104 (ING-101 lives in scripts/).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from epra.common.config import Settings

_MSG = "M2 not implemented yet — build per SPEC-01 §10 (see module docstring)"


def load_oespi(settings: Settings) -> pd.DataFrame:
    """Load + gate-check the reconciled ÖSPI CSV; returns month-indexed frame."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.oespi`` — validate the committed CSV (ING-103)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
