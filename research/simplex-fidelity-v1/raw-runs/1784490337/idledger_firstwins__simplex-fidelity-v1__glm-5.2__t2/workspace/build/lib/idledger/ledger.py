"""Idempotent, thread-safe ledger of integer-cent account balances."""

import threading
from collections.abc import Mapping

from .errors import InsufficientFunds

__all__ = ["Ledger"]

_VALID_KINDS = ("credit", "debit")
_REQUIRED_KEYS = frozenset({"id", "account", "kind", "amount"})


class Ledger:
    """An idempotent, thread-safe ledger of integer-cent account balances.

    Balances are stored as integer cents.  Every successful command is recorded
    by its command id so that repeating or reusing an id returns the original
    result without re-applying the command.
    """

    def __init__(self, initial=None):
        self._lock = threading.Lock()
        # Validate up front so a bad initial state raises before any attribute
        # beyond the lock is established.
        self._balances = self._validate_initial(initial)
        self._history = {}

    # ------------------------------------------------------------------ #
    # validation helpers (pure: never touch instance state)              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_initial(initial):
        if initial is None:
            return {}
        if not isinstance(initial, Mapping):
            raise ValueError("initial balances must be a mapping or None")
        balances = {}
        for name, value in initial.items():
            if not isinstance(name, str):
                raise ValueError(
                    f"account name must be a string, got {type(name).__name__}"
                )
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(
                    f"balance for account {name!r} must be an integer, "
                    f"got {type(value).__name__}"
                )
            if value < 0:
                raise ValueError(
                    f"balance for account {name!r} must be non-negative, "
                    f"got {value}"
                )
            balances[name] = value
        return balances

    @staticmethod
    def _validate_command(command):
        if not isinstance(command, Mapping):
            raise ValueError("command must be a mapping")
        if set(command.keys()) != _REQUIRED_KEYS:
            raise ValueError(
                "command must have exactly the keys "
                f"{sorted(_REQUIRED_KEYS)}, got {sorted(command.keys())}"
            )
        cmd_id = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]
        if not isinstance(cmd_id, str):
            raise ValueError(
                f"command id must be a string, got {type(cmd_id).__name__}"
            )
        if not isinstance(account, str):
            raise ValueError(
                f"command account must be a string, got {type(account).__name__}"
            )
        if kind not in _VALID_KINDS:
            raise ValueError(
                f"command kind must be 'credit' or 'debit', got {kind!r}"
            )
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError(
                f"command amount must be an integer, got {type(amount).__name__}"
            )
        if amount <= 0:
            raise ValueError(
                f"command amount must be a positive integer, got {amount}"
            )
        return cmd_id, account, kind, amount

    # ------------------------------------------------------------------ #
    # public API                                                          #
    # ------------------------------------------------------------------ #

    def snapshot(self):
        """Return a new dict of balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply an idempotent credit/debit command and return the result.

        The command must be a mapping with exactly the keys ``id``,
        ``account``, ``kind`` and ``amount`` where ``kind`` is ``"credit"`` or
        ``"debit"`` and ``amount`` is a positive integer.  A successful apply
        returns a mapping with exactly ``id``, ``account`` and ``balance``.
        """
        cmd_id, account, kind, amount = self._validate_command(command)
        with self._lock:
            # Repeating or reusing a successful command id returns the
            # original result without re-applying (first successful command
            # wins).  Validation already happened above, so state is untouched.
            if cmd_id in self._history:
                return dict(self._history[cmd_id])
            current = self._balances.get(account, 0)
            if kind == "debit":
                if current - amount < 0:
                    raise InsufficientFunds(
                        f"debit of {amount} from account {account!r} with "
                        f"balance {current} would leave a negative balance"
                    )
                new_balance = current - amount
            else:  # credit
                new_balance = current + amount
            self._balances[account] = new_balance
            result = {"id": cmd_id, "account": account, "balance": new_balance}
            self._history[cmd_id] = dict(result)
            return dict(result)