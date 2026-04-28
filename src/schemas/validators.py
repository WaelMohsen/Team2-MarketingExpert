"""Shared validators for schema validation."""

import re


def assert_ascii(v: str) -> str:
    """Validate that a string contains only ASCII (English) characters.

    Args:
        v: The string to validate.

    Returns:
        The validated string unchanged.

    Raises:
        ValueError: If the string contains non-ASCII characters.
    """
    if not re.match(r"^[\x00-\x7F]+$", v):
        raise ValueError("Field must contain only English (ASCII) characters")
    return v
