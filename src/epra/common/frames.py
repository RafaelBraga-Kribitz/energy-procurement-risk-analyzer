"""Typed scalar access into DataFrames (pandas-stubs types ``.loc`` cells as a
broad union, which mypy --strict rejects in arithmetic)."""

from __future__ import annotations

from collections.abc import Hashable
from typing import cast

import pandas as pd


def scalar(frame: pd.DataFrame, row: Hashable, column: Hashable) -> float:
    """``float(frame.loc[row, column])`` with a type mypy accepts."""
    return float(cast(float, frame.at[row, column]))
