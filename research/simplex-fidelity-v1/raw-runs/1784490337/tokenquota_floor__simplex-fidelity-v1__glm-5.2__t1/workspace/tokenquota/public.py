"""Public API for the tokenquota package.

This module exposes :class:`Bucket`, a token-bucket rate limiter that:

* uses only the supplied clock for elapsed-time decisions (CONSTRAINT [C1]);
* depends solely on the Python standard library (CONSTRAINT [C1]).

See the project rules R1-R7 for the full behavioural contract.
"""

import math
import threading
import time

__all__ = ["Bucket"]


class Bucket:
    """A thread-safe token bucket.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be positive.
    refill_per_second:
        Steady-state token replenishment rate. Must be non-negative.
    clock:
        Optional zero-argument callable returning a monotonic-ish number of
        seconds. Defaults to :func:`time.monotonic`. Only this clock is ever
        consulted for elapsed-time decisions (CONSTRAINT [C1]).
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        # Validate capacity (R6): a real, positive number.
        if not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        # Validate refill rate (R6): a real, non-negative number.
        if not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        # The bucket starts full (R1).
        self._balance = capacity
        self._last_time = self._clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill the bucket using only the supplied clock.

        Called while holding ``self._lock``. Implements R3 and R4:

        * elapsed time is ``now - last_time``;
        * a backward (or stationary) clock yields zero elapsed time, so no
          tokens are added and the ``last_time`` marker is not moved backward;
        * on a positive-time refill the balance is clamped to ``capacity`` and
          then rounded down to the nearest integer before the caller answers.
        """
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round down to the nearest integer after a positive-time refill
            # and capacity clamp (R4).
            self._balance = math.floor(self._balance)
            self._last_time = now
        # elapsed <= 0 (backward or stationary clock): zero elapsed time,
        # no refill, no rounding, last_time unchanged (R3).

    def allow(self, amount=1):
        """Refill, then consume ``amount`` tokens if available (R2).

        Returns ``True`` and consumes the tokens when enough are available,
        otherwise returns ``False`` without consuming anything.

        ``amount`` must be a positive, non-boolean number (R6, X1); invalid
        values raise :class:`ValueError` without consuming tokens.
        """
        # Validate amount (R6, X1) before touching state.
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
        """Return the current balance without consuming tokens (R5).

        Performs the same refill calculation as :meth:`allow`.
        """
        with self._lock:
            self._refill()
            return self._balance