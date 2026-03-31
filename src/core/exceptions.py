"""Application-specific exception types."""


class MarketingExpertError(Exception):
    """Base class for application-specific failures."""


class DataLoadError(MarketingExpertError):
    """Raised when a data source cannot be loaded."""


class DataValidationError(MarketingExpertError):
    """Raised when input data does not satisfy expected contracts."""


class CategoryNotSupportedError(MarketingExpertError):
    """Raised when a requested analysis category is not supported."""


class PipelineExecutionError(MarketingExpertError):
    """Raised when an orchestration pipeline cannot complete."""
