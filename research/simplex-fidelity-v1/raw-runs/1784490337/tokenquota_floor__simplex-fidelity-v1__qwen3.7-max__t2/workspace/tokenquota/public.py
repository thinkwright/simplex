"""Public API for the tokenquota package."""

import math
import threading
import time


class Bucket:
    """A thread-safe token bucket that starts full.

    Parameters
    ----------
    capacity : positive number
        Maximum number of tokens the bucket can hold.
    refill_per_second : non-negative number
        Tokens added per second of elapsed time.
    clock : callable, optional
        A zero-argument callable returning a monotonic timestamp.
        Defaults to ``time.monotonic``.
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        # --- validate capacity ---
        if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        # --- validate refill_per_second ---
        if isinstance(refill_per_second, bool) or not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        self._balance = float(capacity)
        self._last_time = self._clock()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self):
        """Add tokens based on elapsed time.  Must be called under lock."""
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            # Clamp to capacity
            if self._balance > self._capacity:
                self._balance = float(self._capacity)
            # Round down to nearest integer (R4)
            self._balance = float(math.floor(self._balance))
            self._last_time = now
        # elapsed <= 0 → treat as zero elapsed; do nothing

    @staticmethod
    def _validate_amount(amount):
        """Raise ValueError for invalid consumption amounts."""
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number, not boolean")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self, amount=1):
        """Try to consume *amount* tokens.

        Refills first, then consumes if enough tokens exist.
        Returns ``True`` on success, ``False`` otherwise.
        """
        self._validate_amount(amount)
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
