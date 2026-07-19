import threading
from ._errors import InsufficientFunds, CommandConflict


class Ledger:
    """Thread-safe ledger with idempotent command application."""

    def __init__(self, initial=None):
        if initial is None:
            self._balances = {}
        elif isinstance(initial, dict):
            for key, val in initial.items():
                if not isinstance(key, str):
                    raise ValueError(
                        f"account name must be a string, got {type(key).__name__}"
                    )
                if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                    raise ValueError(
                        f"balance for {key!r} must be a non-negative integer, got {val!r}"
                    )
            self._balances = dict(initial)
        else:
            raise ValueError(
                f"initial must be a dict or None, got {type(initial).__name__}"
            )
        self._commands = {}  # cmd_id -> result dict
        self._lock = threading.Lock()

    def snapshot(self):
        """Return a new dict of balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply a credit or debit command to the ledger.

        Returns a result dict with id, account, and balance on success.
        Raises InsufficientFunds if a debit would make balance negative.
        Raises ValueError for invalid command structure.
        """
        with self._lock:
            # --- validate command structure (before any state change) ---
            if not isinstance(command, dict):
                raise ValueError("command must be a dict")

            if set(command.keys()) != {"id", "account", "kind", "amount"}:
                raise ValueError(
                    "command must have exactly the keys: id, account, kind, amount"
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
                raise ValueError(f"account {account!r} does not exist")

            # --- idempotency: if cmd_id was already successful, return cached ---
            if cmd_id in self._commands:
                return dict(self._commands[cmd_id])

            # --- apply the operation ---
            current = self._balances[account]

            if kind == "debit":
                if current < amount:
                    raise InsufficientFunds(
                        f"insufficient funds in {account!r}: "
                        f"balance {current}, debit {amount}"
                    )
                new_balance = current - amount
            else:  # credit
                new_balance = current + amount

            self._balances[account] = new_balance

            result = {"id": cmd_id, "account": account, "balance": new_balance}
            self._commands[cmd_id] = result

            return dict(result)
