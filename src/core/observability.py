"""Shared logging and correlation-id utilities.

Public API is unchanged — all existing callers (app.py, src/core/__init__.py,
tests/test_observability.py) continue to work without modification.

Internally, configure_logging() now delegates to the loguru-based setup in
src.logging.logger rather than configuring a stdlib StreamHandler directly.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator
from uuid import uuid4

# ---------------------------------------------------------------------------
# Correlation-id state — ContextVar is the single source of truth
# ---------------------------------------------------------------------------
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


# ---------------------------------------------------------------------------
# Compatibility shim — kept so existing tests/imports remain valid
# ---------------------------------------------------------------------------
class CorrelationIdFilter(logging.Filter):
    """Inject the active correlation-id into stdlib log records.

    Retained as a compatibility shim; the active logging backend is loguru,
    which uses the patcher in src.logging.logger instead.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()  
        return True


# ---------------------------------------------------------------------------
# Public configuration entry-point
# ---------------------------------------------------------------------------
def configure_logging(level: int = logging.INFO) -> None:
    """Configure application logging once with correlation-id support.

    Delegates to the loguru-based ``configure_loguru`` in *src.logging*.
    The import is lazy (inside the function body) to avoid a circular import
    between this module and src.logging.logger, which lazily imports
    ``get_correlation_id`` from here.

    Args:
        level: stdlib integer log level (e.g. ``logging.INFO``).  Converted
            to a level name string before being passed to loguru.
    """
    from src.logging.logger import configure_loguru 

    configure_loguru(log_level=logging.getLevelName(level))


# ---------------------------------------------------------------------------
# Correlation-id helpers — public API unchanged
# ---------------------------------------------------------------------------
def new_correlation_id() -> str:
    """Create a new short correlation id."""
    return uuid4().hex[:12]


def get_correlation_id() -> str:
    """Return the current correlation id."""
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> Token[str]:
    """Set the active correlation id and return the context token."""
    return _correlation_id_var.set(correlation_id)


def reset_correlation_id(token: Token[str]) -> None:
    """Reset the correlation id to its previous value."""
    _correlation_id_var.reset(token)


@contextmanager
def correlation_context(correlation_id: str | None = None) -> Iterator[str]:
    """Run code inside a correlation-id scope."""
    token = set_correlation_id(correlation_id or new_correlation_id())
    try:
        yield get_correlation_id()
    finally:
        reset_correlation_id(token)
