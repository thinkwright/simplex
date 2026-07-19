"""Ledger implementation.

A small ledger that supports idempotent command application with
thread-safe semantics. Only the Python standard library is used.
"""

from __future__ import annotations

import threading
from typing import Any, Mapping


class InsufficientFunds(Exception):
    """Raised when a debit would cause a negative balance."""


class CommandConflict(Exception):
    """Reserved for future use; not raised in current implementation."""


_VALID_KINDS = ("credit", "debit")
_REQUIRED_COMMAND_KEYS = ("id", "account", "kind", "amount")


class Ledger:
    """A ledger of integer-cent balances keyed by account name.

    Parameters
    ----------
    initial:
        Optional mapping of account name to non-negative integer balance.
    """

    def __init__(self, initial: Mapping[str, int] | None = None) -> None:
        self._balances: dict[str, int] = {}
        self._history: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        if initial is not None:
            self._set_initial(initial)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    def _set_initial(self, initial: Mapping[str, int]) -> None:
        if not isinstance(initial, Mapping):
            raise ValueError("initial must be a mapping of account names to balances")
        for account, balance in initial.items():
            if not isinstance(account, str):
                raise ValueError("account names must be strings")
            if not isinstance(balance, int) or isinstance(balance, bool):
                raise ValueError("balances must be integers")
            if balance < 0:
                raise ValueError("balances must be non-negative")
            self._balances[account] = balance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def snapshot(self) -> dict[str, int]:
        """Return a new dict of balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command: Mapping[str, Any]) -> dict[str, Any]:
        """Apply a command and return ``{id, account, balance}``.

        Raises
        ------
        ValueError
            If the command structure is invalid.
        InsufficientFunds
            If a debit would cause a negative balance.
        """
        # Validate command structure outside the lock so we don't hold it
        # while raising. We re-check history under the lock for idempotency.
        self._validate_command(command)

        cmd_id = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]

        with self._lock:
            # Idempotency: if we've seen this id before, return the original
            # result. If the content differs, R5 says we still return the
            # original result and leave balances unchanged.
            if cmd_id in self._history:
                stored = self._history[cmd_id]
                return {
                    "id": stored["id"],
                    "account": stored["account"],
                    "balance": stored["balance"],
                }

            current = self._balances.get(account, 0)
            if kind == "credit":
                new_balance = current + amount
            else:  # debit
                new_balance = current - amount
                if new_balance < 0:
                    # R6: do not consume the command id, leave state unchanged.
                    raise InsufficientFunds(
                        f"debit of {amount} from account {account!r} "
                        f"would leave balance {new_balance}"
                    )

            self._balances[account] = new_balance
            result = {"id": cmd_id, "account": account, "balance": new_balance}
            self._history[cmd_id] = result
            return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_command(self, command: Any) -> None:
        if not isinstance(command, Mapping):
            raise ValueError("command must be a mapping")
        keys = set(command.keys())
        required = set(_REQUIRED_COMMAND_KEYS)
        if keys != required:
            raise ValueError(
                f"command must contain exactly {sorted(required)} keys, "
                f"got {sorted(keys)}"
            )

        cmd_id = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]

        if not isinstance(cmd_id, str) or not cmd_id:
            raise ValueError("command id must be a non-empty string")
        if not isinstance(account, str) or not account:
            raise ValueError("command account must be a non-empty string")
        if kind not in _VALID_KINDS:
            raise ValueError(f"command kind must be one of {_VALID_KINDS}")
        if (
            not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount <= 0
        ):
            raise ValueError("command amount must be a positive integer")