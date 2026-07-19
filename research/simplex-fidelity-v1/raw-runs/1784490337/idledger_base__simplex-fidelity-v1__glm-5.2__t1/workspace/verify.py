"""Verification script covering examples E1-E7 for the idledger package."""

import ast
import os
import sys
import threading

from idledger.public import CommandConflict, InsufficientFunds, Ledger


def expect_raises(exc, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc:
        return
    raise AssertionError("expected %s from %r" % (exc.__name__, fn))


# E1 -> R1, R2, R3, C1, D1 ------------------------------------------------
ledger = Ledger({"a": 100})
result = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
assert result == {"id": "c1", "account": "a", "balance": 60}, result
assert set(result.keys()) == {"id", "account", "balance"}, result
print("E1 ok:", result)

# E2 -> R4 -----------------------------------------------------------------
ledger = Ledger({"a": 100})
first = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
second = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
assert first == second, (first, second)
# The balance changes exactly once (idempotent replay does not re-apply).
assert ledger.snapshot() == {"a": 60}, ledger.snapshot()
print("E2 ok:", first, second, ledger.snapshot())

# E3 -> R5 -----------------------------------------------------------------
ledger = Ledger({"a": 100})
ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
expect_raises(CommandConflict, ledger.apply,
              {"id": "c1", "account": "a", "kind": "debit", "amount": 50})
assert ledger.snapshot() == {"a": 60}, ledger.snapshot()
# original result is still returned for the identical command
assert ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40}) == \
    {"id": "c1", "account": "a", "balance": 60}
print("E3 ok:", ledger.snapshot())

# E4 -> R6, X1 -------------------------------------------------------------
ledger = Ledger({"a": 100})
expect_raises(InsufficientFunds, ledger.apply,
              {"id": "c1", "account": "a", "kind": "debit", "amount": 101})
assert ledger.snapshot() == {"a": 100}, ledger.snapshot()
# the command id remains reusable after an insufficient-funds failure
reused = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
assert reused == {"id": "c1", "account": "a", "balance": 60}, reused
assert ledger.snapshot() == {"a": 60}, ledger.snapshot()
print("E4 ok:", reused, ledger.snapshot())

# E5 -> R7, X2 -------------------------------------------------------------
ledger = Ledger({"a": 100})
bad_commands = [
    {"id": "c1", "account": "a", "kind": "debit", "amount": True},   # bool amount
    {"id": "c1", "account": "a", "kind": "debit", "amount": 0},      # zero amount
    {"id": "c1", "account": "a", "kind": "debit", "amount": -5},     # negative
    {"id": "c1", "account": "a", "kind": "debit", "amount": 1.5},     # float
    {"id": "c1", "account": "a", "kind": "debit", "amount": "40"},    # string
    {"id": "c1", "account": "a", "kind": "debit", "amount": 40, "extra": 1},
    {"id": "c1", "account": "a", "kind": "debit"},                   # missing field
    {"id": "c1", "account": "a", "kind": "transfer", "amount": 40},   # bad kind
    {"account": "a", "kind": "debit", "amount": 40},                 # missing id
    "not a mapping",
]
for bad in bad_commands:
    expect_raises(ValueError, ledger.apply, bad)
assert ledger.snapshot() == {"a": 100}, ledger.snapshot()
# invalid initial state
expect_raises(ValueError, Ledger, {"a": -1})
expect_raises(ValueError, Ledger, {"a": True})
expect_raises(ValueError, Ledger, {"a": 1.5})
expect_raises(ValueError, Ledger, [1, 2, 3])
expect_raises(ValueError, Ledger, 100)
print("E5 ok")

# E6 -> R8 -----------------------------------------------------------------
ledger = Ledger({"a": 0})
N = 200


def credit_one(i):
    ledger.apply({"id": "c%d" % i, "account": "a", "kind": "credit", "amount": 1})


threads = [threading.Thread(target=credit_one, args=(i,)) for i in range(N)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert ledger.snapshot() == {"a": N}, ledger.snapshot()
print("E6 ok:", ledger.snapshot())

# Concurrent idempotency: same id from many threads applies exactly once.
ledger = Ledger({"a": 0})
M = 100


def same_id_credit():
    ledger.apply({"id": "shared", "account": "a", "kind": "credit", "amount": 7})


threads = [threading.Thread(target=same_id_credit) for _ in range(M)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert ledger.snapshot() == {"a": 7}, ledger.snapshot()
print("E6b ok (idempotent under concurrency):", ledger.snapshot())

# E7 -> C2 -----------------------------------------------------------------
import idledger  # noqa: E402

stdlib = set(sys.stdlib_module_names)
pkg_dir = os.path.dirname(idledger.__file__)
offenders = []
for fname in sorted(os.listdir(pkg_dir)):
    if not fname.endswith(".py"):
        continue
    path = os.path.join(pkg_dir, fname)
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top != "idledger" and top not in stdlib:
                    offenders.append((fname, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import within idledger
            if node.module is None:
                continue
            top = node.module.split(".")[0]
            if top != "idledger" and top not in stdlib:
                offenders.append((fname, node.module))
assert not offenders, offenders
print("E7 ok: every import is stdlib or idledger itself")

# A couple of extra sanity checks -----------------------------------------
# Credit to a brand-new account creates it starting from zero.
ledger = Ledger({})
r = ledger.apply({"id": "n1", "account": "new", "kind": "credit", "amount": 25})
assert r == {"id": "n1", "account": "new", "balance": 25}, r
assert ledger.snapshot() == {"new": 25}, ledger.snapshot()

# Debit down to exactly zero is allowed.
ledger = Ledger({"a": 100})
r = ledger.apply({"id": "d1", "account": "a", "kind": "debit", "amount": 100})
assert r == {"id": "d1", "account": "a", "balance": 0}, r
assert ledger.snapshot() == {"a": 0}, ledger.snapshot()

# snapshot returns an independent copy that does not mutate internal state.
ledger = Ledger({"a": 5})
snap = ledger.snapshot()
snap["a"] = 999
assert ledger.snapshot() == {"a": 5}, ledger.snapshot()

print("ALL OK")