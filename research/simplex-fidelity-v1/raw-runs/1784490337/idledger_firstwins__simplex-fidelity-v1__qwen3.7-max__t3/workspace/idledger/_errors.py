class InsufficientFunds(Exception):
    """Raised when a debit would make a balance negative."""
    pass


class CommandConflict(Exception):
    """Raised on command-id conflicts."""
    pass
