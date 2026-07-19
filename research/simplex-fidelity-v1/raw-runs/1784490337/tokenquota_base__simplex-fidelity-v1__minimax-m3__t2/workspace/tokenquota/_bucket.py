"""Bucket implementation."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional


class Bucket:
    """A token-bucket rate limiter with an injectable clock."""

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = float(capacity)
        self._refill_per_second = float(refill_per_second)
        self._clock = clock if clock is not None else time.monotonic
        self._tokens = float(capacity)
        self._last = self._clock()
        self._lock = threading.Lock()

    def _refill_locked(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            elapsed = 0.0
        if elapsed > 0 and self._refill_per_second > 0:
            self._tokens += elapsed * self._refill_per_second
            if self._tokens > self._capacity:
                self._tokens = self._capacity
        self._last = now

    def allow(self, amount: float = 1) -> bool:
        if isinstance(amount, bool):
            raise ValueError("amount must not be a boolean")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill_locked()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False

    def available(self) -> float:
        with self._lock:
            self._refill_locked()
            return self._tokens