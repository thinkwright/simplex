"""Idempotent, thread-safe ledger accounting in integer cents.

The ledger stores account balances as integer cents and never allows a
successful operation to leave a negative balance.  Commands are applied
idempotently: each command carries an ``id`` and applying an identical,
previously successful command returns the original result, while a
conflicting command (same id, different content) atomically replaces the
original command.
"""

import threading
from collections.abc import Mapping

from .errors import CommandConflict, InsufficientFunds


__all__ = ["Ledger"]

_FIELDS = ("id", "account", "kind", "amount")
_FIELD_SET = frozenset(_FIELDS)
_KINDS = ("credit", "debit")


def _is_int_cents(value):
    """Return True for a genuine integer that is not a bool."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_initial(initial):
    if not isinstance(initial, Mapping):
        raise ValueError(
            "initial must be a mapping of account names to non-negative "
            "integer balances"
        )
    for name, balance in initial.items():
        if not isinstance(name, str):
            raise ValueError("account names must be strings")
        if not _is_int_cents(balance) or balance < 0:
            raise ValueError("balances must be non-negative integers")


def _validate_command(command):
    if not isinstance(command, Mapping):
        raise ValueError("command must be a mapping")
    if set(command.keys()) != _FIELD_SET:
        raise ValueError(
            "command must have exactly the fields id, account, kind and amount"
        )
    if not isinstance(command["id"], str):
        raise ValueError("command id must be a string")
    if not isinstance(command["account"], str):
        raise ValueError("command account must be a string")
    if command["kind"] not in _KINDS:
        raise ValueError("command kind must be 'credit' or 'debit'")
    amount = command["amount"]
    if not _is_int_cents(amount) or amount <= 0:
        raise ValueError("command amount must be a positive integer")


class Ledger:
    """An idempotent, thread-safe ledger of integer-cent account balances."""

    def __init__(self, initial=None):
        self._lock = threading.RLock()
        self._balances = {}
        self._commands = {}
        self._results = {}
        if initial is not None:
            _validate_initial(initial)
            self._balances = dict(initial)

    def snapshot(self):
        """Return a new account-name-sorted dict mapping account -> balance."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply ``command`` idempotently and return its result.

        ``command`` must be a mapping with exactly the fields ``id``,
        ``account``, ``kind`` and ``amount`` where ``kind`` is ``'credit'`` or
        ``'debit'`` and ``amount`` is a positive integer.  A success returns a
        mapping with exactly ``id``, ``account`` and ``balance``.
        """
        # Validate before touching any state so an invalid command never
        # mutates balances or command history.
        _validate_command(command)
        with self._lock:
            cid = command["id"]
            stored = self._commands.get(cid)
            if stored is None:
                return self._apply_new(command)
            if stored == dict(command):
                # Identical repeat: return the original result, apply nothing.
                return dict(self._results[cid])
            return self._replace(stored, command)

    def _apply_new(self, command):
        cid = command["id"]
        account = command["account"]
        amount = command["amount"]
        current = self._balances.get(account, 0)
        if command["kind"] == "credit":
            new_balance = current + amount
        else:
            new_balance = current - amount
            if new_balance < 0:
                # Leave all state unchanged and do not consume the command id.
                raise InsufficientFunds(
                    "debit of {0} cents would leave account {1!r} negative".format(
                        amount, account
                    )
                )
        self._balances[account] = new_balance
        result = {"id": cid, "account": account, "balance": new_balance}
        self._commands[cid] = dict(command)
        self._results[cid] = dict(result)
        return dict(result)

    def _replace(self, original, replacement):
        cid = replacement["id"]
        # Work on a private copy so the original state is preserved if the
        # replacement cannot be committed.
        balances = dict(self._balances)

        orig_account = original["account"]
        # Reversing a credit subtracts; reversing a debit adds back.
        reverse_delta = (
            -original["amount"]
            if original["kind"] == "credit"
            else original["amount"]
        )

        rep_account = replacement["account"]
        apply_delta = (
            replacement["amount"]
            if replacement["kind"] == "credit"
            else -replacement["amount"]
        )

        if orig_account == rep_account:
            final = balances.get(orig_account, 0) + reverse_delta + apply_delta
            if final < 0:
                raise CommandConflict(
                    "replacement of command {0!r} would leave a negative "
                    "balance".format(cid)
                )
            balances[orig_account] = final
        else:
            final_orig = balances.get(orig_account, 0) + reverse_delta
            final_rep = balances.get(rep_account, 0) + apply_delta
            if final_orig < 0 or final_rep < 0:
                raise CommandConflict(
                    "replacement of command {0!r} would leave a negative "
                    "balance".format(cid)
                )
            balances[orig_account] = final_orig
            balances[rep_account] = final_rep

        self._balances = balances
        result = {
            "id": cid,
            "account": rep_account,
            "balance": balances[rep_account],
        }
        self._commands[cid] = dict(replacement)
        self._results[cid] = dict(result)
        return dict(result)