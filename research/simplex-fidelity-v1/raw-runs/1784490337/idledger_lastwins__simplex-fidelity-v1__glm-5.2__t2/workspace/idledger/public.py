"""Public API for the :mod:`idledger` package.

The ledger stores account balances as integer cents.  Every successful command
is recorded by its command id so that repeating an identical command is
idempotent (rule R4) and a conflicting command id atomically replaces the
original (rule R5).  All mutating operations are guarded by a lock so that
concurrent successful commands are each reflected exactly once (rule R8).
"""

import threading
from collections.abc import Mapping

__all__ = ["Ledger", "InsufficientFunds", "CommandConflict"]


class InsufficientFunds(Exception):
    """Raised when a debit (or a conflict replacement) would make a balance negative."""


class CommandConflict(Exception):
    """Raised for command-id conflicts that cannot be resolved.

    ``Ledger.apply`` resolves conflicts automatically (see rule R5); this
    exception is exposed as part of the public API so callers may distinguish
    conflict-related failures when they occur.
    """


def _is_int(value):
    """Return ``True`` for genuine integers; booleans are rejected."""
    return isinstance(value, int) and not isinstance(value, bool)


class Ledger:
    """An idempotent, thread-safe ledger of integer-cent account balances."""

    _REQUIRED_KEYS = frozenset({"id", "account", "kind", "amount"})
    _KINDS = frozenset({"credit", "debit"})

    def __init__(self, initial=None):
        self._balances = self._validate_initial(initial)
        self._history = {}
        self._lock = threading.RLock()

    # -- validation -------------------------------------------------------

    @staticmethod
    def _validate_initial(initial):
        if initial is None:
            return {}
        if not isinstance(initial, Mapping):
            raise ValueError("initial balances must be a mapping or None")
        validated = {}
        for name, balance in initial.items():
            try:
                hash(name)
            except TypeError:
                raise ValueError("account names must be hashable")
            if not _is_int(balance) or balance < 0:
                raise ValueError("initial balances must be non-negative integers")
            validated[name] = balance
        return validated

    @classmethod
    def _validate_command(cls, command):
        if not isinstance(command, Mapping):
            raise ValueError("command must be a mapping")
        # Always operate on a private copy so a caller mutating the command
        # object concurrently cannot corrupt the ledger's state.
        command = dict(command)
        if set(command.keys()) != cls._REQUIRED_KEYS:
            raise ValueError(
                "command must have exactly the keys: id, account, kind, amount"
            )
        if command["kind"] not in cls._KINDS:
            raise ValueError("command kind must be 'credit' or 'debit'")
        if not _is_int(command["amount"]) or command["amount"] <= 0:
            raise ValueError("command amount must be a positive integer")
        for field in ("id", "account"):
            try:
                hash(command[field])
            except TypeError:
                raise ValueError("command %r must be hashable" % field)
        return command

    # -- public API -------------------------------------------------------

    def snapshot(self):
        """Return a new account-name-sorted dict of the current balances."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply ``command`` and return its result.

        ``command`` must have exactly the keys ``id``, ``account``, ``kind``
        and ``amount`` where ``kind`` is ``credit`` or ``debit`` and ``amount``
        is a positive integer.  Repeating an identical command id returns the
        original result without re-applying; a conflicting command id
        atomically replaces the original.
        """
        command = self._validate_command(command)
        with self._lock:
            cid = command["id"]
            existing = self._history.get(cid)
            if existing is not None:
                stored_command, stored_result = existing
                if stored_command == command:
                    return dict(stored_result)
                return self._replace(stored_command, command)
            return self._apply_new(command)

    # -- internals --------------------------------------------------------

    def _apply_new(self, command):
        cid = command["id"]
        account = command["account"]
        amount = command["amount"]
        balance = self._balances.get(account, 0)
        if command["kind"] == "credit":
            new_balance = balance + amount
        else:
            new_balance = balance - amount
            if new_balance < 0:
                raise InsufficientFunds(
                    "debit of %d would make account %r negative"
                    % (amount, account)
                )
        self._balances[account] = new_balance
        result = {"id": cid, "account": account, "balance": new_balance}
        self._history[cid] = (command, dict(result))
        return dict(result)

    def _replace(self, stored_command, command):
        cid = command["id"]
        orig_account = stored_command["account"]
        orig_kind = stored_command["kind"]
        orig_amount = stored_command["amount"]
        new_account = command["account"]
        new_kind = command["kind"]
        new_amount = command["amount"]

        # Compute the tentative balances on a copy so the original state is
        # preserved untouched if the replacement cannot be applied.
        tentative = dict(self._balances)
        # Reverse the original command.
        if orig_kind == "credit":
            tentative[orig_account] = tentative.get(orig_account, 0) - orig_amount
        else:
            tentative[orig_account] = tentative.get(orig_account, 0) + orig_amount
        # Apply the replacement command.
        if new_kind == "credit":
            tentative[new_account] = tentative.get(new_account, 0) + new_amount
        else:
            tentative[new_account] = tentative.get(new_account, 0) - new_amount

        for account in (orig_account, new_account):
            if tentative.get(account, 0) < 0:
                # Replacement fails: leave all state and history unchanged so
                # the original command remains in effect.
                raise InsufficientFunds(
                    "replacement would make account %r negative" % (account,)
                )

        self._balances[orig_account] = tentative[orig_account]
        self._balances[new_account] = tentative[new_account]
        result = {
            "id": cid,
            "account": new_account,
            "balance": tentative[new_account],
        }
        self._history[cid] = (command, dict(result))
        return dict(result)