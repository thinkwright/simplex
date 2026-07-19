"""Public API for the :mod:`tokenquota` package.

This module implements a thread-safe token bucket using only the Python
standard library. All elapsed-time decisions are made through a user-supplied
clock (a zero-argument callable returning a seconds-like number). When no
clock is supplied, :func:`time.monotonic` is used as the default.
"""

import threading
import time


def _is_real_number(value):
    """Return ``True`` only for genuine ``int``/``float`` values.

    Booleans are rejected because, although ``bool`` is a subclass of ``int``,
    they are not meaningful token quantities.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Bucket:
    """A thread-safe token bucket.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be a positive
        number. The bucket starts full (``capacity`` tokens available).
    refill_per_second:
        Steady-state refill rate in tokens per second. Must be a non-negative
        number.
    clock:
        Optional zero-argument callable returning a seconds-like number used
        for all elapsed-time decisions. When ``None`` (the default),
        :func:`time.monotonic` is used.

    Raises
    ------
    ValueError
        If ``capacity`` is not positive or ``refill_per_second`` is negative
        (or either is not a real number).
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
        self._tokens = capacity
        self._last = self._clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Add tokens accrued since the last refill, capped at capacity.

        A backward clock movement is treated as zero elapsed time. The balance
        is never rounded: fractional tokens are preserved exactly.
        """
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            # Backward clock movement: no tokens gained.
            elapsed = 0
        self._last = now
        if elapsed and self._refill_per_second:
            self._tokens = min(
                self._capacity, self._tokens + elapsed * self._refill_per_second
            )

    def allow(self, amount=1):
        """Refill, then consume ``amount`` tokens if available.

        Returns ``True`` and consumes ``amount`` tokens when enough tokens are
        available; otherwise returns ``False`` without consuming anything.

        Raises
        ------
        ValueError
            If ``amount`` is not a positive, non-boolean number. No tokens are
            consumed when this is raised.
        """
        if not _is_real_number(amount):
            raise ValueError("amount must be a positive number and not a boolean")
        if amount <= 0:
            raise ValueError("amount must be positive")
        with self._lock:
            self._refill()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False

    def available(self):
        """Return the current token balance without consuming any tokens.

        Performs the same refill calculation as :meth:`allow` first.
        """
        with self._lock:
            self._refill()
            return self._tokens