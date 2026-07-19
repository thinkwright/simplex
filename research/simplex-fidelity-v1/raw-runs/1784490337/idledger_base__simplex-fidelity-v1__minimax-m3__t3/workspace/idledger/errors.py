"""Exception types raised by the ledger."""


class InsufficientFunds(Exception):
    """Raised when a debit would make a balance negative."""


class CommandConflict(Exception):
    """Raised when a command id is reused with different content."""