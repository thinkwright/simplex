"""Verification tests for all examples E1–E6."""

import threading
import time
from tokenquota.public import Bucket


def test_e1():
    """capacity-2 bucket → allow(1) true twice then false."""
    t = [0.0]
    clock = lambda: t[0]
    b = Bucket(2, 0, clock=clock)
    assert b.allow(1) is True, "first allow should be True"
    assert b.allow(1) is True, "second allow should be True"
    assert b.allow(1) is False, "third allow should be False"
    print("E1 passed ✓")


def test_e2():
    """capacity-3, refill 0.5, advance 3s → available() is 2."""
    t = [0.0]
    clock = lambda: t[0]
    b = Bucket(3, 0.5, clock=clock)
    # empty the bucket
    b.allow(3)
    assert b.available() == 0, f"should be 0 after emptying, got {b.available()}"
    # advance 3 seconds → 3 * 0.5 = 1.5, ceil → 2
    t[0] = 3.0
    avail = b.available()
    assert avail == 2, f"expected 2, got {avail}"
    print("E2 passed ✓")


def test_e3():
    """advancing far beyond capacity or backward clock → balance never exceeds capacity."""
    t = [0.0]
    clock = lambda: t[0]
    b = Bucket(5, 10, clock=clock)
    # empty it
    b.allow(5)
    # advance a huge amount
    t[0] = 1000.0
    avail = b.available()
    assert avail <= 5, f"balance {avail} exceeds capacity 5"
    assert avail == 5, f"expected 5, got {avail}"

    # backward clock
    t[0] = 500.0
    avail2 = b.available()
    assert avail2 == 5, f"backward clock changed balance: {avail2}"
    print("E3 passed ✓")


def test_e4():
    """capacity 0, negative refill, allow(True) → ValueError."""
    errors = []
    try:
        Bucket(0, 1)
    except ValueError:
        pass
    else:
        errors.append("capacity 0 did not raise ValueError")

    try:
        Bucket(1, -1)
    except ValueError:
        pass
    else:
        errors.append("negative refill did not raise ValueError")

    t = [0.0]
    b = Bucket(5, 0, clock=lambda: t[0])
    try:
        b.allow(True)
    except ValueError:
        pass
    else:
        errors.append("allow(True) did not raise ValueError")

    assert not errors, "; ".join(errors)
    print("E4 passed ✓")


def test_e5():
    """many concurrent allow(1) calls, capacity-N, no refill → exactly N succeed."""
    N = 100
    t = [0.0]
    b = Bucket(N, 0, clock=lambda: t[0])
    results = []
    lock = threading.Lock()

    def worker():
        r = b.allow(1)
        with lock:
            results.append(r)

    threads = [threading.Thread(target=worker) for _ in range(N * 3)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    successes = sum(1 for r in results if r)
    failures = sum(1 for r in results if not r)
    assert successes == N, f"expected {N} successes, got {successes}"
    assert failures == N * 2, f"expected {N*2} failures, got {failures}"
    print("E5 passed ✓")


def test_e6():
    """fake clock fully controls refill; only stdlib deps."""
    t = [100.0]
    clock = lambda: t[0]
    b = Bucket(10, 2, clock=clock)
    b.allow(10)  # empty
    assert b.available() == 0

    t[0] = 101.0  # 1 second → 2 tokens
    assert b.available() == 2

    t[0] = 103.0  # 2 more seconds → 4 more tokens → 6
    assert b.available() == 6

    # Check only stdlib imports
    import tokenquota._bucket as mod
    import inspect
    source = inspect.getsource(mod)
    # Only imports should be: math, threading, time (all stdlib)
    import_lines = [l.strip() for l in source.splitlines() if l.strip().startswith("import ") or l.strip().startswith("from ")]
    for line in import_lines:
        for pkg in ["math", "threading", "time"]:
            if pkg in line:
                break
        else:
            raise AssertionError(f"non-stdlib import found: {line}")
    print("E6 passed ✓")


if __name__ == "__main__":
    test_e1()
    test_e2()
    test_e3()
    test_e4()
    test_e5()
    test_e6()
    print("\nAll tests passed! ✓✓✓")
