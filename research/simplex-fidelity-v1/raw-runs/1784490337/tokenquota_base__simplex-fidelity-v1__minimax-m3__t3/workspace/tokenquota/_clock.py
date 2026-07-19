"""Default clock implementation using only the Python standard library."""

from time import monotonic


def default_clock() -> float:
    """Return the current monotonic time in seconds.

    Uses :func:`time.monotonic` so the value never goes backward
    within a single Python process.
    """
    return monotonic()