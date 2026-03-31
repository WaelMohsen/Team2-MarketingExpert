"""Backward-compatible router that delegates to the refactored services."""

from __future__ import annotations

import pandas as pd

from ..core import DataLoadError, DataValidationError
from ..ingestion import CampaignDataService
from ..metrics import CampaignMetricsService

_data_service = CampaignDataService()
_metrics_service = CampaignMetricsService()


def load_data(filepath: str = "data/all_campaigns_data.csv") -> pd.DataFrame | None:
    """Load and validate campaign data using the new ingestion service."""

    try:
        return _data_service.load_dataframe(filepath)
    except (DataLoadError, DataValidationError):
        return None


def calculate_metrics(dataframe: pd.DataFrame, target: str) -> dict[str, object]:
    """Calculate metrics for one dataframe slice."""

    try:
        return _metrics_service.calculate(dataframe, target)
    except DataValidationError:
        return {"error": "No data available"}


def calculate_metrics_full(dataframe: pd.DataFrame, target: str) -> dict[str, object]:
    """Calculate overall and per-channel metrics using the new service."""

    if dataframe is None or dataframe.empty:
        return {"error": "No data available"}

    try:
        return _metrics_service.calculate_full(dataframe, target).to_dict()
    except DataValidationError:
        return {"error": "No data available"}
