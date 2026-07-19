#!/usr/bin/env python3
"""Comprehensive tests for the idledger package."""

import threading
import sys

# E7: Check that only stdlib is used
import idledger
import idledger.public
import inspect

def check_dependencies():
    """E7: verify only stdlib dependencies."""
    source = inspect.getsource(idledger.public)
    # Only imports should be threading from stdlib
    import_lines = [l.strip() for l in source.split('\n') if l.strip().startswith('import ') or l.strip().startswith('from ')]
    for line in import_lines:
        # Should only import threading (stdlib)
        assert 'threading' in line or line.startswith('from idledger'), f"Unexpected import: {line}"
    print("E7 PASS: only stdlib dependencies")

def test_e1_basic_apply():
    """E1: Ledger({a: 100}).apply({id: c1, account: a, kind: debit, amount: 40}) → {id: c1, account: a, balance: 60}"""
    from idledger import Ledger
    ledger = Ledger({"a": 100})
    result = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
    assert result == {"id": "c1", "account": "a", "balance": 60}, f"Got: {result}"
    print("E1 PASS: basic apply")

def test_e2_idempotency():
    """E2: applying the same successful command twice → second result equals first, balance changes once."""
    from idledger import Ledger
    ledger = Ledger({"a": 100})
    r1 = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
    r2 = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
    assert r1 == r2, f"Results differ: {r1} vs {r2}"
    assert ledger.snapshot() == {"a": 60}, f"Balance wrong: {ledger.snapshot()}"
    print("E2 PASS: idempotency")

def test_e3_conflict_replace():
    """E3: replace c1 debit 40 with c1 credit 20 → reverse the debit, apply the credit, balance 120."""
    from idledger import Ledger
    ledger = Ledger({"a": 100})
    r1 = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 40})
    assert r1 == {"id": "c1", "account": "a", "balance": 60}
    r2 = ledger.apply({"id": "c1", "account": "a", "kind": "credit", "amount": 20})
    assert r2 == {"id": "c1", "account": "a", "balance": 120}, f"Got: {r2}"
    assert ledger.snapshot() == {"a": 120}, f"Snapshot: {ledger.snapshot()}"
    print("E3 PASS: conflict replace")

def test_e4_insufficient_funds():
    """E4: debit 101 from balance 100 → InsufficientFunds, command id reusable."""
    from idledger import Ledger, InsufficientFunds
    ledger = Ledger({"a": 100})
    try:
        ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 101})
        assert False, "Should have raised InsufficientFunds"
    except InsufficientFunds:
        pass
    # Command id should be reusable
    result = ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 50})
    assert result == {"id": "c1", "account": "a", "balance": 50}, f"Got: {result}"
    assert ledger.snapshot() == {"a": 50}
    print("E4 PASS: insufficient funds")

def test_e5_invalid_commands():
    """E5: amount true, zero, or extra fields → ValueError, no state change."""
    from idledger import Ledger
    ledger = Ledger({"a": 100})

    # amount=True (bool, not int)
    try:
        ledger.apply({"id": "c1", "account": "a", "kind": "credit", "amount": True})
        assert False, "Should raise ValueError for bool amount"
    except ValueError:
        pass
    assert ledger.snapshot() == {"a": 100}

    # amount=0
    try:
        ledger.apply({"id": "c2", "account": "a", "kind": "credit", "amount": 0})
        assert False, "Should raise ValueError for zero amount"
    except ValueError:
        pass
    assert ledger.snapshot() == {"a": 100}

    # extra fields
    try:
        ledger.apply({"id": "c3", "account": "a", "kind": "credit", "amount": 10, "extra": "bad"})
        assert False, "Should raise ValueError for extra fields"
    except ValueError:
        pass
    assert ledger.snapshot() == {"a": 100}

    # missing fields
    try:
        ledger.apply({"id": "c4", "account": "a"})
        assert False, "Should raise ValueError for missing fields"
    except ValueError:
        pass
    assert ledger.snapshot() == {"a": 100}

    # negative amount
    try:
        ledger.apply({"id": "c5", "account": "a", "kind": "credit", "amount": -5})
        assert False, "Should raise ValueError for negative amount"
    except ValueError:
        pass
    assert ledger.snapshot() == {"a": 100}

    # invalid kind
    try:
        ledger.apply({"id": "c6", "account": "a", "kind": "transfer", "amount": 10})
        assert False, "Should raise ValueError for invalid kind"
    except ValueError:
        pass
    assert ledger.snapshot() == {"a": 100}

    # non-existent account
    try:
        ledger.apply({"id": "c7", "account": "b", "kind": "credit", "amount": 10})
        assert False, "Should raise ValueError for non-existent account"
    except ValueError:
        pass
    assert ledger.snapshot() == {"a": 100}

    print("E5 PASS: invalid commands")

def test_e6_concurrent_credits():
    """E6: concurrent distinct credits → final balance = initial + sum of all credits."""
    from idledger import Ledger
    ledger = Ledger({"a": 100})
    n = 100
    errors = []

    def apply_credit(i):
        try:
            ledger.apply({"id": f"c{i}", "account": "a", "kind": "credit", "amount": 1})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=apply_credit, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors: {errors}"
    snap = ledger.snapshot()
    assert snap == {"a": 200}, f"Expected 200, got {snap}"
    print("E6 PASS: concurrent credits")

def test_initial_validation():
    """Test invalid initial state."""
    from idledger import Ledger

    # Negative balance
    try:
        Ledger({"a": -1})
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # Non-integer balance
    try:
        Ledger({"a": 1.5})
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # Bool balance
    try:
        Ledger({"a": True})
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # Non-string account name
    try:
        Ledger({1: 100})
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # Non-dict initial
    try:
        Ledger([1, 2, 3])
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    print("PASS: initial validation")

def test_snapshot_sorted():
    """Test that snapshot returns sorted dict."""
    from idledger import Ledger
    ledger = Ledger({"c": 300, "a": 100, "b": 200})
    snap = ledger.snapshot()
    assert list(snap.keys()) == ["a", "b", "c"], f"Keys not sorted: {list(snap.keys())}"
    assert snap == {"a": 100, "b": 200, "c": 300}
    print("PASS: snapshot sorted")

def test_none_initial():
    """Test Ledger with no initial state."""
    from idledger import Ledger
    ledger = Ledger()
    assert ledger.snapshot() == {}
    print("PASS: None initial")

def test_conflict_replace_preserves_on_failure():
    """Test that if replacement fails, original is preserved."""
    from idledger import Ledger, CommandConflict
    ledger = Ledger({"a": 100})
    # Apply c1: credit 50 → a=150
    r1 = ledger.apply({"id": "c1", "account": "a", "kind": "credit", "amount": 50})
    assert r1 == {"id": "c1", "account": "a", "balance": 150}

    # Now try to replace c1 with a debit of 200 (would fail since after reversing credit, a=100)
    try:
        ledger.apply({"id": "c1", "account": "a", "kind": "debit", "amount": 200})
        assert False, "Should raise CommandConflict"
    except CommandConflict:
        pass

    # Original should be preserved: a=150
    assert ledger.snapshot() == {"a": 150}, f"Got: {ledger.snapshot()}"
    # Re-applying original should return cached result
    r2 = ledger.apply({"id": "c1", "account": "a", "kind": "credit", "amount": 50})
    assert r2 == {"id": "c1", "account": "a", "balance": 150}
    print("PASS: conflict preserves original on failure")

def test_conflict_reverse_fails():
    """Test that if reversing original fails, original is preserved."""
    from idledger import Ledger, CommandConflict
    ledger = Ledger({"a": 100, "b": 0})
    # Apply c1: credit 50 to a → a=150
    r1 = ledger.apply({"id": "c1", "account": "a", "kind": "credit", "amount": 50})
    assert r1 == {"id": "c1", "account": "a", "balance": 150}

    # Debit 150 from a → a=0
    ledger.apply({"id": "c2", "account": "a", "kind": "debit", "amount": 150})
    assert ledger.snapshot()["a"] == 0

    # Now try to replace c1 with credit 10 to b
    # Reversing c1 (credit 50 to a) means debit 50 from a, but a=0 → fails
    try:
        ledger.apply({"id": "c1", "account": "b", "kind": "credit", "amount": 10})
        assert False, "Should raise CommandConflict"
    except CommandConflict:
        pass

    # State should be unchanged: a=0, b=0
    assert ledger.snapshot() == {"a": 0, "b": 0}, f"Got: {ledger.snapshot()}"
    print("PASS: conflict reverse fails preserves original")

def test_imports():
    """R1: verify imports work."""
    from idledger import Ledger, InsufficientFunds, CommandConflict
    from idledger.public import Ledger as L2, InsufficientFunds as IF2, CommandConflict as CC2
    assert Ledger is L2
    assert InsufficientFunds is IF2
    assert CommandConflict is CC2
    print("PASS: imports")

if __name__ == "__main__":
    test_imports()
    test_e1_basic_apply()
    test_e2_idempotency()
    test_e3_conflict_replace()
    test_e4_insufficient_funds()
    test_e5_invalid_commands()
    test_e6_concurrent_credits()
    check_dependencies()
    test_initial_validation()
    test_snapshot_sorted()
    test_none_initial()
    test_conflict_replace_preserves_on_failure()
    test_conflict_reverse_fails()
    print("\n=== ALL TESTS PASSED ===")
