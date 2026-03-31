"""Backward-compatible wrapper around the refactored metrics package."""

from ..metrics.calculators import calculate_base_metrics

__all__ = ["calculate_base_metrics"]
