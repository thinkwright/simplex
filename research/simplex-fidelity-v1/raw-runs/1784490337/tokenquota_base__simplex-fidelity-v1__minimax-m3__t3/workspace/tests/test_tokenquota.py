"""Tests for the tokenquota package.

Covers examples E1..E6 from the spec.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import unittest


# Make the in-tree package importable without installation.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tokenquota import Bucket  # noqa: E402


class FakeClock:
    """A manually-advanced clock used to make time deterministic."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class E1CapacityTwoAtTimeZero(unittest.TestCase):
    """E1: capacity-2 bucket at time 0 -> allow(1) twice then false."""

    def test_two_consumptions_then_false(self) -> None:
        clock = FakeClock(0.0)
        b = Bucket(capacity=2, refill_per_second=0, clock=clock)
        self.assertTrue(b.allow(1))
        self.assertTrue(b.allow(1))
        self.assertFalse(b.allow(1))


class E2RefillAfterThreeSeconds(unittest.TestCase):
    """E2: empty capacity-3 bucket, rate 0.5, +3s -> available() == 1.5."""

    def test_fractional_balance(self) -> None:
        clock = FakeClock(0.0)
        b = Bucket(capacity=3, refill_per_second=0.5, clock=clock)
        # Drain it.
        self.assertTrue(b.allow(3))
        self.assertFalse(b.allow(1))
        clock.advance(3)
        self.assertEqual(b.available(), 1.5)


class E3BackwardClockAndOverflow(unittest.TestCase):
    """E3: backward clock and far-future clock never exceed capacity."""

    def test_backward_clock_does_not_add_tokens(self) -> None:
        clock = FakeClock(100.0)
        b = Bucket(capacity=2, refill_per_second=1, clock=clock)
        # Move the clock backward.
        clock.now = 50.0
        # No tokens should have been added.
        self.assertEqual(b.available(), 2.0)

    def test_far_future_does_not_exceed_capacity(self) -> None:
        clock = FakeClock(0.0)
        b = Bucket(capacity=2, refill_per_second=10, clock=clock)
        clock.advance(10_000)
        self.assertEqual(b.available(), 2.0)


class E4InvalidArguments(unittest.TestCase):
    """E4: capacity 0, negative refill, allow(True) -> ValueError."""

    def test_capacity_zero(self) -> None:
        with self.assertRaises(ValueError):
            Bucket(capacity=0, refill_per_second=1)

    def test_negative_refill(self) -> None:
        with self.assertRaises(ValueError):
            Bucket(capacity=1, refill_per_second=-0.1)

    def test_allow_true(self) -> None:
        b = Bucket(capacity=1, refill_per_second=0)
        with self.assertRaises(ValueError):
            b.allow(True)

    def test_invalid_amount_does_not_consume(self) -> None:
        # X1: invalid amount must not consume tokens.
        b = Bucket(capacity=2, refill_per_second=0)
        with self.assertRaises(ValueError):
            b.allow(0)
        with self.assertRaises(ValueError):
            b.allow(-1)
        # Balance untouched.
        self.assertEqual(b.available(), 2.0)


class E5ConcurrentConsumption(unittest.TestCase):
    """E5: many concurrent allow(1) on a full capacity-N bucket -> exactly N succeed."""

    def test_exactly_n_succeed(self) -> None:
        n = 100
        b = Bucket(capacity=n, refill_per_second=0)
        successes = []
        lock = threading.Lock()

        def worker() -> None:
            ok = b.allow(1)
            with lock:
                successes.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(n * 5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sum(1 for s in successes if s), n)
        self.assertEqual(b.available(), 0.0)


class E6FakeClockAndStdlibOnly(unittest.TestCase):
    """E6: fake clock controls refill; only stdlib dependencies."""

    def test_fake_clock_controls_refill(self) -> None:
        clock = FakeClock(0.0)
        b = Bucket(capacity=2, refill_per_second=1, clock=clock)
        # Drain.
        self.assertTrue(b.allow(2))
        self.assertEqual(b.available(), 0.0)
        # Advance 1.5 seconds -> 1.5 tokens.
        clock.advance(1.5)
        self.assertEqual(b.available(), 1.5)
        # Advance another 10 seconds -> capped at capacity.
        clock.advance(10)
        self.assertEqual(b.available(), 2.0)

    def test_only_stdlib_dependencies(self) -> None:
        # The package must import without any third-party deps.
        import tokenquota  # noqa: F401
        import tokenquota.public  # noqa: F401
        import tokenquota._bucket  # noqa: F401
        import tokenquota._clock  # noqa: F401

        # Sanity: time.monotonic is stdlib.
        self.assertTrue(hasattr(time, "monotonic"))


class ExtraRules(unittest.TestCase):
    """Additional checks for R1, R4, R5, R6, R7."""

    def test_starts_full(self) -> None:
        b = Bucket(capacity=5, refill_per_second=1)
        self.assertEqual(b.available(), 5.0)

    def test_fractional_tokens_preserved(self) -> None:
        clock = FakeClock(0.0)
        b = Bucket(capacity=10, refill_per_second=0.1, clock=clock)
        b.allow(10)
        clock.advance(0.3)  # 0.03 tokens
        self.assertAlmostEqual(b.available(), 0.03, places=12)

    def test_available_does_not_consume(self) -> None:
        clock = FakeClock(0.0)
        b = Bucket(capacity=2, refill_per_second=0, clock=clock)
        for _ in range(10):
            self.assertEqual(b.available(), 2.0)
        self.assertTrue(b.allow(1))

    def test_invalid_constructor_types(self) -> None:
        with self.assertRaises(ValueError):
            Bucket(capacity="x", refill_per_second=1)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            Bucket(capacity=1, refill_per_second="x")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()