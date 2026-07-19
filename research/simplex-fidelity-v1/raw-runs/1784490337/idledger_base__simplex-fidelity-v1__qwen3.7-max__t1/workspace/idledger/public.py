"""Public API for the idledger package."""

import threading


class InsufficientFunds(Exception):
    """Raised when a debit would result in a negative balance."""
    pass


class CommandConflict(Exception):
    """Raised when a command id is reused with different content."""
    pass


class Ledger:
    """A thread-safe ledger that tracks account balances and applies commands."""

    def __init__(self, initial=None):
        """Initialize the ledger.

        Args:
            initial: Optional mapping of account names (str) to non-negative
                     integer balances.

        Raises:
            ValueError: If initial state is invalid.
        """
        self._lock = threading.Lock()
        self._balances = {}
        self._successful_commands = {}  # cmd_id -> ((account, kind, amount), result_dict)

        if initial is not None:
            if not hasattr(initial, 'items') or not hasattr(initial, 'keys'):
                raise ValueError("initial must be a mapping or None")
            for name, balance in initial.items():
                if not isinstance(name, str):
                    raise ValueError(
                        f"account name must be a string, got {type(name).__name__}"
                    )
                if isinstance(balance, bool) or not isinstance(balance, int):
                    raise ValueError(
                        f"balance must be an integer, got {type(balance).__name__}"
                    )
                if balance < 0:
                    raise ValueError(
                        f"balance must be non-negative, got {balance}"
                    )
                self._balances[name] = balance

    def snapshot(self):
        """Return a new dict of account balances sorted by account name.

        Returns:
            A dict with account names as keys and balances as values,
            sorted by account name.
        """
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply a command to the ledger.

        Args:
            command: A dict with exactly four keys: id, account, kind, amount.
                     - id: any hashable value identifying the command
                     - account: str, the account name
                     - kind: 'credit' or 'debit'
                     - amount: positive integer

        Returns:
            A dict with keys id, account, and balance (the resulting balance).

        Raises:
            ValueError: If the command structure is invalid or the account
                        does not exist.
            InsufficientFunds: If a debit would make the balance negative.
            CommandConflict: If the command id was already used with different
                             content.
        """
        with self._lock:
            # --- Validate command structure (R7) ---
            if not isinstance(command, dict):
                raise ValueError("command must be a dict")

            expected_keys = {"id", "account", "kind", "amount"}
            if set(command.keys()) != expected_keys:
                raise ValueError(
                    f"command must have exactly keys {sorted(expected_keys)}, "
                    f"got {sorted(command.keys())}"
                )

            cmd_id = command["id"]
            account = command["account"]
            kind = command["kind"]
            amount = command["amount"]

            # Validate id is hashable
            try:
                hash(cmd_id)
            except TypeError:
                raise ValueError("command id must be hashable")

            # Validate account is a string
            if not isinstance(account, str):
                raise ValueError(
                    f"account must be a string, got {type(account).__name__}"
                )

            # Validate kind
            if kind not in ("credit", "debit"):
                raise ValueError(
                    f"kind must be 'credit' or 'debit', got {kind!r}"
                )

            # Validate amount: must be a positive integer, not a bool
            if isinstance(amount, bool) or not isinstance(amount, int):
                raise ValueError(
                    f"amount must be a positive integer, got {type(amount).__name__}"
                )
            if amount <= 0:
                raise ValueError(f"amount must be positive, got {amount}")

            # --- Check for existing command id (R4, R5) ---
            if cmd_id in self._successful_commands:
                stored_content, stored_result = self._successful_commands[cmd_id]
                if stored_content == (account, kind, amount):
                    # R4: identical command, return original result
                    return dict(stored_result)
                else:
                    # R5: same id, different content
                    raise CommandConflict(
                        f"command id {cmd_id!r} was already used with "
                        f"different content"
                    )

            # --- Validate account exists ---
            if account not in self._balances:
                raise ValueError(f"account {account!r} does not exist")

            # --- Apply the command (R3, R6) ---
            current_balance = self._balances[account]

            if kind == "debit":
                if current_balance < amount:
                    # R6: insufficient funds, do not consume command id
                    raise InsufficientFunds(
                        f"insufficient funds in account {account!r}: "
                        f"balance is {current_balance}, debit amount is {amount}"
                    )
                new_balance = current_balance - amount
            else:
                # credit
                new_balance = current_balance + amount

            self._balances[account] = new_balance

            result = {"id": cmd_id, "account": account, "balance": new_balance}
            self._successful_commands[cmd_id] = (
                (account, kind, amount),
                dict(result),
            )

            return dict(result)
