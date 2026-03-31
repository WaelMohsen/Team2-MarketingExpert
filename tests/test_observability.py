import logging

from src.core.observability import CorrelationIdFilter, correlation_context, get_correlation_id, new_correlation_id


def test_correlation_context_sets_and_resets_id():
    original = get_correlation_id()

    with correlation_context("abc123") as correlation_id:
        assert correlation_id == "abc123"
        assert get_correlation_id() == "abc123"

    assert get_correlation_id() == original


def test_correlation_filter_injects_active_id():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    with correlation_context("xyz789"):
        assert CorrelationIdFilter().filter(record) is True

    assert record.correlation_id == "xyz789"


def test_new_correlation_id_is_short_and_non_empty():
    correlation_id = new_correlation_id()

    assert isinstance(correlation_id, str)
    assert len(correlation_id) == 12
