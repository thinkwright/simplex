"""Exception types raised by the idledger package."""


class InsufficientFunds(Exception):
    """Raised when a debit would make an account balance negative."""


class CommandConflict(Exception):
    """Raised when a conflicting command id cannot be resolved.

    A conflict occurs when a command id has already been applied successfully
    and a new command with the same id differs from the original. The ledger
    attempts to atomically replace the original by reversing it and applying
    the replacement; this exception is raised only when that replacement
    itself fails (e.g. the replacement debit would overdraw the account).
    """