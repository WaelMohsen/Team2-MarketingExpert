"""
Centralized logging configuration using loguru.

Features:
- INFO level baseline (DEBUG suppressed for noisy libraries)
- Console streaming with colors and formatted output
- File rotation: 7-day retention with JSON structured logs
- Automatic suppression of verbose libraries (openai, httpx, urllib3, etc.)
- Single entry point via @lru_cache pattern
"""

import sys
import os
from functools import lru_cache
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger as _logger


# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

CONSOLE_LOG_FORMAT = (
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

FILE_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# Libraries to suppress (set to WARNING/ERROR only)
NOISY_LIBRARIES = [
    "openai",
    "httpx",
    "urllib3",
    "asyncio",
    "streamlit",
    "aiohttp",
]

# 7-day retention for rotated logs
RETENTION_DAYS = 7


# ============================================================================
# LOGGER INITIALIZATION (lru_cache for singleton-like behavior)
# ============================================================================

@lru_cache(maxsize=1)
def get_logger():
    """
    Initialize and return configured loguru logger.
    
    Returns:
        Logger: Configured loguru logger instance
        
    Note:
        This function uses @lru_cache to ensure logger is initialized
        only once, similar to the project's get_client() pattern.
    """
    
    # Remove default handler
    _logger.remove()
    
    # ========================================================================
    # CONSOLE HANDLER - Real-time colored output
    # ========================================================================
    _logger.add(
        sys.stderr,
        format=CONSOLE_LOG_FORMAT,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # ========================================================================
    # FILE HANDLER - JSON structured logs with 7-day rotation
    # ========================================================================
    log_file = LOG_DIR / "app.log"
    
    _logger.add(
        str(log_file),
        format=FILE_LOG_FORMAT,
        level="DEBUG",
        rotation="00:00",  # Rotate at midnight
        retention=f"{RETENTION_DAYS} days",  # Keep 7 days
        compression="zip",  # Compress rotated logs
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )
    
    # ========================================================================
    # STRUCTURED JSON HANDLER - For machine parsing (optional but useful)
    # ========================================================================
    json_log_file = LOG_DIR / "app.json"
    
    def json_serializer(record):
        """Custom JSON formatter for structured logging."""
        return {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "process": record["process"].name,
            "thread": record["thread"].name,
        }
    
    _logger.add(
        json_log_file,
        format="{message}",
        level="DEBUG",
        rotation="00:00",
        retention=f"{RETENTION_DAYS} days",
        compression="zip",
        encoding="utf-8",
        serialize=json_serializer,  # Use custom JSON formatter
    )
    
    # ========================================================================
    # SUPPRESS NOISY LIBRARIES
    # ========================================================================
    for library in NOISY_LIBRARIES:
        _logger.disable(library)
    
    # Set third-party libraries to WARNING level only
    import logging
    for library in NOISY_LIBRARIES:
        logging.getLogger(library).setLevel(logging.WARNING)
    
    return _logger


# ============================================================================
# PUBLIC API
# ============================================================================

def configure_logger():
    """
    Explicitly configure the logger.
    
    Useful if called from main module or initialization point.
    Can be called multiple times safely (lru_cache prevents re-initialization).
    """
    return get_logger()


# Make logger easily importable
logger = get_logger()

__all__ = ["get_logger", "configure_logger", "logger"]
