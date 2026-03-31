"""Result contracts for orchestration pipelines."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..metrics import MetricsBundle
from ..reporting import MarketingReport


@dataclass(frozen=True)
class MarketingPipelineResult:
    """Complete output of the end-to-end marketing pipeline."""

    dataset: pd.DataFrame
    metrics: MetricsBundle
    report: MarketingReport
