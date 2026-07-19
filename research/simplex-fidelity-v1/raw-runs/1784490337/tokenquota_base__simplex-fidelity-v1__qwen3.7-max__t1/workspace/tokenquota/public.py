"""Token-bucket rate limiter with pluggable clock."""

import threading
import time


class Bucket:
    """A token bucket that starts full and refills over time.

    Parameters
    ----------
    capacity : float
        Maximum number of tokens (must be positive).
    refill_per_second : float
        Tokens added per second of elapsed time (must be non-negative).
    clock : callable, optional
        A callable returning the current time as a float.  Defaults to
        ``time.monotonic``.
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        # --- validation (R6 / X1) ---
        if isinstance(capacity, bool):
            raise ValueError("capacity must be a positive number")
        if not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        if isinstance(refill_per_second, bool):
            raise ValueError("refill_per_second must be a non-negative number")
        if not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = float(capacity)
        self._refill_per_second = float(refill_per_second)
        self._clock = clock if clock is not None else time.monotonic
        self._tokens = float(capacity)  # starts full (R1)
        self._last_time = self._clock()
        self._lock = threading.Lock()  # R7

    # ------------------------------------------------------------------
    # internal helpers (must be called while holding self._lock)
    # ------------------------------------------------------------------

    def _refill(self):
        """Add tokens based on elapsed time (R3, R4)."""
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed < 0:
            # backward clock movement → treat as zero elapsed (R3)
            elapsed = 0.0
        if elapsed > 0 and self._refill_per_second > 0:
            self._tokens += elapsed * self._refill_per_second
            if self._tokens > self._capacity:
                self._tokens = self._capacity
        self._last_time = now

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def allow(self, amount=1):
        """Try to consume *amount* tokens.

        Returns ``True`` and deducts the tokens when the bucket has enough;
        otherwise returns ``False`` without consuming anything (R2).

        Raises ``ValueError`` if *amount* is not a positive, non-boolean
        number (R6 / X1).
        """
        # validation (R6 / X1)
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False

    def available(self):
        """Return the current token balance after refilling, without
        consuming any tokens (R5)."""
        with self._lock:
            self._refill()
            return self._tokens
