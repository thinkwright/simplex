"""Token-bucket implementation."""

from threading import Lock
from typing import Callable, Optional

from tokenquota._clock import default_clock


class Bucket:
    """A token-bucket rate limiter.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be positive.
    refill_per_second:
        Number of tokens added per second of elapsed time. Must be
        non-negative.
    clock:
        Optional callable returning the current time in seconds. When
        ``None`` (the default) :func:`time.monotonic` is used.
    """

    def __init__(
        self,
        capacity,
        refill_per_second,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if not isinstance(capacity, (int, float)) or isinstance(capacity, bool):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        if not isinstance(refill_per_second, (int, float)) or isinstance(
            refill_per_second, bool
        ):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = float(capacity)
        self._refill_per_second = float(refill_per_second)
        self._clock = clock if clock is not None else default_clock
        self._tokens = float(capacity)
        self._last_time = self._clock()
        self._lock = Lock()

    def _refill_locked(self) -> None:
        """Refill tokens based on elapsed time. Caller must hold the lock."""
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed < 0:
            # Backward clock movement: treat as zero elapsed time.
            elapsed = 0
        if elapsed > 0:
            self._tokens += elapsed * self._refill_per_second
            if self._tokens > self._capacity:
                self._tokens = self._capacity
            # Round up to nearest integer without exceeding capacity.
            if self._tokens > 0:
                rounded = int(self._tokens) if self._tokens == int(self._tokens) else int(self._tokens) + 1
                if rounded > self._capacity:
                    rounded = int(self._capacity)
                self._tokens = float(rounded)
            self._last_time = now

    def available(self) -> float:
        """Return the current token balance without consuming any."""
        with self._lock:
            self._refill_locked()
            return self._tokens

    def allow(self, amount=1) -> bool:
        """Attempt to consume ``amount`` tokens.

        Returns ``True`` and consumes the tokens when enough are available,
        otherwise returns ``False`` without consuming any tokens.
        """
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number, not a boolean")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill_locked()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False