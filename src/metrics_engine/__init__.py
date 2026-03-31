"""Backward-compatible exports for the legacy metrics_engine package."""

from .router import calculate_metrics, calculate_metrics_full, load_data

__all__ = ["calculate_metrics", "calculate_metrics_full", "load_data"]
