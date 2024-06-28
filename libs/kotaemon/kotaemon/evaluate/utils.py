import re

PATTERN_INTEGER: re.Pattern = re.compile(r"([+-]?[1-9][0-9]*|0)")
"""Regex that matches integers."""


def validate_rating(rating) -> int:
    """Validate a rating is between 0 and 10."""

    if not 0 <= rating <= 10:
        raise ValueError("Rating must be between 0 and 10")

    return rating


def re_0_10_rating(s: str) -> int:
    """Extract a 0-10 rating from a string.

    If the string does not match an integer or matches an integer outside the
    0-10 range, raises an error instead. If multiple numbers are found within
    the expected 0-10 range, the smallest is returned.

    Args:
        s: String to extract rating from.

    Returns:
        int: Extracted rating.

    Raises:
        ParseError: If no integers between 0 and 10 are found in the string.
    """

    matches = PATTERN_INTEGER.findall(s)
    if not matches:
        raise AssertionError

    vals = set()
    for match in matches:
        try:
            vals.add(validate_rating(int(match)))
        except ValueError:
            pass

    if not vals:
        raise AssertionError

    # Min to handle cases like "The rating is 8 out of 10."
    return min(vals)
