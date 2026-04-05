"""Loguru-based logger configuration for the Marketing Expert application.

This module is the single source of truth for all logging setup:
  - Console sink  : colorised, human-readable (StreamHandler equivalent)
  - File sink     : plain-text, rotation-managed, thread-safe
  - Stdlib bridge : routes third-party stdlib logging into loguru
  - Noisy-lib     : suppresses chatty libraries (openai, httpx, …) to WARNING
  - Correlation   : injects the active correlation-id into every record
  - LRU cache     : _setup_sinks is cached so repeated calls with the same
                    level are resolved in O(1) without re-entering setup logic
"""

from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record

# ---------------------------------------------------------------------------
# Safety flag — prevents double-configuration if called with different levels
# ---------------------------------------------------------------------------
_configured: bool = False

# ---------------------------------------------------------------------------
# Log formats
# ---------------------------------------------------------------------------
_CONSOLE_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "[corr={extra[correlation_id]}] | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

_FILE_FORMAT: str = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | "
    "[corr={extra[correlation_id]}] | "
    "{name}:{function}:{line} | {message}"
)

# Libraries whose verbosity is capped at WARNING.
_NOISY_LOGGERS: tuple[str, ...] = (
    "openai",
    "httpx",
    "httpcore",
    "urllib3",
    "requests",
    "asyncio",
)


# ---------------------------------------------------------------------------
# Stdlib → loguru bridge
# ---------------------------------------------------------------------------
class _InterceptHandler(logging.Handler):
    """Route stdlib log records into loguru, preserving origin location."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Walk past stdlib's internal frames so loguru shows the real caller.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ---------------------------------------------------------------------------
# Correlation-id patcher
# ---------------------------------------------------------------------------
def _correlation_id_patcher(record: "Record") -> None:
    """Inject the active correlation-id into every log record's extra dict.

    Lazy import breaks the potential circular dependency:
      src.core.observability → src.logging.logger → src.core.observability
    """
    from src.core.observability import get_correlation_id  # noqa: PLC0415

    record["extra"].setdefault("correlation_id", get_correlation_id())


# ---------------------------------------------------------------------------
# Cached sink setup — runs at most once per unique log_level value
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _setup_sinks(log_level: str) -> None:
    """Configure loguru sinks for the given console log level.

    Decorated with ``@lru_cache(maxsize=1)`` so that repeated calls with the
    same resolved level are short-circuited in O(1) by the cache lookup,
    without re-entering any setup logic.  A secondary ``_configured`` flag
    guards the edge case where this is called with two different level strings.
    """
    global _configured
    if _configured:
        return

    # Remove loguru's default stderr handler; install correlation patcher.
    logger.configure(handlers=[], patcher=_correlation_id_patcher)

    # -- Console sink (StreamHandler equivalent) ----------------------------
    logger.add(
        sys.stderr,
        format=_CONSOLE_FORMAT,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=False,  # keep variable values out of tracebacks (PII safety)
    )

    # -- File sink ----------------------------------------------------------
    logger.add(
        "logs/app.log",
        format=_FILE_FORMAT,
        level="DEBUG",       # always capture DEBUG+ to disk
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,        # async, thread-safe writes
        backtrace=True,
        diagnose=False,
    )

    # -- Stdlib bridge: redirect all third-party logging into loguru --------
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # -- Suppress noisy third-party loggers ---------------------------------
    for lib in _NOISY_LOGGERS:
        logging.getLogger(lib).setLevel(logging.WARNING)

    _configured = True


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------
def configure_loguru(log_level: str | None = None) -> None:
    """Configure loguru sinks for the application.

    Resolves the effective log level, then delegates to the LRU-cached
    ``_setup_sinks``.  Repeated calls with the same level are O(1) cache hits.

    Args:
        log_level: Desired console log level (e.g. ``"DEBUG"``, ``"INFO"``).
            Falls back to the ``LOG_LEVEL`` environment variable, then
            ``"INFO"``.
    """
    resolved: str = (log_level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    _setup_sinks(resolved)
