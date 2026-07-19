"""Public API for the tokenquota package."""

import threading
import time


class Bucket:
    """A token-bucket rate limiter.

    Parameters
    ----------
    capacity : int or float
        Maximum number of tokens (must be positive).
    refill_per_second : int or float
        Rate at which tokens are added per second (must be non-negative).
    clock : callable, optional
        A zero-argument callable returning the current time as a number.
        Defaults to ``time.monotonic``.
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        # --- validation ------------------------------------------------
        if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        if isinstance(refill_per_second, bool) or not isinstance(
            refill_per_second, (int, float)
        ):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        self._balance = float(capacity)  # starts full
        self._last_time = self._clock()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _refill(self):
        """Add tokens based on elapsed time.  Must be called under lock."""
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed < 0:
            # Backward clock movement → treat as zero elapsed time.
            elapsed = 0
        self._last_time = now
        self._balance = min(
            self._capacity, self._balance + elapsed * self._refill_per_second
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def allow(self, amount=1):
        """Try to consume *amount* tokens.

        Returns ``True`` if the tokens were available (and consumed),
        ``False`` otherwise.

        Raises ``ValueError`` if *amount* is not a positive, non-boolean
        number.
        """
        # Validate before acquiring the lock so we never consume on bad input.
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
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
        """Return the current token balance after refilling.

        Does **not** consume any tokens.
        """
        with self._lock:
            self._refill()
            return self._balance
