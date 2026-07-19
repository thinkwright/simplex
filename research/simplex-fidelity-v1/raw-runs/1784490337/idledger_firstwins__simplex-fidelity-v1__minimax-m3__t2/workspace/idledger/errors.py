"""Custom exceptions for the idledger package."""


class InsufficientFunds(Exception):
    """Raised when a debit would cause an account balance to go negative."""


class CommandConflict(Exception):
    """Raised when a command id is reused with different command content."""