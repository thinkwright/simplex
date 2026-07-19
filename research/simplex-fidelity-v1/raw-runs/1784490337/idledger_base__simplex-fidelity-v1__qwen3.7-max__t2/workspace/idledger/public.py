"""idledger public API."""

import threading


class InsufficientFunds(Exception):
    """Raised when a debit would make a balance negative."""
    pass


class CommandConflict(Exception):
    """Raised when a command id is reused with different content."""
    pass


class Ledger:
    """A simple ledger tracking account balances in integer cents."""

    def __init__(self, initial=None):
        self._lock = threading.Lock()
        self._balances = {}
        self._commands = {}  # command_id -> (command_dict, result_dict)

        if initial is not None:
            if not isinstance(initial, dict):
                raise ValueError("initial must be a mapping or None")
            for name, balance in initial.items():
                if not isinstance(name, str):
                    raise ValueError(
                        f"account name must be a string, got {type(name).__name__}"
                    )
                if not isinstance(balance, int) or isinstance(balance, bool):
                    raise ValueError(
                        f"balance must be an integer, got {type(balance).__name__}"
                    )
                if balance < 0:
                    raise ValueError(
                        f"initial balance for '{name}' must be non-negative, got {balance}"
                    )
                self._balances[name] = balance

    def snapshot(self):
        """Return a new dict of balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply a command to the ledger.

        command must be a dict with exactly the keys: id, account, kind, amount.
        kind must be 'credit' or 'debit'.
        amount must be a positive integer.

        Returns a dict with id, account, and resulting balance on success.
        """
        # Validate command structure outside the lock first (but we re-check inside)
        self._validate_command(command)

        cmd_id = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]

        with self._lock:
            # Check for idempotency / conflict
            if cmd_id in self._commands:
                stored_cmd, stored_result = self._commands[cmd_id]
                if self._commands_equal(stored_cmd, command):
                    return dict(stored_result)
                else:
                    raise CommandConflict(
                        f"command id '{cmd_id}' was already used with different content"
                    )

            # Ensure account exists
            if account not in self._balances:
                raise ValueError(f"account '{account}' does not exist")

            current_balance = self._balances[account]

            if kind == "credit":
                new_balance = current_balance + amount
            elif kind == "debit":
                new_balance = current_balance - amount
                if new_balance < 0:
                    raise InsufficientFunds(
                        f"insufficient funds in '{account}': "
                        f"balance {current_balance}, debit {amount}"
                    )
            else:
                # Should not reach here due to validation, but just in case
                raise ValueError(f"invalid kind: '{kind}'")

            # Apply the change
            self._balances[account] = new_balance

            result = {
                "id": cmd_id,
                "account": account,
                "balance": new_balance,
            }

            # Store the command for idempotency
            self._commands[cmd_id] = (dict(command), dict(result))

            return dict(result)

    def _validate_command(self, command):
        """Validate command structure. Raises ValueError on invalid input."""
        if not isinstance(command, dict):
            raise ValueError("command must be a dict")

        required_keys = {"id", "account", "kind", "amount"}
        if set(command.keys()) != required_keys:
            extra = set(command.keys()) - required_keys
            missing = required_keys - set(command.keys())
            parts = []
            if extra:
                parts.append(f"extra keys: {extra}")
            if missing:
                parts.append(f"missing keys: {missing}")
            raise ValueError(f"invalid command structure: {', '.join(parts)}")

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

        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError(
                f"amount must be an integer, got {type(amount).__name__}"
            )

        if amount <= 0:
            raise ValueError(f"amount must be positive, got {amount}")

    @staticmethod
    def _commands_equal(stored, incoming):
        """Check if two commands are identical in content."""
        return (
            stored["id"] == incoming["id"]
            and stored["account"] == incoming["account"]
            and stored["kind"] == incoming["kind"]
            and stored["amount"] == incoming["amount"]
        )
