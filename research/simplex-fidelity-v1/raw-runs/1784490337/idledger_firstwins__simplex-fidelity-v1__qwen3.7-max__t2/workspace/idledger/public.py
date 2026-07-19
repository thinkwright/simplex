"""idledger public API – Ledger, InsufficientFunds, CommandConflict."""

import threading
from collections.abc import Mapping


class InsufficientFunds(Exception):
    """Raised when a debit would result in a negative balance."""


class CommandConflict(Exception):
    """Raised when a command-id conflict is detected."""


class Ledger:
    """A simple in-memory ledger with idempotent command application."""

    def __init__(self, initial=None):
        if initial is None:
            self._balances: dict[str, int] = {}
        elif isinstance(initial, Mapping):
            for key, val in initial.items():
                if not isinstance(key, str):
                    raise ValueError(
                        f"account name must be a string, got {type(key).__name__}"
                    )
                if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                    raise ValueError(
                        f"balance for '{key}' must be a non-negative integer, "
                        f"got {val!r}"
                    )
            self._balances = dict(initial)
        else:
            raise ValueError(
                f"initial must be a mapping or None, got {type(initial).__name__}"
            )
        self._commands: dict = {}          # cmd_id -> result dict
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        """Return a name-sorted copy of the current balances."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    # ------------------------------------------------------------------
    def apply(self, command) -> dict:
        """Apply *command* to the ledger and return the result.

        *command* must be a dict with exactly the keys
        ``id``, ``account``, ``kind`` (``"credit"`` | ``"debit"``),
        and ``amount`` (positive int).
        """
        with self._lock:
            # --- basic type check ----------------------------------------
            if not isinstance(command, dict):
                raise ValueError("command must be a dict")

            # --- idempotency / first-wins check --------------------------
            if "id" in command:
                cmd_id = command["id"]
                try:
                    cached = self._commands.get(cmd_id)
                except TypeError:
                    raise ValueError("command id must be hashable")
                if cached is not None:
                    return cached

            # --- structural validation -----------------------------------
            expected_keys = {"id", "account", "kind", "amount"}
            if set(command.keys()) != expected_keys:
                raise ValueError(
                    "command must have exactly the keys: "
                    "id, account, kind, amount"
                )

            cmd_id = command["id"]
            account = command["account"]
            kind = command["kind"]
            amount = command["amount"]

            if not isinstance(account, str):
                raise ValueError(
                    f"account must be a string, got {type(account).__name__}"
                )
            if kind not in ("credit", "debit"):
                raise ValueError(
                    f"kind must be 'credit' or 'debit', got {kind!r}"
                )
            if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                raise ValueError(
                    f"amount must be a positive integer, got {amount!r}"
                )
            if account not in self._balances:
                raise ValueError(f"account '{account}' does not exist")

            # --- apply ---------------------------------------------------
            current = self._balances[account]

            if kind == "debit":
                if current < amount:
                    raise InsufficientFunds(
                        f"insufficient funds in '{account}': "
                        f"balance {current}, debit {amount}"
                    )
                new_balance = current - amount
            else:  # credit
                new_balance = current + amount

            self._balances[account] = new_balance
            result = {"id": cmd_id, "account": account, "balance": new_balance}
            self._commands[cmd_id] = result
            return result
