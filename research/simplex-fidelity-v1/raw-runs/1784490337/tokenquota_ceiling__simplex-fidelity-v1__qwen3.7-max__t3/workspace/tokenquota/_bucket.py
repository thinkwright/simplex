"""Token-quota bucket – internal implementation."""

import math
import threading
import time


class Bucket:
    """A token bucket that starts full, refills over time, and is thread-safe.

    Parameters
    ----------
    capacity : positive number
        Maximum (and initial) token balance.
    refill_per_second : non-negative number
        Tokens added per elapsed second.
    clock : callable, optional
        Zero-argument callable returning the current time.
        Defaults to ``time.monotonic``.
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        # --- validate capacity ---
        if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        # --- validate refill_per_second ---
        if isinstance(refill_per_second, bool) or not isinstance(
            refill_per_second, (int, float)
        ):
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
    # internal helpers
    # ------------------------------------------------------------------

    def _refill(self):
        """Add tokens based on elapsed time (must be called under lock)."""
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            # clamp to capacity
            self._balance = min(self._balance, self._capacity)
            # round up to nearest integer, then clamp again
            self._balance = min(math.ceil(self._balance), self._capacity)
            self._last_time = now
        # elapsed <= 0 → backward clock or no time passed → no refill, no update

    @staticmethod
    def _validate_amount(amount):
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number, not a boolean")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def allow(self, amount=1):
        """Try to consume *amount* tokens.

        Refills first, then consumes if enough tokens exist.
        Returns ``True`` on success, ``False`` otherwise (no consumption).
        Raises ``ValueError`` for invalid *amount*.
        """
        self._validate_amount(amount)
        with self._lock:
            self._refill()
            if self._balance >= amount:
                self._balance -= amount
                return True
            return False

    def available(self):
        """Return the current token balance after refilling (no consumption)."""
        with self._lock:
            self._refill()
            return self._balance
