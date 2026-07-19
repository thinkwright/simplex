"""Clock abstraction for tokenquota.

The default clock is :func:`time.monotonic` from the standard library.
Tests and callers may inject a fake clock by passing an object with a
``now()`` method returning a numeric timestamp (typically seconds).
"""

from time import monotonic


class SystemClock:
    """Default clock backed by :func:`time.monotonic`."""

    def now(self) -> float:
        return monotonic()