"""Logging package — loguru-based configuration for Marketing Expert.

Usage in any service module:
    from ..logging import get_logger
    logger = get_logger()
"""

from loguru import logger

from .logger import configure_loguru

__all__ = ["configure_loguru", "logger"]
