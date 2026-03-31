"""Shared core building blocks for the Marketing Expert application."""

from .exceptions import (
    CategoryNotSupportedError,
    DataLoadError,
    DataValidationError,
    MarketingExpertError,
    PipelineExecutionError,
    ReportValidationError,
)
from .observability import (
    configure_logging,
    correlation_context,
    get_correlation_id,
    new_correlation_id,
)

__all__ = [
    "CategoryNotSupportedError",
    "DataLoadError",
    "DataValidationError",
    "MarketingExpertError",
    "PipelineExecutionError",
    "ReportValidationError",
    "configure_logging",
    "correlation_context",
    "get_correlation_id",
    "new_correlation_id",
]
