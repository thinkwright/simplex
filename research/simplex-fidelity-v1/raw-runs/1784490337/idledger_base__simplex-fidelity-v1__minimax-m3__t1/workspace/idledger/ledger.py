"""Ledger implementation.

A thread-safe, append-only ledger of integer-cents credit/debit commands.
Only the Python standard library is used.
"""

from __future__ import annotations

import threading
from typing import Any, Mapping


class InsufficientFunds(Exception):
    """Raised when a debit would cause a negative balance."""


class CommandConflict(Exception):
    """Raised when a command id is reused with different content."""


_VALID_KINDS = ("credit", "debit")
_REQUIRED_COMMAND_KEYS = ("id", "account", "kind", "amount")


def _validate_initial(initial: Mapping[str, Any]) -> dict:
    if not isinstance(initial, Mapping):
        raise ValueError("initial must be a mapping of account names to balances")
    result: dict = {}
    for account, balance in initial.items():
        if not isinstance(account, str) or not account:
            raise ValueError("account names must be non-empty strings")
        if isinstance(balance, bool) or not isinstance(balance, int):
            raise ValueError(
                f"balance for {account!r} must be an integer (got {type(balance).__name__})"
            )
        if balance < 0:
            raise ValueError(
                f"balance for {account!r} must be non-negative (got {balance})"
            )
        result[account] = int(balance)
    return result


def _validate_command(command: Any) -> tuple:
    if not isinstance(command, Mapping):
        raise ValueError("command must be a mapping")
    keys = set(command.keys())
    required = set(_REQUIRED_COMMAND_KEYS)
    if keys != required:
        extra = keys - required
        missing = required - keys
        parts = []
        if missing:
            parts.append(f"missing keys {sorted(missing)}")
        if extra:
            parts.append(f"unexpected keys {sorted(extra)}")
        raise ValueError("command must contain exactly " +
                         ", ".join(_REQUIRED_COMMAND_KEYS) + "; " + ", ".join(parts))

    cid = command["id"]
    account = command["account"]
    kind = command["kind"]
    amount = command["amount"]

    if not isinstance(cid, str) or not cid:
        raise ValueError("command id must be a non-empty string")
    if not isinstance(account, str) or not account:
        raise ValueError("command account must be a non-empty string")
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"command kind must be one of {_VALID_KINDS} (got {kind!r})"
        )
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError(
            f"command amount must be an integer (got {type(amount).__name__})"
        )
    if amount <= 0:
        raise ValueError(f"command amount must be a positive integer (got {amount})")

    return cid, account, kind, int(amount)


class Ledger:
    """A thread-safe ledger of credit/debit commands keyed by command id."""

    def __init__(self, initial: Mapping[str, int] | None = None) -> None:
        self._lock = threading.Lock()
        self._balances: dict = _validate_initial(initial if initial is not None else {})
        self._history: dict = {}  # cid -> (command_dict, result_dict)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command: Mapping[str, Any]) -> dict:
        cid, account, kind, amount = _validate_command(command)

        with self._lock:
            if cid in self._history:
                stored_command, stored_result = self._history[cid]
                # Compare command content (values only).
                if (
                    stored_command["account"] == account
                    and stored_command["kind"] == kind
                    and stored_command["amount"] == amount
                ):
                    # Idempotent replay: return the original result.
                    return {
                        "id": stored_result["id"],
                        "account": stored_result["account"],
                        "balance": stored_result["balance"],
                    }
                raise CommandConflict(
                    f"command id {cid!r} already used with different content"
                )

            if account not in self._balances:
                raise ValueError(f"unknown account {account!r}")

            current = self._balances[account]
            if kind == "debit":
                new_balance = current - amount
                if new_balance < 0:
                    raise InsufficientFunds(
                        f"debit of {amount} from account {account!r} "
                        f"with balance {current} would go negative"
                    )
            else:  # credit
                new_balance = current + amount

            self._balances[account] = new_balance
            result = {"id": cid, "account": account, "balance": new_balance}
            # Store a frozen view of the command for future comparison.
            self._history[cid] = (
                {"account": account, "kind": kind, "amount": amount},
                result,
            )
            return {"id": result["id"], "account": result["account"], "balance": result["balance"]}