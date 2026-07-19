"""Public exception types for the idledger package."""

__all__ = ["InsufficientFunds", "CommandConflict"]


class InsufficientFunds(Exception):
    """Raised when a debit would leave an account with a negative balance."""


class CommandConflict(Exception):
    """Public exception type for the idledger package.

    Reusing a successful command id returns the original result without
    re-applying the command (the first successful command wins), so this
    exception is not raised by :class:`~idledger.ledger.Ledger` for that case.
    It is exposed as part of the public API surface so callers may use a shared
    exception type to represent command-id conflicts if they choose to.
    """