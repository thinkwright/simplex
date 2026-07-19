"""Token-bucket implementation.

A token bucket holds up to ``capacity`` tokens and refills at
``refill_per_second`` tokens per second of elapsed wall-clock time.
The clock source is injectable so tests can drive time deterministically.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional, Union

Number = Union[int, float]


def _default_clock() -> float:
    """Return the current monotonic time in seconds."""
    return _monotonic()


try:
    from time import monotonic as _monotonic
except ImportError:  # pragma: no cover - extremely old Python fallback
    from time import time as _monotonic  # type: ignore[assignment]


class Bucket:
    """A token bucket with an injectable clock.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be > 0.
    refill_per_second:
        Tokens added per elapsed second. Must be >= 0.
    clock:
        Callable returning the current time in seconds. Defaults to
        :func:`time.monotonic`. Used only for elapsed-time decisions.
    """

    def __init__(
        self,
        capacity: Number,
        refill_per_second: Number,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
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

        self._capacity: float = float(capacity)
        self._refill_per_second: float = float(refill_per_second)
        self._clock: Callable[[], float] = clock if clock is not None else _default_clock
        self._tokens: float = float(capacity)
        self._last_time: float = float(self._clock())
        self._lock = threading.Lock()

    def _refill_locked(self, now: float) -> None:
        elapsed = now - self._last_time
        if elapsed < 0:
            elapsed = 0
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_per_second)
            self._last_time = now

    def _refill(self) -> None:
        now = float(self._clock())
        self._refill_locked(now)

    def available(self) -> float:
        """Return the current token balance, refilling first.

        Does not consume any tokens.
        """
        with self._lock:
            self._refill()
            return self._tokens

    def allow(self, amount: Number = 1) -> bool:
        """Attempt to consume ``amount`` tokens.

        Refills first based on elapsed time, then consumes ``amount`` if
        enough tokens are available. Returns ``True`` on success and
        ``False`` otherwise. On failure no tokens are consumed.

        Raises ``ValueError`` for invalid ``amount`` values.
        """
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False