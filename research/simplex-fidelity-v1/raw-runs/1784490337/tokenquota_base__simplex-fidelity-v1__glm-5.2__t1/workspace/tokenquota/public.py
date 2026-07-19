"""Public API for the :mod:`tokenquota` package.

This module exposes :class:`Bucket`, a thread-safe token bucket rate limiter
that depends only on the Python standard library and uses the supplied clock
for every elapsed-time decision.
"""

import threading
import time

__all__ = ["Bucket"]


def _is_real_number(value):
    """Return ``True`` when *value* is an ``int`` or ``float`` but not a ``bool``.

    ``bool`` is a subclass of ``int`` in Python, so it is rejected explicitly so
    that values such as ``True``/``False`` are never silently treated as the
    numbers ``1``/``0``.
    """
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


class Bucket:
    """A thread-safe token bucket.

    The bucket starts full with ``capacity`` tokens and refills continuously
    at ``refill_per_second`` tokens per second, never exceeding ``capacity``.

    All elapsed-time decisions use ``clock`` -- a zero-argument callable that
    returns the current time as a number. When ``clock`` is ``None``,
    :func:`time.monotonic` is used. A backward clock movement is treated as
    zero elapsed time, so it never grants extra tokens. The fractional balance
    is preserved exactly; it is never rounded.
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        if not _is_real_number(capacity) or capacity <= 0:
            raise ValueError("capacity must be a positive number")
        if not _is_real_number(refill_per_second) or refill_per_second < 0:
            raise ValueError("refill_per_second must be a non-negative number")

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        self._tokens = capacity
        self._last = self._clock()
        self._lock = threading.Lock()

    def _refill_locked(self):
        """Refill the bucket using the supplied clock. The caller holds the lock."""
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            elapsed = 0
        self._tokens = min(
            self._capacity, self._tokens + elapsed * self._refill_per_second
        )
        self._last = now
        return self._tokens

    def allow(self, amount=1):
        """Refill, then consume ``amount`` tokens if enough are available.

        Returns ``True`` when there were enough tokens (consuming them), or
        ``False`` when there were not (leaving the balance untouched). Raises
        :class:`ValueError` for an invalid ``amount`` without consuming tokens.
        """
        if not _is_real_number(amount) or amount <= 0:
            raise ValueError("amount must be a positive number")
        with self._lock:
            self._refill_locked()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False

    def available(self):
        """Return the current token balance after refilling, without consuming."""
        with self._lock:
            return self._refill_locked()