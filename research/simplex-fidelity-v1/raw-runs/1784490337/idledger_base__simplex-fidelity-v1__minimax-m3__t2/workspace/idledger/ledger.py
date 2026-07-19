"""Ledger implementation.

A small ledger that supports idempotent command application with thread safety.
Uses only the Python standard library.
"""

from __future__ import annotations

import threading
from typing import Any, Mapping


class InsufficientFunds(Exception):
    """Raised when a debit would cause a negative balance."""


class CommandConflict(Exception):
    """Raised when a command id is reused with different content."""


_VALID_KINDS = ("credit", "debit")


def _validate_initial(initial: Mapping[str, Any]) -> dict:
    if not isinstance(initial, Mapping):
        raise ValueError("initial state must be a mapping")
    result: dict = {}
    for key, value in initial.items():
        if not isinstance(key, str):
            raise ValueError("account names must be strings")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("balances must be integers")
        if value < 0:
            raise ValueError("balances must be non-negative")
        result[key] = value
    return result


def _validate_command(command: Mapping[str, Any]) -> tuple:
    if not isinstance(command, Mapping):
        raise ValueError("command must be a mapping")
    keys = set(command.keys())
    required = {"id", "account", "kind", "amount"}
    if keys != required:
        raise ValueError(
            "command must contain exactly id, account, kind, and amount"
        )
    cid = command["id"]
    account = command["account"]
    kind = command["kind"]
    amount = command["amount"]

    if not isinstance(cid, str) or not cid:
        raise ValueError("command id must be a non-empty string")
    if not isinstance(account, str) or not account:
        raise ValueError("command account must be a non-empty string")
    if kind not in _VALID_KINDS:
        raise ValueError("command kind must be 'credit' or 'debit'")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("command amount must be an integer")
    if amount <= 0:
        raise ValueError("command amount must be a positive integer")
    return cid, account, kind, amount


class Ledger:
    """A ledger supporting idempotent command application."""

    def __init__(self, initial: Mapping[str, Any] | None = None) -> None:
        self._lock = threading.Lock()
        # Validate initial state before mutating anything.
        validated = _validate_initial(initial if initial is not None else {})
        self._balances: dict = dict(validated)
        # command id -> (account, kind, amount, result_balance)
        self._history: dict = {}

    def snapshot(self) -> dict:
        """Return a new account-name-sorted dict of balances."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command: Mapping[str, Any]) -> dict:
        """Apply a command idempotently.

        Returns a dict with exactly id, account, and balance.
        """
        # Validate the command first; on failure, leave all state unchanged.
        cid, account, kind, amount = _validate_command(command)

        with self._lock:
            # Idempotency: if we've seen this id before, return the original
            # result only if the command content matches.
            prior = self._history.get(cid)
            if prior is not None:
                prior_account, prior_kind, prior_amount, prior_balance = prior
                if (
                    prior_account != account
                    or prior_kind != kind
                    or prior_amount != amount
                ):
                    raise CommandConflict(
                        f"command id {cid!r} reused with different content"
                    )
                return {
                    "id": cid,
                    "account": prior_account,
                    "balance": prior_balance,
                }

            current = self._balances.get(account, 0)
            if kind == "debit":
                new_balance = current - amount
                if new_balance < 0:
                    # Do not consume the command id; leave state unchanged.
                    raise InsufficientFunds(
                        f"insufficient funds in account {account!r}"
                    )
            else:  # credit
                new_balance = current + amount

            self._balances[account] = new_balance
            self._history[cid] = (account, kind, amount, new_balance)
            return {"id": cid, "account": account, "balance": new_balance}