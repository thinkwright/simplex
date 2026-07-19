"""Comprehensive tests for tokenquota package."""
import sys
import threading
import time

# Test imports
from tokenquota.public import Bucket

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")

# ── E1: capacity-2 bucket at time 0 → allow(1) true twice then false ──
print("E1: Basic consumption")
t = [0.0]
clock = lambda: t[0]
b = Bucket(2, 0, clock=clock)
check("first allow(1) is True", b.allow(1) == True)
check("second allow(1) is True", b.allow(1) == True)
check("third allow(1) is False", b.allow(1) == False)

# ── E2: capacity-3, refill 0.5, advance 3s → available() is 1 ──
print("E2: Refill and available")
t = [0.0]
clock = lambda: t[0]
b = Bucket(3, 0.5, clock=clock)
b.allow(1); b.allow(1); b.allow(1)  # empty it
check("bucket is empty", b.available() == 0)
t[0] = 3.0  # advance 3 seconds → 3 * 0.5 = 1.5 → floor → 1
check("available() after 3s is 1", b.available() == 1)

# ── E3: advancing beyond capacity / backward clock ──
print("E3: Capacity clamp and backward clock")
t = [0.0]
clock = lambda: t[0]
b = Bucket(3, 1.0, clock=clock)
b.allow(3)  # empty it
check("empty bucket", b.available() == 0)
t[0] = 100.0  # way beyond capacity
check("never exceeds capacity", b.available() == 3)
t[0] = 50.0  # backward clock
check("backward clock no gain", b.available() == 3)

# ── E4: ValueError cases ──
print("E4: ValueError on invalid inputs")
try:
    Bucket(0, 1)
    check("capacity 0 raises ValueError", False)
except ValueError:
    check("capacity 0 raises ValueError", True)

try:
    Bucket(-1, 1)
    check("negative capacity raises ValueError", False)
except ValueError:
    check("negative capacity raises ValueError", True)

try:
    Bucket(5, -1)
    check("negative refill raises ValueError", False)
except ValueError:
    check("negative refill raises ValueError", True)

try:
    b = Bucket(5, 1)
    b.allow(True)
    check("allow(True) raises ValueError", False)
except ValueError:
    check("allow(True) raises ValueError", True)

try:
    b = Bucket(5, 1)
    b.allow(0)
    check("allow(0) raises ValueError", False)
except ValueError:
    check("allow(0) raises ValueError", True)

try:
    b = Bucket(5, 1)
    b.allow(-1)
    check("allow(-1) raises ValueError", False)
except ValueError:
    check("allow(-1) raises ValueError", True)

# ── E5: concurrent allow(1) calls → exactly N succeed ──
print("E5: Thread safety")
N = 100
t = [0.0]
clock = lambda: t[0]
b = Bucket(N, 0, clock=clock)
results = []
barrier = threading.Barrier(N)

def worker():
    barrier.wait()
    r = b.allow(1)
    results.append(r)

threads = [threading.Thread(target=worker) for _ in range(N)]
for th in threads:
    th.start()
for th in threads:
    th.join()

successes = sum(1 for r in results if r)
check(f"exactly {N} successes out of {N} calls", successes == N)

# Now try one more - should fail
check("one more allow(1) fails", b.allow(1) == False)

# ── E6: fake clock controls refill, only stdlib ──
print("E6: Fake clock and stdlib only")
fake_time = [0.0]
def fake_clock():
    return fake_time[0]

b = Bucket(5, 2.0, clock=fake_clock)
b.allow(5)  # empty
check("empty after consuming all", b.available() == 0)
fake_time[0] = 1.0  # 1 second → 2 tokens
check("fake clock: 2 tokens after 1s", b.available() == 2)
fake_time[0] = 2.0  # another second → 4 tokens total
check("fake clock: 4 tokens after 2s", b.available() == 4)

# Check no external dependencies
import tokenquota.public as mod
import inspect
source = inspect.getsource(mod)
# Only standard library imports
import_lines = [l.strip() for l in source.split('\n') if l.strip().startswith('import ') or l.strip().startswith('from ')]
stdlib_modules = {'time', 'threading', 'math'}
for line in import_lines:
    parts = line.replace('from ', '').replace('import ', '').split()[0].split('.')
    check(f"import '{line}' is stdlib", parts[0] in stdlib_modules)

# ── Additional edge cases ──
print("Additional: R4 rounding")
t = [0.0]
clock = lambda: t[0]
b = Bucket(10, 1.0, clock=clock)
b.allow(10)  # empty
t[0] = 1.5  # 1.5 tokens → floor → 1
check("floor(1.5) = 1", b.available() == 1)

print("Additional: allow default amount")
t = [0.0]
clock = lambda: t[0]
b = Bucket(2, 0, clock=clock)
check("allow() default is 1, first True", b.allow() == True)
check("allow() default is 1, second True", b.allow() == True)
check("allow() default is 1, third False", b.allow() == False)

print("Additional: allow does not consume on failure")
t = [0.0]
clock = lambda: t[0]
b = Bucket(1, 0, clock=clock)
check("allow(2) fails on capacity-1", b.allow(2) == False)
check("allow(1) still succeeds", b.allow(1) == True)

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
else:
    print("All tests passed!")
    sys.exit(0)
