"""Token-bucket implementation."""

from __future__ import annotations

import math
import threading
from typing import Callable, Optional


class _SystemClock:
    """Default clock backed by time.monotonic."""

    def __init__(self) -> None:
        import time

        self._time = time

    def __call__(self) -> float:
        return self._time.monotonic()


class Bucket:
    """A token-bucket rate limiter.

    The bucket starts full. ``allow`` refills based on elapsed time, then
    consumes tokens if enough are available. ``available`` reports the
    current balance without consuming.
    """

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        # Validate capacity.
        if isinstance(capacity, bool):
            raise ValueError("capacity must be a positive number")
        if not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        # Validate refill rate.
        if isinstance(refill_per_second, bool):
            raise ValueError("refill_per_second must be a non-negative number")
        if not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity: float = float(capacity)
        self._refill_per_second: float = float(refill_per_second)
        self._clock: Callable[[], float] = clock if clock is not None else _SystemClock()
        self._balance: float = float(capacity)
        self._last_time: float = self._clock()
        self._lock = threading.Lock()

    def _refill_locked(self) -> None:
        """Refill the bucket based on elapsed time. Caller must hold the lock."""
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed < 0:
            # Backward clock movement: treat as zero elapsed time.
            elapsed = 0.0
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round up to the nearest integer without exceeding capacity.
            rounded = math.ceil(self._balance)
            if rounded > self._capacity:
                rounded = self._capacity
            self._balance = float(rounded)
            self._last_time = now

    def available(self) -> float:
        """Return the current token balance without consuming."""
        with self._lock:
            self._refill_locked()
            return self._balance

    def allow(self, amount: float = 1) -> bool:
        """Try to consume ``amount`` tokens. Returns True on success."""
        # Validate amount.
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill_locked()
            if self._balance >= amount:
                self._balance -= amount
                return True
            return False