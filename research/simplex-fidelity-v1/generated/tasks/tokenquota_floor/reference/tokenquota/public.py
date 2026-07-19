from __future__ import annotations

import math
import time
from threading import RLock


MODE = "floor"


def _number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


class Bucket:
    def __init__(self, capacity, refill_per_second, clock=None):
        if not _number(capacity) or capacity <= 0:
            raise ValueError("capacity must be positive")
        if not _number(refill_per_second) or refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")
        if clock is not None and not callable(clock):
            raise ValueError("clock must be callable")
        self._capacity = float(capacity)
        self._rate = float(refill_per_second)
        self._clock = clock or time.monotonic
        self._tokens = float(capacity)
        self._last = float(self._clock())
        self._lock = RLock()

    def _refill(self) -> None:
        now = float(self._clock())
        if now <= self._last:
            return
        self._tokens = min(self._capacity, self._tokens + (now - self._last) * self._rate)
        self._last = now
        if MODE == "floor":
            self._tokens = math.floor(self._tokens)
        elif MODE == "ceiling":
            self._tokens = min(self._capacity, math.ceil(self._tokens))

    def allow(self, amount=1) -> bool:
        if not _number(amount) or amount <= 0:
            raise ValueError("amount must be positive")
        amount = float(amount)
        with self._lock:
            self._refill()
            if amount > self._tokens:
                return False
            self._tokens -= amount
            return True

    def available(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens
