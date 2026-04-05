"""
Logging module for Team2-MarketingExpert.

Provides centralized, pre-configured loguru-based logging with:
- INFO level baseline with colored console output
- JSON structured file logs (7-day retention)
- Automatic suppression of noisy third-party libraries
"""

from .logger import get_logger, configure_logger, logger

__all__ = ["get_logger", "configure_logger", "logger"]
