"""Public API for the :mod:`tokenquota` package.

This module exposes :class:`Bucket`, a thread-safe token bucket limiter that
relies solely on the Python standard library and on the clock supplied by the
caller for every elapsed-time decision.
"""

import math
import threading
import time


class Bucket:
    """A thread-safe token bucket.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be positive.
    refill_per_second:
        Number of tokens added per second of elapsed time. Must be
        non-negative. The bucket never holds more than ``capacity`` tokens.
    clock:
        Optional zero-argument callable returning the current time as a
        number. It is the only source of time used by the bucket. When
        omitted, the standard-library :func:`time.monotonic` is used.

    The bucket starts full (``capacity`` tokens available).
    """

    __slots__ = (
        "_capacity",
        "_refill_per_second",
        "_clock",
        "_balance",
        "_last",
        "_lock",
    )

    def __init__(self, capacity, refill_per_second, clock=None):
        # Validate capacity: must be a real, positive number.
        if not isinstance(capacity, (int, float)) or isinstance(capacity, bool):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        # Validate refill_per_second: must be a real, non-negative number.
        if (
            not isinstance(refill_per_second, (int, float))
            or isinstance(refill_per_second, bool)
        ):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        if clock is None:
            clock = time.monotonic

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock
        # The bucket starts full.
        self._balance = capacity
        self._last = clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill the bucket based on elapsed time.

        Adds ``elapsed_seconds * refill_per_second`` tokens, clamps to
        ``capacity``, and (for positive elapsed time) rounds the balance down
        to the nearest integer. A backward clock movement is treated as zero
        elapsed time so it never grants tokens.
        """
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            # Backward clock movement: treat as zero elapsed time.
            elapsed = 0
        self._last = now
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round down to the nearest integer after a positive-time refill.
            self._balance = math.floor(self._balance)

    def allow(self, amount=1):
        """Refill, then consume ``amount`` tokens if available.

        Returns ``True`` and consumes the tokens when enough tokens exist,
        otherwise returns ``False`` without consuming anything.

        ``amount`` must be a positive, non-boolean number.
        """
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number and not a boolean")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill()
            if self._balance >= amount:
                self._balance -= amount
                return True
            return False

    def available(self):
        """Return the current token balance without consuming any tokens.

        Performs the same refill calculation as :meth:`allow`.
        """
        with self._lock:
            self._refill()
            return self._balance


__all__ = ["Bucket"]