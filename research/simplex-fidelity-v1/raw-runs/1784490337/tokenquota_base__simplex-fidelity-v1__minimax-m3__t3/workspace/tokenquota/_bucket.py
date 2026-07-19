"""Token-bucket implementation.

A :class:`Bucket` holds up to ``capacity`` tokens and refills at
``refill_per_second`` tokens per second of elapsed wall time. The
elapsed time is read from a supplied clock (or the default monotonic
clock) so that tests can fully control time.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from tokenquota._clock import default_clock


class Bucket:
    """A thread-safe token bucket.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold. Must be > 0.
    refill_per_second:
        Rate at which tokens are added per second of elapsed time.
        Must be >= 0.
    clock:
        Optional zero-argument callable returning the current time in
        seconds. Defaults to :func:`time.monotonic`. The clock is the
        sole source of elapsed-time decisions.
    """

    __slots__ = (
        "_capacity",
        "_refill_per_second",
        "_clock",
        "_balance",
        "_last_time",
        "_lock",
    )

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        # --- validation (R6) ---
        if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if isinstance(refill_per_second, bool) or not isinstance(
            refill_per_second, (int, float)
        ):
            raise ValueError("refill_per_second must be a non-negative number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")

        self._capacity = float(capacity)
        self._refill_per_second = float(refill_per_second)
        self._clock = clock if clock is not None else default_clock

        # Start full (R1).
        self._balance = float(capacity)
        self._last_time = self._clock()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _refill_locked(self) -> None:
        """Recompute the balance based on elapsed time.

        Must be called while holding ``self._lock``.
        """
        now = self._clock()
        elapsed = now - self._last_time
        # R3: backward clock movement is treated as zero elapsed time.
        if elapsed < 0:
            elapsed = 0.0
        if elapsed > 0:
            # R4: keep fractional tokens exactly; do not round.
            self._balance += elapsed * self._refill_per_second
            if self._balance > self._capacity:
                self._balance = self._capacity
            self._last_time = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def available(self) -> float:
        """Return the current token balance without consuming any.

        Performs the same refill calculation as :meth:`allow`.
        """
        with self._lock:
            self._refill_locked()
            return self._balance

    def allow(self, amount: float = 1) -> bool:
        """Attempt to consume ``amount`` tokens.

        Returns ``True`` and consumes the tokens on success, otherwise
        returns ``False`` without modifying the balance.
        """
        # R6 / X1: validate amount before doing anything else.
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            self._refill_locked()
            if self._balance >= amount:
                self._balance -= amount
                return True
            return False