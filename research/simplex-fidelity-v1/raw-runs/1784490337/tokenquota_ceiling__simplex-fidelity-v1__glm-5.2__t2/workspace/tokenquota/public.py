"""Public API for the :mod:`tokenquota` package.

This module exposes :class:`Bucket`, a thread-safe token bucket that uses only
the Python standard library and only the clock supplied by the caller (defaulting
to :func:`time.monotonic` when none is provided) for elapsed-time decisions.
"""

import math
import threading
import time


__all__ = ["Bucket"]


def _is_real_number(value):
    """Return True when *value* is a real (int/float) and not a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Bucket:
    """A thread-safe token bucket.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be a positive number.
    refill_per_second:
        Steady-state refill rate in tokens per second. Must be a non-negative
        number.
    clock:
        Optional zero-argument callable returning the current time as a number.
        It is the *only* source of time used for refill decisions. When omitted,
        :func:`time.monotonic` is used.

    The bucket starts full (its balance equals ``capacity``).
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        if not _is_real_number(capacity):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not _is_real_number(refill_per_second):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = capacity
        self._rate = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        # The bucket starts full.
        self._balance = capacity
        self._last = self._clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill the bucket based on elapsed time.

        Holds no lock itself; callers must hold ``self._lock``. A backward clock
        movement is treated as zero elapsed time and does not move the reference
        point forward, so a backward-then-forward round trip never grants tokens
        for the negative portion.
        """
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            # Backward clock movement: no tokens, and keep the higher reference.
            elapsed = 0
        else:
            self._last = now

        if elapsed > 0:
            self._balance += elapsed * self._rate
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round up to the nearest integer without exceeding capacity.
            rounded = math.ceil(self._balance)
            if rounded > self._capacity:
                rounded = self._capacity
            self._balance = rounded

    def allow(self, amount=1):
        """Refill, then consume *amount* tokens if available.

        Returns True when there were enough tokens (consuming them), or False
        without consuming anything when there were not. Raises ``ValueError`` for
        an invalid *amount* without consuming any tokens.
        """
        if not _is_real_number(amount):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill()
            if self._balance >= amount:
                self._balance -= amount
                return True
            return False

    def available(self):
        """Return the current token balance without consuming any.

        Performs the same refill calculation as :meth:`allow`.
        """
        with self._lock:
            self._refill()
            return self._balance