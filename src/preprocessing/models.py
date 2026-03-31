"""Contracts for preprocessing results."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PreprocessingResult:
    """Canonical dataframe plus traceable information about applied steps."""

    dataframe: pd.DataFrame
    applied_steps: tuple[str, ...]
    row_count_before: int
    row_count_after: int
