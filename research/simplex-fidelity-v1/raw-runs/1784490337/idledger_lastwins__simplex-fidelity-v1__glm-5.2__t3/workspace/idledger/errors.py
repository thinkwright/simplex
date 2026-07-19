"""Exception types for the idledger package."""


class LedgerError(Exception):
    """Base class for all idledger errors."""


class InsufficientFunds(LedgerError):
    """Raised when a debit would leave an account with a negative balance."""


class CommandConflict(LedgerError):
    """Raised when a conflicting command id cannot atomically replace the
    original command without violating the ledger invariants."""