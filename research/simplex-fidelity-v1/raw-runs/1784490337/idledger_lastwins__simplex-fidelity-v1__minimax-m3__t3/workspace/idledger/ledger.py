"""Core Ledger implementation for idledger.

The Ledger applies idempotent commands to account balances. Each command is
identified by an ``id``; repeating an identical successful command returns the
original result without re-applying it. A conflicting command with the same id
is resolved by atomically reversing the original and applying the replacement.
"""

from __future__ import annotations

import threading
from typing import Any, Mapping, Optional

from idledger.errors import InsufficientFunds, CommandConflict

_VALID_KINDS = ("credit", "debit")
_REQUIRED_COMMAND_KEYS = ("id", "account", "kind", "amount")


def _validate_initial(initial: Any) -> dict:
    """Validate and copy an initial balances mapping.

    Returns a new dict mapping account names to non-negative integer cents.
    Raises ``ValueError`` for any structural problem.
    """
    if initial is None:
        return {}
    if not isinstance(initial, Mapping):
        raise ValueError("initial must be a mapping of account names to balances")
    result: dict = {}
    for account, balance in initial.items():
        if not isinstance(account, str):
            raise ValueError("account names must be strings")
        if isinstance(balance, bool) or not isinstance(balance, int):
            raise ValueError("balances must be integers")
        if balance < 0:
            raise ValueError("balances must be non-negative")
        result[account] = balance
    return result


def _validate_command(command: Any) -> tuple:
    """Validate a command mapping.

    Returns ``(cmd_id, account, kind, amount)`` on success. Raises
    ``ValueError`` for any structural problem.
    """
    if not isinstance(command, Mapping):
        raise ValueError("command must be a mapping")
    # Reject extra keys: command must contain exactly the required keys.
    if tuple(command.keys()) != _REQUIRED_COMMAND_KEYS:
        raise ValueError(
            "command must contain exactly the keys: id, account, kind, amount"
        )
    cmd_id = command["id"]
    account = command["account"]
    kind = command["kind"]
    amount = command["amount"]

    if not isinstance(cmd_id, str):
        raise ValueError("command id must be a string")
    if not isinstance(account, str):
        raise ValueError("command account must be a string")
    if not isinstance(kind, str):
        raise ValueError("command kind must be a string")
    if kind not in _VALID_KINDS:
        raise ValueError("command kind must be 'credit' or 'debit'")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("command amount must be an integer")
    if amount <= 0:
        raise ValueError("command amount must be a positive integer")
    return cmd_id, account, kind, amount


class Ledger:
    """A ledger of integer-cents account balances with idempotent commands."""

    def __init__(self, initial: Optional[Mapping[str, int]] = None) -> None:
        # Validate the initial state up front so a bad mapping never leaves a
        # partially constructed ledger.
        balances = _validate_initial(initial)
        self._balances: dict = balances
        # History of successfully applied commands: id -> (command, result).
        self._history: dict = {}
        self._lock = threading.Lock()

    def snapshot(self) -> dict:
        """Return a new dict of account-name-sorted balances."""
        with self._lock:
            # Sorting by account name gives a deterministic, sorted snapshot.
            return dict(sorted(self._balances.items()))

    def apply(self, command: Mapping[str, Any]) -> dict:
        """Apply a command and return ``{id, account, balance}``.

        Behaviour:
            * Repeating an identical successful command returns the original
              result without re-applying.
            * A conflicting command with the same id atomically reverses the
              original and applies the replacement; if the replacement fails
              the original is preserved and ``CommandConflict`` is raised.
            * A debit that would make a balance negative raises
              ``InsufficientFunds`` and leaves all state unchanged; the
              command id is not consumed.
            * Invalid commands raise ``ValueError`` and leave all state and
              history unchanged.
        """
        # Validate the command before acquiring the lock so that bad input
        # never touches mutable state.
        cmd_id, account, kind, amount = _validate_command(command)

        with self._lock:
            # Idempotent replay: identical successful command returns the
            # original result without re-applying.
            if cmd_id in self._history:
                original_cmd, original_result = self._history[cmd_id]
                if _commands_equal(original_cmd, command):
                    return {
                        "id": original_result["id"],
                        "account": original_result["account"],
                        "balance": original_result["balance"],
                    }
                # Conflict: try to atomically replace.
                return self._replace_conflicting(cmd_id, command, account, kind, amount)

            # Fresh command: apply it.
            return self._apply_new(cmd_id, account, kind, amount)

    # ------------------------------------------------------------------
    # Internal helpers (must be called with self._lock held).
    # ------------------------------------------------------------------

    def _apply_new(self, cmd_id: str, account: str, kind: str, amount: int) -> dict:
        """Apply a brand-new command and record it in history."""
        balance = self._balances.get(account, 0)
        if kind == "debit":
            if balance - amount < 0:
                # Do not consume the command id; leave history untouched.
                raise InsufficientFunds(
                    "debit of {} from account {!r} would leave a negative balance".format(
                        amount, account
                    )
                )
            new_balance = balance - amount
        else:  # credit
            new_balance = balance + amount

        self._balances[account] = new_balance
        result = {"id": cmd_id, "account": account, "balance": new_balance}
        # Store a copy of the command so future replays compare structurally.
        self._history[cmd_id] = (
            {"id": cmd_id, "account": account, "kind": kind, "amount": amount},
            result,
        )
        return {"id": result["id"], "account": result["account"], "balance": result["balance"]}

    def _replace_conflicting(
        self,
        cmd_id: str,
        new_command: Mapping[str, Any],
        account: str,
        kind: str,
        amount: int,
    ) -> dict:
        """Atomically replace a previously applied command.

        Reverses the original command, then applies the replacement. If the
        replacement itself fails (e.g. overdraw), the reversal is undone and
        ``CommandConflict`` is raised; the original command and its result
        remain in history.
        """
        original_cmd, _original_result = self._history[cmd_id]
        orig_account = original_cmd["account"]
        orig_kind = original_cmd["kind"]
        orig_amount = original_cmd["amount"]

        # Reverse the original on a temporary copy of balances so we can
        # roll back if the replacement fails.
        working = dict(self._balances)
        if orig_kind == "credit":
            working[orig_account] = working.get(orig_account, 0) - orig_amount
        else:  # debit
            working[orig_account] = working.get(orig_account, 0) + orig_amount

        # Attempt the replacement against the working copy.
        balance = working.get(account, 0)
        if kind == "debit":
            if balance - amount < 0:
                raise CommandConflict(
                    "replacement command {!r} would overdraw account {!r}".format(
                        cmd_id, account
                    )
                )
            new_balance = balance - amount
        else:  # credit
            new_balance = balance + amount
        working[account] = new_balance

        # Commit: replace balances and history entry atomically.
        self._balances = working
        result = {"id": cmd_id, "account": account, "balance": new_balance}
        self._history[cmd_id] = (
            {"id": cmd_id, "account": account, "kind": kind, "amount": amount},
            result,
        )
        return {"id": result["id"], "account": result["account"], "balance": result["balance"]}


def _commands_equal(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Return True if two commands are structurally identical."""
    return (
        a["id"] == b["id"]
        and a["account"] == b["account"]
        and a["kind"] == b["kind"]
        and a["amount"] == b["amount"]
    )