"""Token-bucket implementation.

The bucket starts full. ``allow`` and ``available`` first refill based on the
elapsed time reported by the supplied clock, then operate on the resulting
balance. A backward clock movement is treated as zero elapsed time. After each
positive-time refill and capacity clamp, the balance is rounded down to the
nearest integer before answering the operation.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional


def _default_clock() -> float:
    """Return the current monotonic time in seconds (stdlib only)."""
    import time

    return time.monotonic()


class Bucket:
    """A token-bucket rate limiter with an injectable clock."""

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        # Validate constructor arguments (R6).
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
        self._clock = clock if clock is not None else _default_clock

        # Start full (R1).
        self._balance = float(capacity)
        self._last_time = self._clock()

        # Serialise allow/available so concurrent consumption cannot exceed
        # the available balance (R7).
        self._lock = threading.Lock()

    def _refill_locked(self) -> None:
        """Recompute the balance based on elapsed time. Caller must hold the lock."""
        now = self._clock()
        elapsed = now - self._last_time
        # Backward clock movement is treated as zero elapsed time (R3).
        if elapsed < 0:
            elapsed = 0.0
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            # Never exceed capacity (R3).
            if self._balance > self._capacity:
                self._balance = self._capacity
            # Round down to the nearest integer after a positive-time refill (R4).
            self._balance = float(int(self._balance))
            self._last_time = now

    def available(self) -> float:
        """Return the current numeric balance without consuming tokens (R5)."""
        with self._lock:
            self._refill_locked()
            return self._balance

    def allow(self, amount: float = 1) -> bool:
        """Try to consume ``amount`` tokens. Return True on success (R2)."""
        # Validate the consumption amount (R6, X1).
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