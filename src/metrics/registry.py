"""Registry for category-specific metric calculators."""

from __future__ import annotations

from collections.abc import Mapping

from .calculators import (
    MetricCalculator,
    calculate_acquisition_metrics,
    calculate_retention_metrics,
    calculate_revenue_metrics,
    calculate_satisfaction_metrics,
)

DEFAULT_METRIC_CALCULATORS: dict[str, MetricCalculator] = {
    "Customer Acquisition": calculate_acquisition_metrics,
    "Customer Satisfaction": calculate_satisfaction_metrics,
    "Revenue Growth": calculate_revenue_metrics,
    "Customer Retention": calculate_retention_metrics,
}


class MetricCalculatorRegistry:
    """Maps business categories to their metric calculators."""

    def __init__(self, calculators: Mapping[str, MetricCalculator] | None = None) -> None:
        self._calculators: dict[str, MetricCalculator] = dict(calculators or DEFAULT_METRIC_CALCULATORS)

    def register(self, category: str, calculator: MetricCalculator) -> None:
        """Register or replace a calculator for a category."""

        self._calculators[category] = calculator

    def get(self, category: str) -> MetricCalculator | None:
        """Return the calculator for a category, if present."""

        return self._calculators.get(category)

    def supported_categories(self) -> tuple[str, ...]:
        """Return the known business categories."""

        return tuple(self._calculators.keys())
