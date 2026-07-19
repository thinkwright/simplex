"""Token bucket implementation."""

from __future__ import annotations

import math
import threading
from typing import Callable, Optional


class _SystemClock:
    """Default clock using the standard library time module."""

    def time(self) -> float:
        import time as _time

        return _time.monotonic()


class Bucket:
    """A token bucket with injectable clock.

    The bucket starts full at the time of construction. Tokens refill at
    ``refill_per_second`` per elapsed second, capped at ``capacity``.
    """

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
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
        self._clock = clock if clock is not None else _SystemClock().time
        self._balance = float(capacity)
        self._last_time = self._clock()
        self._lock = threading.Lock()

    def _refill_locked(self) -> None:
        now = self._clock()
        elapsed = now - self._last_time
        if elapsed < 0:
            elapsed = 0.0
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round up to nearest integer without exceeding capacity.
            if self._balance < self._capacity:
                self._balance = math.ceil(self._balance)
                if self._balance > self._capacity:
                    self._balance = self._capacity
        self._last_time = now

    def available(self) -> float:
        """Return the current numeric balance without consuming tokens."""
        with self._lock:
            self._refill_locked()
            return self._balance

    def allow(self, amount: float = 1) -> bool:
        """Try to consume ``amount`` tokens. Returns True on success."""
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