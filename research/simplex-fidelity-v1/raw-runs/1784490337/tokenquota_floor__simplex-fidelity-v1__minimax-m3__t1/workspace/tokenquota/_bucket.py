"""Token-bucket implementation.

The bucket starts full, refills continuously based on elapsed wall-clock
time, and supports thread-safe consumption.
"""

from threading import Lock

from tokenquota._clock import SystemClock


class Bucket:
    """A token-bucket quota.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be > 0.
    refill_per_second:
        Rate at which tokens are added per second. Must be >= 0.
    clock:
        Optional object exposing ``now()`` returning a numeric timestamp.
        Defaults to :class:`tokenquota._clock.SystemClock` which uses
        :func:`time.monotonic` from the standard library.
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        if not isinstance(capacity, (int, float)) or isinstance(capacity, bool):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be a positive number")
        if not isinstance(refill_per_second, (int, float)) or isinstance(
            refill_per_second, bool
        ):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be a non-negative number")

        self._capacity = float(capacity)
        self._refill_per_second = float(refill_per_second)
        self._clock = clock if clock is not None else SystemClock()
        self._balance = float(capacity)
        self._last_time = self._clock.now()
        self._lock = Lock()

    def _refill_locked(self):
        """Recompute the balance based on elapsed time. Caller must hold the lock."""
        now = self._clock.now()
        elapsed = now - self._last_time
        if elapsed < 0:
            # Backward clock movement: treat as zero elapsed time.
            elapsed = 0
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round down to nearest integer after a positive-time refill + clamp.
            self._balance = float(int(self._balance))
            self._last_time = now

    def available(self):
        """Return the current token balance without consuming any tokens."""
        with self._lock:
            self._refill_locked()
            return self._balance

    def allow(self, amount=1):
        """Attempt to consume ``amount`` tokens.

        Returns ``True`` if enough tokens were available (and consumes them),
        otherwise returns ``False`` without consuming anything.
        """
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be a positive number")

        with self._lock:
            self._refill_locked()
            if self._balance >= amount:
                self._balance -= amount
                return True
            return False