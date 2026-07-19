"""Behavioural tests for the tokenquota package (standard library only).

Run with:  python test_tokenquota.py
"""

import threading

from tokenquota.public import Bucket
import tokenquota


class FakeClock:
    """A controllable clock: calling it returns the current time ``t``."""

    def __init__(self, t=0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _expect_valueerror(fn, what):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected ValueError for: %s" % what)


def test_public_api_imports():
    # D1 / R1: importable public API.
    assert tokenquota.Bucket is Bucket
    b = Bucket(1, 0, clock=FakeClock(0))
    assert b.allow(1) is True


def test_e1_capacity_two_at_time_zero():
    clock = FakeClock(0)
    b = Bucket(2, 0, clock=clock)
    assert b.allow(1) is True
    assert b.allow(1) is True
    assert b.allow(1) is False


def test_e2_refill_rounds_down():
    clock = FakeClock(0)
    b = Bucket(3, 0.5, clock=clock)
    # Empty the bucket.
    assert b.allow(3) is True
    assert b.available() == 0
    # Advance 3 seconds: 3 * 0.5 = 1.5 tokens, rounded down to 1 (R3, R4).
    clock.advance(3)
    assert b.available() == 1


def test_e3_clamp_and_backward_clock():
    clock = FakeClock(0)
    b = Bucket(5, 1, clock=clock)
    # Advancing far beyond capacity never exceeds capacity.
    clock.advance(1000)
    assert b.available() == 5
    # Moving the clock backward yields zero elapsed time: no tokens gained.
    clock.t = 0
    assert b.available() == 5
    clock.advance(10)  # still before the last seen time (1000)
    assert b.available() == 5
    # Once past the last seen time, refill resumes normally but is clamped.
    clock.t = 1003
    assert b.available() == 5


def test_e4_invalid_values_raise_valueerror():
    clock = FakeClock(0)
    _expect_valueerror(lambda: Bucket(0, 1, clock=clock), "capacity 0")
    _expect_valueerror(lambda: Bucket(-1, 1, clock=clock), "capacity -1")
    _expect_valueerror(lambda: Bucket(2, -1, clock=clock), "negative refill")

    b = Bucket(2, 1, clock=clock)
    _expect_valueerror(lambda: b.allow(True), "allow(True)")
    _expect_valueerror(lambda: b.allow(False), "allow(False)")
    _expect_valueerror(lambda: b.allow(0), "allow(0)")
    _expect_valueerror(lambda: b.allow(-1), "allow(-1)")
    _expect_valueerror(lambda: b.allow("x"), "allow('x')")
    # Invalid consumption must not consume tokens (X1).
    assert b.available() == 2


def test_e5_concurrent_consumption_exact():
    n = 200
    clock = FakeClock(0)
    b = Bucket(n, 0, clock=clock)
    results = []
    rlock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker():
        barrier.wait()
        ok = b.allow(1)
        with rlock:
            results.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = sum(1 for r in results if r)
    assert successes == n, "expected exactly %d successes, got %d" % (n, successes)
    assert b.available() == 0


def test_e6_fake_clock_controls_refill():
    clock = FakeClock(0)
    b = Bucket(2, 1, clock=clock)
    assert b.allow(2) is True
    # Empty, clock unchanged: no refill.
    assert b.allow(1) is False
    # Advance exactly 1 second: 1 token refilled.
    clock.advance(1)
    assert b.allow(1) is True
    assert b.allow(1) is False
    # Advance far: clamped to capacity.
    clock.advance(100)
    assert b.available() == 2


def test_default_clock_starts_full():
    # With the default clock the bucket still starts full and can consume.
    b = Bucket(2, 0)
    assert b.allow(1) is True
    assert b.allow(1) is True
    assert b.allow(1) is False


def test_available_does_not_consume():
    clock = FakeClock(0)
    b = Bucket(2, 1, clock=clock)
    assert b.available() == 2
    assert b.available() == 2
    assert b.allow(2) is True
    assert b.available() == 0


def test_fractional_amount():
    clock = FakeClock(0)
    b = Bucket(2, 0, clock=clock)
    assert b.allow(0.5) is True
    assert b.allow(0.5) is True
    assert b.allow(0.5) is True
    assert b.allow(0.5) is True
    assert b.allow(0.5) is False


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("\nALL %d TESTS PASSED" % len(tests))


if __name__ == "__main__":
    main()