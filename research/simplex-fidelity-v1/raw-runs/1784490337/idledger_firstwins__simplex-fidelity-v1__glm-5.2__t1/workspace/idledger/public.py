"""Public API for the :mod:`idledger` package.

This module exposes three names:

* :class:`Ledger` -- an idempotent, thread-safe ledger of integer-cent
  account balances.
* :class:`InsufficientFunds` -- raised when a debit would make a balance
  negative.
* :class:`CommandConflict` -- part of the public API surface for command-id
  reuse.

Only the Python standard library is imported here.
"""

import threading
from collections.abc import Mapping


__all__ = ["Ledger", "InsufficientFunds", "CommandConflict"]


def _is_int(value):
    """Return ``True`` only for genuine integers (booleans are excluded)."""
    return isinstance(value, int) and not isinstance(value, bool)


class InsufficientFunds(Exception):
    """Raised when a debit would leave an account with a negative balance.

    The ledger's state is left unchanged and the command id is not consumed.
    """

    def __init__(self, account, balance, amount):
        self.account = account
        self.balance = balance
        self.amount = amount
        super().__init__(
            "debit of {} from account {!r} with balance {} would result in a "
            "negative balance".format(amount, account, balance)
        )


class CommandConflict(Exception):
    """Public exception type for command-id reuse scenarios.

    The ledger follows a "first successful command wins" policy: reusing a
    successful command id returns the original result without re-applying the
    command, so :meth:`Ledger.apply` does not raise this exception. It is
    exposed so callers can catch or subclass it when layering stricter
    semantics on top of the ledger.
    """


class Ledger:
    """An idempotent, thread-safe ledger of integer-cent account balances.

    Balances and command amounts are integer cents. No successful operation
    ever leaves a balance negative.
    """

    _REQUIRED_KEYS = frozenset(("id", "account", "kind", "amount"))
    _VALID_KINDS = frozenset(("credit", "debit"))

    def __init__(self, initial=None):
        self._lock = threading.RLock()
        if initial is None:
            balances = {}
        else:
            balances = self._validate_initial(initial)
        self._balances = balances
        # Maps command id -> the result dict of the first successful command.
        self._results = {}

    # -- validation ---------------------------------------------------------

    @staticmethod
    def _validate_initial(initial):
        if not isinstance(initial, Mapping):
            raise ValueError("initial balances must be a mapping or None")
        balances = {}
        for name, value in initial.items():
            if not isinstance(name, str):
                raise ValueError(
                    "account name must be a string, got {!r}".format(name)
                )
            if not _is_int(value) or value < 0:
                raise ValueError(
                    "balance for account {!r} must be a non-negative integer, "
                    "got {!r}".format(name, value)
                )
            balances[name] = value
        return balances

    def _validate_command(self, command):
        if not isinstance(command, Mapping):
            raise ValueError("command must be a mapping")
        keys = set(command.keys())
        if keys != self._REQUIRED_KEYS:
            raise ValueError(
                "command must have exactly the keys id, account, kind, amount; "
                "got {}".format(sorted(keys, key=repr))
            )
        cid = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]
        try:
            hash(cid)
        except TypeError:
            raise ValueError("command id must be hashable, got {!r}".format(cid))
        if not isinstance(account, str):
            raise ValueError("account must be a string, got {!r}".format(account))
        if kind not in self._VALID_KINDS:
            raise ValueError(
                "kind must be 'credit' or 'debit', got {!r}".format(kind)
            )
        if not _is_int(amount) or amount <= 0:
            raise ValueError(
                "amount must be a positive integer, got {!r}".format(amount)
            )
        return cid, account, kind, amount

    # -- public API ---------------------------------------------------------

    def snapshot(self):
        """Return a new dict of balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply a command idempotently and return its result.

        ``command`` must be a mapping with exactly the keys ``id``,
        ``account``, ``kind`` and ``amount``. ``kind`` must be ``"credit"`` or
        ``"debit"`` and ``amount`` a positive integer of cents. A success
        returns a mapping with exactly ``id``, ``account`` and ``balance``.
        """
        with self._lock:
            cid, account, kind, amount = self._validate_command(command)
            # Idempotency: the first successful command for an id wins.
            if cid in self._results:
                return dict(self._results[cid])
            balance = self._balances.get(account, 0)
            if kind == "debit":
                if balance - amount < 0:
                    raise InsufficientFunds(account, balance, amount)
                balance -= amount
            else:  # credit
                balance += amount
            self._balances[account] = balance
            result = {"id": cid, "account": account, "balance": balance}
            self._results[cid] = result
            return dict(result)