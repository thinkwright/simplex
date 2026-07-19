"""Public API for the :mod:`idledger` package.

This module exposes :class:`Ledger`, :class:`InsufficientFunds`, and
:class:`CommandConflict`.  Only the Python standard library is used so that
the package has no third-party dependencies (see constraint C2).
"""

import threading

__all__ = ["Ledger", "InsufficientFunds", "CommandConflict"]


class InsufficientFunds(Exception):
    """Raised when a debit would leave an account with a negative balance."""


class CommandConflict(Exception):
    """Raised when a command id is reused with conflicting content.

    The ledger semantics resolve id reuse by returning the original
    successful result (the first successful command wins), so this
    exception is part of the public surface for callers that wish to
    detect conflicts explicitly.
    """


def _is_integer_cents(value):
    """Return ``True`` when *value* is an ``int`` but not a ``bool``.

    Balances and command amounts are integer cents (constraint C1); a
    Python ``bool`` is technically an ``int`` subclass but is not a valid
    monetary amount, so it is rejected.
    """
    return isinstance(value, int) and not isinstance(value, bool)


class Ledger:
    """An idempotent, thread-safe ledger of integer-cent account balances.

    Balances are stored as integer cents and no successful operation may
    leave a negative balance (constraint C1).  Successful commands are
    recorded by id so that replaying an id returns the original result
    without reapplying the command (rules R4/R5).
    """

    _REQUIRED_KEYS = frozenset(("id", "account", "kind", "amount"))
    _VALID_KINDS = frozenset(("credit", "debit"))

    def __init__(self, initial=None):
        self._lock = threading.Lock()
        self._balances = {}
        self._results = {}
        if initial is not None:
            self._balances = self._validate_initial(initial)

    # -- validation helpers ------------------------------------------------

    @staticmethod
    def _validate_initial(initial):
        if not isinstance(initial, dict):
            raise ValueError(
                "initial must be a mapping of account names to "
                "non-negative integer balances"
            )
        validated = {}
        for account, balance in initial.items():
            if not _is_integer_cents(balance) or balance < 0:
                raise ValueError(
                    "initial balance for %r must be a non-negative "
                    "integer" % (account,)
                )
            validated[account] = balance
        return validated

    @staticmethod
    def _validate_command(command):
        if not isinstance(command, dict):
            raise ValueError("command must be a mapping")
        if set(command.keys()) != Ledger._REQUIRED_KEYS:
            raise ValueError(
                "command must have exactly the keys id, account, "
                "kind, and amount"
            )
        cmd_id = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]
        if kind not in Ledger._VALID_KINDS:
            raise ValueError("kind must be 'credit' or 'debit'")
        if not _is_integer_cents(amount) or amount <= 0:
            raise ValueError("amount must be a positive integer")
        for name, value in (("id", cmd_id), ("account", account)):
            try:
                hash(value)
            except TypeError:
                raise ValueError("%s must be hashable" % (name,))
        return cmd_id, account, kind, amount

    # -- public API --------------------------------------------------------

    def apply(self, command):
        """Apply *command* and return its result.

        *command* must be a mapping with exactly the keys ``id``,
        ``account``, ``kind`` and ``amount`` where ``kind`` is
        ``'credit'`` or ``'debit'`` and ``amount`` is a positive integer.
        A success returns a mapping with exactly ``id``, ``account`` and
        ``balance`` (rule R3).
        """
        cmd_id, account, kind, amount = self._validate_command(command)
        with self._lock:
            # Replaying a successful command id returns the original
            # result without reapplying the command (rules R4/R5).
            if cmd_id in self._results:
                return dict(self._results[cmd_id])
            current = self._balances.get(account, 0)
            if kind == "debit":
                if current < amount:
                    raise InsufficientFunds(
                        "debit of %d from %r would leave a negative "
                        "balance" % (amount, account)
                    )
                new_balance = current - amount
            else:
                new_balance = current + amount
            self._balances[account] = new_balance
            result = {"id": cmd_id, "account": account, "balance": new_balance}
            self._results[cmd_id] = result
            return dict(result)

    def snapshot(self):
        """Return a new account-name-sorted dict of the current balances."""
        with self._lock:
            return dict(sorted(self._balances.items()))