"""Token-bucket rate limiter – public API."""

import threading
import time


class Bucket:
    """A thread-safe token bucket that starts full.

    Parameters
    ----------
    capacity : positive number
        Maximum number of tokens the bucket can hold.
    refill_per_second : non-negative number
        Tokens added per second (capped at *capacity*).
    clock : callable, optional
        A zero-argument callable returning the current time.
        Defaults to ``time.monotonic``.
    """

    __slots__ = ("_capacity", "_refill_per_second", "_clock",
                 "_tokens", "_last_time", "_lock")

    def __init__(self, capacity, refill_per_second, clock=None):
        # --- validate capacity ---
        if isinstance(capacity, bool):
            raise ValueError("capacity must be a positive number")
        if not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        # --- validate refill_per_second ---
        if isinstance(refill_per_second, bool):
            raise ValueError("refill_per_second must be a non-negative number")
        if not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = clock if clock is not None else time.monotonic
        self._tokens = float(capacity)  # starts full
        self._last_time = self._clock()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _refill(self):
        """Add tokens based on elapsed time.  Must be called under lock."""
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed <= 0:
            # Backward or zero clock movement → no tokens added,
            # and we do NOT advance _last_time so that a later
            # forward jump is measured from the last good time.
            return
        added = elapsed * self._refill_per_second
        self._tokens = min(self._capacity, self._tokens + added)
        self._last_time = now

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def allow(self, amount=1):
        """Try to consume *amount* tokens.

        Refills first, then attempts to consume.  Returns ``True`` on
        success, ``False`` when insufficient tokens remain (nothing is
        consumed in that case).

        Raises ``ValueError`` if *amount* is not a positive, non-boolean
        number.
        """
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number, not boolean")
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
        """Return the current token balance after refilling.

        Performs the same refill calculation as :meth:`allow` but does
        not consume any tokens.
        """
        with self._lock:
            self._refill()
            return self._tokens
