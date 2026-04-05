"""Application services for campaign metric calculations."""

from __future__ import annotations

import pandas as pd

from ..logging.logger import logger

from ..core import DataValidationError
from .calculators import calculate_base_metrics
from .models import MetricsBundle, MetricsMap
from .registry import MetricCalculatorRegistry


class CampaignMetricsService:
    """Calculates campaign metrics with optional category-specific enrichment."""

    def __init__(self, registry: MetricCalculatorRegistry | None = None) -> None:
        self._registry = registry or MetricCalculatorRegistry()

    @property
    def supported_categories(self) -> tuple[str, ...]:
        """Expose the categories supported by the configured registry."""

        return self._registry.supported_categories()

    def calculate(self, dataframe: pd.DataFrame, category: str) -> MetricsMap:
        """Calculate metrics for a single dataframe slice."""

        if dataframe is None or dataframe.empty:
            raise DataValidationError("No data available for metric calculation.")

        logger.info("Calculating metrics for category %s with %s rows", category, len(dataframe))
        base_metrics = calculate_base_metrics(dataframe)
        calculator = self._registry.get(category)

        if calculator is None:
            return base_metrics

        return calculator(dataframe, dict(base_metrics))

    def calculate_full(self, dataframe: pd.DataFrame, category: str) -> MetricsBundle:
        """Calculate overall metrics and per-channel metrics."""

        logger.info("Calculating full metric bundle for category %s", category)
        overall = self.calculate(dataframe, category)
        per_channel: dict[str, MetricsMap] = {}

        if "channel" in dataframe.columns:
            for channel_name, channel_dataframe in dataframe.groupby("channel", dropna=False):
                per_channel[str(channel_name)] = self.calculate(
                    channel_dataframe.reset_index(drop=True),
                    category,
                )

        logger.info("Calculated per-channel metrics for %s channels", len(per_channel))
        return MetricsBundle(overall=overall, per_channel=per_channel)
