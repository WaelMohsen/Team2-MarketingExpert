"""Shared validators for schema validation."""

import re

_ASCII_PUNCTUATION_MAP = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
        "\u2022": "-",
    }
)


def normalize_ascii_punctuation(v: str) -> str:
    """Normalize common Unicode punctuation to ASCII equivalents.

    This keeps language validation strict while tolerating model output that uses
    typographic quotes, dashes, ellipses, bullets, or non-breaking spaces.
    """

    return v.translate(_ASCII_PUNCTUATION_MAP)


def assert_ascii(v: str) -> str:
    """Validate that a string contains only ASCII (English) characters.

    Args:
        v: The string to validate.

    Returns:
        The validated string unchanged.

    Raises:
        ValueError: If the string contains non-ASCII characters.
    """
    v = normalize_ascii_punctuation(v)
    if not re.match(r"^[\x00-\x7F]+$", v):
        raise ValueError("Field must contain only English (ASCII) characters")
    return v
