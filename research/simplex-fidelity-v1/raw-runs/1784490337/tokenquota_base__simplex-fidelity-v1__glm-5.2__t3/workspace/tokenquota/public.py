"""Public API for the :mod:`tokenquota` package.

Exposes :class:`Bucket`, a thread-safe token-bucket rate limiter that uses
only the supplied clock for elapsed-time decisions and depends solely on the
Python standard library.
"""

import threading
import time

__all__ = ["Bucket"]


def _validate_number(value, name, *, allow_zero):
    """Validate that *value* is a real (non-boolean) number within range.

    Booleans are rejected even though ``bool`` subclasses ``int``: a truth
    value is not a meaningful capacity, rate, or consumption amount.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{name} must be a real number (int or float), "
            f"not {type(value).__name__}"
        )
    if allow_zero:
        if value < 0:
            raise ValueError(f"{name} must be non-negative, got {value!r}")
    else:
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value!r}")


class Bucket:
    """A thread-safe token bucket.

    The bucket starts full at *capacity* tokens and refills continuously at
    *refill_per_second* tokens per second.  Time is read from *clock*, a
    callable returning the current time as a number; when *clock* is ``None``
    the standard-library :func:`time.monotonic` clock is used.

    A backward clock movement is treated as zero elapsed time, the balance
    never exceeds *capacity*, and fractional tokens are preserved exactly
    (the balance is never rounded).
    """

    def __init__(self, capacity, refill_per_second, clock=None):
        _validate_number(capacity, "capacity", allow_zero=False)
        _validate_number(refill_per_second, "refill_per_second", allow_zero=True)

        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._clock = time.monotonic if clock is None else clock
        self._tokens = capacity
        self._last = self._clock()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill the bucket based on elapsed time.

        The caller must hold ``self._lock``.  Backward clock movement yields
        zero elapsed time; the balance is capped at *capacity* and is never
        rounded.
        """
        now = self._clock()
        elapsed = now - self._last
        if elapsed < 0:
            elapsed = 0
        self._last = now
        if elapsed:
            self._tokens = min(
                self._capacity,
                self._tokens + elapsed * self._refill_per_second,
            )

    def allow(self, amount=1):
        """Refill, then consume *amount* tokens if enough are available.

        Returns ``True`` and consumes the tokens when the balance is at least
        *amount*; otherwise returns ``False`` without consuming anything.
        """
        _validate_number(amount, "amount", allow_zero=False)
        with self._lock:
            self._refill()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False

    def available(self):
        """Refill and return the current token balance without consuming."""
        with self._lock:
            self._refill()
            return self._tokens