"""Exception classes for idledger."""


class InsufficientFunds(Exception):
    """Raised when a debit would result in a negative balance."""
    pass


class CommandConflict(Exception):
    """Raised when a command id conflict cannot be resolved."""
    pass
