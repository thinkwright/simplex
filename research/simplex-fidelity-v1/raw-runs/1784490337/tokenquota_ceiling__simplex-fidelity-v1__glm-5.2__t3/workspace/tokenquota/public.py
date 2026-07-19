"""Public API for the :mod:`tokenquota` package.

Only the Python standard library is used (``math``, ``threading``, ``time``).
All elapsed-time decisions are made through the clock supplied to
:class:`Bucket`; when no clock is supplied, :func:`time.monotonic` is used.
"""

import math
import threading
import time


class Bucket:
    """A token bucket that refills over time.

    The bucket starts full (its initial balance equals ``capacity``).

    Args:
        capacity: Maximum number of tokens the bucket can hold. Must be a
            positive number.
        refill_per_second: Number of tokens added per second of elapsed time.
            Must be a non-negative number.
        clock: Optional callable taking no arguments and returning the current
            time as a number. Defaults to :func:`time.monotonic`.

    Raises:
        ValueError: If ``capacity`` is not positive or ``refill_per_second`` is
            negative (or either is not a real number).
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, (int, float))
            or not (capacity > 0)
        ):
            raise ValueError("capacity must be a positive number")
        if (
            isinstance(refill_per_second, bool)
            or not isinstance(refill_per_second, (int, float))
            or not (refill_per_second >= 0)
        ):
            raise ValueError("refill_per_second must be a non-negative number")

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        self._balance = capacity
        self._last_time = self._clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill the bucket based on elapsed time.

        Adds ``elapsed_seconds * refill_per_second`` tokens, clamps to
        capacity, and (for positive elapsed time) rounds the balance up to the
        nearest integer without exceeding capacity. A backward clock movement
        is treated as zero elapsed time.
        """
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed < 0:
            elapsed = 0
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            rounded = math.ceil(self._balance)
            if rounded > self._capacity:
                rounded = self._capacity
            self._balance = rounded
        self._last_time = now

    def allow(self, amount=1):
        """Refill, then consume ``amount`` tokens if enough are available.

        Args:
            amount: Positive number of tokens to consume. Must not be a
                boolean.

        Returns:
            bool: ``True`` if the tokens were consumed, ``False`` otherwise (in
            which case nothing is consumed).

        Raises:
            ValueError: If ``amount`` is not a positive number or is a boolean.
        """
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not (amount > 0)
        ):
            raise ValueError("amount must be a positive number and not a boolean")
        with self._lock:
            self._refill()
            if self._balance >= amount:
                self._balance -= amount
                return True
            return False

    def available(self):
        """Refill, then return the current balance without consuming tokens."""
        with self._lock:
            self._refill()
            return self._balance