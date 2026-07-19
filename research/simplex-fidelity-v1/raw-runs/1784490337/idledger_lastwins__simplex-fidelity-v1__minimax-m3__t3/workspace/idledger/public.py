"""Public API for the idledger package.

Exposes:
    - Ledger: the main ledger class.
    - InsufficientFunds: raised when a debit would make a balance negative.
    - CommandConflict: raised when a conflicting command id cannot be resolved.
"""

from idledger.ledger import Ledger
from idledger.errors import InsufficientFunds, CommandConflict

__all__ = ["Ledger", "InsufficientFunds", "CommandConflict"]