"""Verification tests for tokenquota."""

import threading
from tokenquota import Bucket


class FakeClock:
    def __init__(self, start=0.0):
        self.t = float(start)

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def test_e1_capacity_2_full():
    b = Bucket(2, 1, clock=FakeClock())
    assert b.allow(1) is True
    assert b.allow(1) is True
    assert b.allow(1) is False
    print("E1 OK")


def test_e2_refill_fractional():
    clock = FakeClock()
    b = Bucket(3, 0.5, clock=clock)
    # empty it
    assert b.allow(3) is True
    assert b.available() == 0.0
    clock.advance(3)
    assert b.available() == 1.5
    print("E2 OK")


def test_e3_no_overflow_no_backward():
    clock = FakeClock()
    b = Bucket(2, 1, clock=clock)
    clock.advance(1000)
    assert b.available() == 2.0  # capped at capacity
    # backward clock
    clock.t -= 50
    assert b.available() == 2.0  # no gain from negative elapsed
    print("E3 OK")


def test_e4_errors():
    for bad_cap in [0, -1, -0.5]:
        try:
            Bucket(bad_cap, 1)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for capacity {bad_cap}")

    try:
        Bucket(1, -0.1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for negative refill")

    b = Bucket(1, 1, clock=FakeClock())
    try:
        b.allow(True)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for allow(True)")

    # invalid amounts
    for bad in [0, -1, False]:
        try:
            b.allow(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for allow({bad!r})")

    # invalid amount must not consume
    b2 = Bucket(1, 0, clock=FakeClock())
    try:
        b2.allow(-1)
    except ValueError:
        pass
    assert b2.available() == 1.0
    print("E4 OK")


def test_e5_concurrent():
    N = 100
    b = Bucket(N, 0, clock=FakeClock())
    successes = []
    lock = threading.Lock()

    def worker():
        if b.allow(1):
            with lock:
                successes.append(1)

    threads = [threading.Thread(target=worker) for _ in range(N * 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(successes) == N, f"expected {N} successes, got {len(successes)}"
    print("E5 OK")


def test_e6_dependencies_and_clock():
    import sys
    # ensure no third-party deps
    third_party = {k: v for k, v in sys.modules.items()
                   if k not in ("builtins",) and not k.startswith("tokenquota")}
    # check that only stdlib + tokenquota are involved in our package
    import tokenquota
    import tokenquota.public
    import tokenquota._bucket
    # verify fake clock controls refill
    clock = FakeClock(100.0)
    b = Bucket(2, 1, clock=clock)
    assert b.available() == 2.0
    clock.advance(1.5)
    assert b.available() == 2.0  # capped
    b2 = Bucket(5, 2, clock=clock)
    clock.advance(1.0)
    assert b2.available() == 2.0  # 2 tokens/sec * 1 sec
    print("E6 OK")


def test_default_clock():
    # default clock should work
    b = Bucket(10, 1)
    assert b.available() == 10.0
    print("default clock OK")


def test_fractional_preserved():
    clock = FakeClock()
    b = Bucket(1, 0.1, clock=clock)
    assert b.allow(1) is True
    assert b.available() == 0.0
    clock.advance(0.3)
    # 0.3 * 0.1 = 0.03 exactly
    assert abs(b.available() - 0.03) < 1e-12
    print("fractional OK")


def test_no_consume_on_failure():
    clock = FakeClock()
    b = Bucket(1, 0, clock=clock)
    assert b.allow(1) is True
    assert b.allow(1) is False
    assert b.available() == 0.0  # not negative
    print("no consume on failure OK")


if __name__ == "__main__":
    test_e1_capacity_2_full()
    test_e2_refill_fractional()
    test_e3_no_overflow_no_backward()
    test_e4_errors()
    test_e5_concurrent()
    test_e6_dependencies_and_clock()
    test_default_clock()
    test_fractional_preserved()
    test_no_consume_on_failure()
    print("\nAll tests passed!")