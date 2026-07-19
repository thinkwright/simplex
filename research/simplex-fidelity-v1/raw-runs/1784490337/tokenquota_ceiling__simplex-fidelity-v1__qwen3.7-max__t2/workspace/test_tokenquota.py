"""Comprehensive tests for the tokenquota package."""

import threading
import sys

# ── E1: capacity-2 bucket, allow(1) true twice then false ──
def test_e1():
    from tokenquota.public import Bucket
    t = [0]
    clock = lambda: t[0]
    b = Bucket(2, 0, clock=clock)
    assert b.allow(1) is True, "first allow should be True"
    assert b.allow(1) is True, "second allow should be True"
    assert b.allow(1) is False, "third allow should be False"
    print("E1 passed")

# ── E2: capacity-3, refill 0.5, advance 3s → available() is 2 ──
def test_e2():
    from tokenquota.public import Bucket
    t = [0]
    clock = lambda: t[0]
    b = Bucket(3, 0.5, clock=clock)
    # empty the bucket
    b.allow(1); b.allow(1); b.allow(1)
    assert b.available() == 0, f"should be 0 after emptying, got {b.available()}"
    t[0] = 3  # advance 3 seconds → 3 * 0.5 = 1.5 tokens, ceil → 2
    avail = b.available()
    assert avail == 2, f"expected 2, got {avail}"
    print("E2 passed")

# ── E3: backward clock and over-capacity ──
def test_e3():
    from tokenquota.public import Bucket
    t = [10]
    clock = lambda: t[0]
    b = Bucket(5, 1, clock=clock)
    # bucket starts full at 5
    assert b.available() == 5
    # advance far beyond capacity
    t[0] = 1000
    assert b.available() == 5, "should be clamped to capacity"
    # move clock backward
    t[0] = 500
    avail = b.available()
    assert avail == 5, f"backward clock should not change balance, got {avail}"
    print("E3 passed")

# ── E4: invalid constructor / allow args → ValueError ──
def test_e4():
    from tokenquota.public import Bucket
    # capacity 0
    try:
        Bucket(0, 1)
        assert False, "should raise ValueError for capacity 0"
    except ValueError:
        pass

    # negative refill
    try:
        Bucket(5, -1)
        assert False, "should raise ValueError for negative refill"
    except ValueError:
        pass

    # allow(True) → boolean
    t = [0]
    b = Bucket(5, 1, clock=lambda: t[0])
    try:
        b.allow(True)
        assert False, "should raise ValueError for allow(True)"
    except ValueError:
        pass

    # allow(0)
    try:
        b.allow(0)
        assert False, "should raise ValueError for allow(0)"
    except ValueError:
        pass

    # allow(-1)
    try:
        b.allow(-1)
        assert False, "should raise ValueError for allow(-1)"
    except ValueError:
        pass

    # negative capacity
    try:
        Bucket(-1, 1)
        assert False, "should raise ValueError for negative capacity"
    except ValueError:
        pass

    print("E4 passed")

# ── E5: concurrent allow(1) on capacity-N bucket with no refill → exactly N succeed ──
def test_e5():
    from tokenquota.public import Bucket
    N = 100
    t = [0]
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
    assert successes == N, f"expected exactly {N} successes, got {successes}"
    print("E5 passed")

# ── E6: fake clock controls refill, only stdlib deps ──
def test_e6():
    from tokenquota.public import Bucket
    t = [0]
    clock = lambda: t[0]
    b = Bucket(10, 2, clock=clock)
    b.allow(5)  # consume 5, balance = 5
    t[0] = 1    # 1s * 2 = 2 tokens added → 5+2=7
    assert b.available() == 7, f"expected 7, got {b.available()}"
    t[0] = 2    # another 1s * 2 = 2 → 7+2=9
    assert b.available() == 9, f"expected 9, got {b.available()}"

    # Check no non-stdlib imports
    import tokenquota.public as mod
    import inspect
    source = inspect.getsource(mod)
    # Only imports should be: math, threading, time (all stdlib)
    import_lines = [l.strip() for l in source.split('\n') if l.strip().startswith('import ') or l.strip().startswith('from ')]
    for line in import_lines:
        for stdlib in ('math', 'threading', 'time'):
            if stdlib in line:
                break
        else:
            assert False, f"non-stdlib import found: {line}"
    print("E6 passed")

# ── R4: rounding up to nearest integer ──
def test_r4_rounding():
    from tokenquota.public import Bucket
    t = [0]
    b = Bucket(10, 1, clock=lambda: t[0])
    b.allow(5)  # balance = 5
    t[0] = 0.1  # 0.1 * 1 = 0.1 → 5.1 → ceil → 6
    avail = b.available()
    assert avail == 6, f"expected 6 after ceil, got {avail}"
    print("R4 rounding passed")

# ── R4: rounding up but not exceeding capacity ──
def test_r4_capacity_clamp():
    from tokenquota.public import Bucket
    t = [0]
    b = Bucket(5, 1, clock=lambda: t[0])
    b.allow(1)  # balance = 4
    t[0] = 0.5  # 4 + 0.5 = 4.5 → ceil → 5 (== capacity, ok)
    avail = b.available()
    assert avail == 5, f"expected 5, got {avail}"

    # Now test where ceil would exceed capacity
    b2 = Bucket(5, 1, clock=lambda: t[0])
    t[0] = 0
    b2.allow(1)  # balance = 4
    t[0] = 100   # 4 + 100 = 104 → clamp to 5 → ceil(5) = 5
    avail2 = b2.available()
    assert avail2 == 5, f"expected 5, got {avail2}"
    print("R4 capacity clamp passed")

# ── D1: import from tokenquota.public ──
def test_d1():
    from tokenquota.public import Bucket
    b = Bucket(5, 1)
    assert b.allow(1) is True
    print("D1 passed")

# ── R6: boolean capacity/refill should raise ValueError ──
def test_r6_boolean_args():
    from tokenquota.public import Bucket
    try:
        Bucket(True, 1)
        assert False, "boolean capacity should raise ValueError"
    except ValueError:
        pass
    try:
        Bucket(5, True)
        assert False, "boolean refill should raise ValueError"
    except ValueError:
        pass
    print("R6 boolean args passed")


if __name__ == '__main__':
    test_d1()
    test_e1()
    test_e2()
    test_e3()
    test_e4()
    test_e5()
    test_e6()
    test_r4_rounding()
    test_r4_capacity_clamp()
    test_r6_boolean_args()
    print("\nAll tests passed!")
