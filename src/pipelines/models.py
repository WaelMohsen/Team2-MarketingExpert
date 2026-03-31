"""Result contracts for orchestration pipelines."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..metrics import MetricsBundle
from ..preprocessing import PreprocessingResult
from ..reporting import MarketingReport
from ..validation import ValidationResult


@dataclass(frozen=True)
class MarketingPipelineResult:
    """Complete output of the end-to-end marketing pipeline."""

    correlation_id: str
    raw_dataset: pd.DataFrame
    dataset: pd.DataFrame
    preprocessing: PreprocessingResult
    input_validation: ValidationResult
    metrics: MetricsBundle
    report: MarketingReport
