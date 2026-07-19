"""Calendar generation — hourly spine with Austrian/Styrian holidays (M2).

Not yet implemented. Binding contract: SPEC-01 §11. Key points:

- Output ``data/raw/calendar/calendar.parquet``, one row per UTC hour from
  2019-01-01 to the end of the forward-risk window, columns (ING-110):
  ``ts_utc, date_local (Europe/Vienna), hour_local, dow_local (0=Mon),
  is_weekend, is_holiday_at, is_peak_hour, year_local, month_local``.
- Holidays via the ``holidays`` package, ``subdiv='6'`` for Styria (ING-110).
- Peak rule is ``epra.common.timeutil.is_peak_hour`` — do not re-implement.
- Tests (ING-111): 2024 national holiday count; Jan 1 / May 1 / Dec 25 always
  holidays; peak definition checked on a known Monday and Sunday.

Implements (when built): ING-110..111; feeds dim_calendar (SPEC-02 §4).
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from epra.common.config import Settings

_MSG = "M2 not implemented yet — build per SPEC-01 §11 (see module docstring)"


def build_calendar(settings: Settings) -> pd.DataFrame:
    """Return the hourly calendar frame per ING-110 (also persisted to parquet)."""
    raise NotImplementedError(_MSG)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m epra.ingest.calendar`` (ING-002)."""
    raise NotImplementedError(_MSG)


if __name__ == "__main__":
    raise SystemExit(main())
