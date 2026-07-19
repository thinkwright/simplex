#!/usr/bin/env python3
"""Demonstration of the idledger API."""

from idledger import Ledger, InsufficientFunds, CommandConflict

# Example 1: Basic usage
print("Example 1: Basic debit")
ledger = Ledger({'a': 100})
result = ledger.apply({'id': 'c1', 'account': 'a', 'kind': 'debit', 'amount': 40})
print(f"  Result: {result}")
print(f"  Snapshot: {ledger.snapshot()}")

# Example 2: Idempotency
print("\nExample 2: Idempotency")
ledger2 = Ledger({'a': 100})
r1 = ledger2.apply({'id': 'c1', 'account': 'a', 'kind': 'debit', 'amount': 40})
r2 = ledger2.apply({'id': 'c1', 'account': 'a', 'kind': 'debit', 'amount': 40})
print(f"  First apply: {r1}")
print(f"  Second apply: {r2}")
print(f"  Balance: {ledger2.snapshot()}")

# Example 3: Command replacement
print("\nExample 3: Command replacement")
ledger3 = Ledger({'a': 100})
ledger3.apply({'id': 'c1', 'account': 'a', 'kind': 'debit', 'amount': 40})
print(f"  After debit 40: {ledger3.snapshot()}")
result = ledger3.apply({'id': 'c1', 'account': 'a', 'kind': 'credit', 'amount': 20})
print(f"  After replacing with credit 20: {result}")
print(f"  Final balance: {ledger3.snapshot()}")

# Example 4: Insufficient funds
print("\nExample 4: Insufficient funds")
ledger4 = Ledger({'a': 100})
try:
    ledger4.apply({'id': 'c1', 'account': 'a', 'kind': 'debit', 'amount': 101})
except InsufficientFunds as e:
    print(f"  Error: {e}")
print(f"  Balance unchanged: {ledger4.snapshot()}")

# Example 5: Invalid command
print("\nExample 5: Invalid command")
ledger5 = Ledger({'a': 100})
try:
    ledger5.apply({'id': 'c1', 'account': 'a', 'kind': 'debit', 'amount': 0})
except ValueError as e:
    print(f"  Error: {e}")
print(f"  Balance unchanged: {ledger5.snapshot()}")

print("\n✓ All examples completed successfully!")
