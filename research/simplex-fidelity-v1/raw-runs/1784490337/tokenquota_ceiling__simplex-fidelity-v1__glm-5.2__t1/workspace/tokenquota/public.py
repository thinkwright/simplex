"""Public API for the :mod:`tokenquota` package.

This module implements a token bucket rate limiter using only the Python
standard library.  All elapsed-time decisions are made through a user supplied
clock (defaulting to :func:`time.monotonic`) so that tests can fully control
the passage of time.
"""

import math
import threading
import time


def _is_real_number(value):
    """Return ``True`` when *value* is an ``int`` or ``float`` but not a ``bool``."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Bucket:
    """A thread-safe token bucket.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold.  Must be positive.
    refill_per_second:
        Steady rate at which tokens are added per second of elapsed time.
        Must be non-negative.
    clock:
        Optional callable returning the current time as a number.  When
        ``None`` :func:`time.monotonic` is used.  The clock is the only source
        of elapsed-time information.
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
        self._refill_per_second = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        # The bucket starts full.
        self._balance = capacity
        self._last_time = self._clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill the bucket based on elapsed time.

        Must be called while holding :attr:`_lock`.  Backward clock movement is
        treated as zero elapsed time.  After a positive-time refill and the
        capacity clamp, the balance is rounded up to the nearest integer
        without exceeding capacity.
        """
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed < 0:
            # A backward clock movement yields no tokens.
            elapsed = 0
        self._last_time = now

        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round up to the nearest integer, clamped to capacity.
            rounded = math.ceil(self._balance)
            if rounded > self._capacity:
                rounded = self._capacity
            self._balance = rounded

    def allow(self, amount=1):
        """Refill, then attempt to consume *amount* tokens.

        Returns ``True`` and consumes the tokens when enough are available,
        otherwise returns ``False`` without consuming anything.

        Raises
        ------
        ValueError
            If *amount* is not a positive number or is a boolean.
        """
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number, not a boolean")
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
        """Return the current token balance without consuming any tokens.

        Performs the same refill calculation as :meth:`allow`.
        """
        with self._lock:
            self._refill()
            return self._balance