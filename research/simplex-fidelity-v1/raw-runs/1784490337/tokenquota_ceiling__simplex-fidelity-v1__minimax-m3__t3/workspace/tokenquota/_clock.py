"""Default clock implementation backed by :func:`time.monotonic`."""

from time import monotonic


def default_clock() -> float:
    """Return the current monotonic time in seconds."""
    return monotonic()