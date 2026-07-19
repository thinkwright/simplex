"""Public API for the :mod:`tokenquota` package.

This module exposes :class:`Bucket`, a thread-safe token bucket that relies
only on a caller-supplied clock (defaulting to :func:`time.monotonic`) for all
elapsed-time decisions.  Only the Python standard library is used.
"""

import math
import threading
import time

__all__ = ["Bucket"]


class Bucket:
    """A thread-safe token bucket rate limiter.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold.  Must be positive.
    refill_per_second:
        Number of tokens added per second of elapsed time.  Must be
        non-negative.
    clock:
        Optional zero-argument callable returning the current time in
        seconds.  When ``None`` (the default) :func:`time.monotonic` is used.
        The bucket uses *only* this clock for elapsed-time decisions.

    The bucket starts full at ``capacity`` tokens.  On every operation the
    bucket first refills based on the elapsed time reported by the clock: it
    adds ``elapsed_seconds * refill_per_second`` tokens and clamps the balance
    to ``capacity``.  A backward clock movement is treated as zero elapsed
    time (and does not reset the reference point, so it can never grant
    tokens).  After the refill and capacity clamp the balance is rounded down
    to the nearest integer before the operation is answered; the underlying
    balance is kept at full precision between operations so fractional accrual
    is never lost.
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        if not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        if not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        # Use only the supplied clock; fall back to the standard-library
        # monotonic clock when none is provided.
        self._clock = clock if clock is not None else time.monotonic
        self._balance = capacity  # starts full
        self._last = self._clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill the bucket using only the configured clock."""
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            # A backward clock movement contributes no elapsed time and does
            # not reset the reference point, so it can never grant tokens.
            elapsed = 0
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            self._last = now

    def allow(self, amount=1):
        """Refill, then consume ``amount`` tokens if enough exist.

        Returns ``True`` (consuming ``amount``) when enough whole tokens exist
        and ``False`` otherwise without consuming anything.  ``amount`` must be
        a positive, non-boolean number.
        """
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number and not a boolean")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill()
            # Round down to the nearest integer before answering.
            if math.floor(self._balance) >= amount:
                self._balance -= amount
                return True
            return False

    def available(self):
        """Refill and return the current whole-token balance without consuming."""
        with self._lock:
            self._refill()
            # Round down to the nearest integer before answering.
            return math.floor(self._balance)