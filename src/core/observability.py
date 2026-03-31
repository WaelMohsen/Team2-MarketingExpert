"""Shared logging and correlation-id utilities."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator
from uuid import uuid4

_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")
_logging_configured = False


class CorrelationIdFilter(logging.Filter):
    """Inject the active correlation id into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application logging once with correlation-id support."""

    global _logging_configured
    if _logging_configured:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [corr=%(correlation_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(CorrelationIdFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    _logging_configured = True


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
