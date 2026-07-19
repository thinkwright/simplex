"""Implementation of the token-bucket primitive.

Only the Python standard library is used. A pluggable clock supplies
elapsed-time information; the default clock is
``time.monotonic``.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional, Union

Number = Union[int, float]


def _default_clock() -> float:
    """Return the current monotonic time in seconds."""
    return time.monotonic()


class Bucket:
    """A token bucket with a capacity and a refill rate.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be > 0.
    refill_per_second:
        Tokens added per real second. Must be >= 0.
    clock:
        Optional zero-argument callable returning a monotonic time
        value in seconds. Used for elapsed-time decisions. Defaults
        to :func:`time.monotonic`.
    """

    def __init__(
        self,
        capacity: Number,
        refill_per_second: Number,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if not isinstance(capacity, (int, float)) or isinstance(capacity, bool):
            raise ValueError("capacity must be a positive number")
        if not isinstance(refill_per_second, (int, float)) or isinstance(refill_per_second, bool):
            raise ValueError("refill_per_second must be a non-negative number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity: float = float(capacity)
        self._refill_per_second: float = float(refill_per_second)
        self._clock: Callable[[], float] = clock if clock is not None else _default_clock

        self._balance: float = self._capacity
        self._last_time: float = float(self._clock())

        self._lock = threading.Lock()

    @property
    def capacity(self) -> float:
        return self._capacity

    @property
    def refill_per_second(self) -> float:
        return self._refill_per_second

    def _refill_locked(self) -> None:
        """Refill the bucket based on elapsed time. Caller must hold the lock."""
        now = float(self._clock())
        elapsed = now - self._last_time
        if elapsed < 0:
            # Backward clock movement: treat as zero elapsed time.
            elapsed = 0
        if elapsed > 0:
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            # R4: round down to nearest integer after a positive-time refill.
            self._balance = float(int(self._balance))
            self._last_time = now
        # If elapsed == 0, do nothing: balance and last_time unchanged.

    def available(self) -> float:
        """Return the current token balance without consuming tokens.

        Performs the same refill calculation as :meth:`allow`.
        """
        with self._lock:
            self._refill_locked()
            return self._balance

    def allow(self, amount: Number = 1) -> bool:
        """Attempt to consume ``amount`` tokens.

        Returns ``True`` and reduces the balance when enough tokens
        exist; otherwise returns ``False`` without consuming.
        """
        # Validate amount before acquiring the lock so a bad call
        # never touches state.
        if isinstance(amount, bool):
            raise ValueError("amount must be a positive number, not a boolean")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

        amount_f = float(amount)

        with self._lock:
            self._refill_locked()
            if self._balance >= amount_f:
                self._balance -= amount_f
                return True
            return False