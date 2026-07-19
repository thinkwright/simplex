"""Public API for the idledger package."""

import threading


class InsufficientFunds(Exception):
    """Raised when a debit would result in a negative balance."""
    pass


class CommandConflict(Exception):
    """Raised when a command id is reused with different content."""
    pass


def _is_strict_int(value):
    """Return True if *value* is an int but not a bool."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_initial(initial):
    """Validate the *initial* mapping and return a plain-dict copy."""
    if initial is None:
        return {}
    if not hasattr(initial, "keys") or not hasattr(initial, "__getitem__"):
        raise ValueError("initial must be a mapping or None")
    result = {}
    for name, balance in initial.items():
        if not isinstance(name, str):
            raise ValueError(
                f"account name must be a string, got {type(name).__name__}"
            )
        if not _is_strict_int(balance):
            raise ValueError(
                f"balance must be an integer, got {type(balance).__name__}"
            )
        if balance < 0:
            raise ValueError(f"balance must be non-negative, got {balance}")
        result[name] = balance
    return result


def _validate_command(command):
    """Validate a command mapping.

    Returns (cmd_id, account, kind, amount) on success.
    Raises ValueError on any structural problem.
    """
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping")

    required_keys = {"id", "account", "kind", "amount"}
    command_keys = set(command.keys())

    if command_keys != required_keys:
        missing = required_keys - command_keys
        extra = command_keys - required_keys
        parts = []
        if missing:
            parts.append(f"missing keys: {missing}")
        if extra:
            parts.append(f"extra keys: {extra}")
        raise ValueError(f"invalid command structure: {', '.join(parts)}")

    cmd_id = command["id"]
    account = command["account"]
    kind = command["kind"]
    amount = command["amount"]

    # id must be hashable so it can serve as a dict key
    try:
        hash(cmd_id)
    except TypeError:
        raise ValueError(f"command id must be hashable, got {type(cmd_id).__name__}")

    if not isinstance(account, str):
        raise ValueError(
            f"account must be a string, got {type(account).__name__}"
        )

    if kind not in ("credit", "debit"):
        raise ValueError(f"kind must be 'credit' or 'debit', got {kind!r}")

    if not _is_strict_int(amount):
        raise ValueError(
            f"amount must be a positive integer, got {type(amount).__name__}"
        )

    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount}")

    return cmd_id, account, kind, amount


class Ledger:
    """A simple in-memory ledger with idempotent, thread-safe commands."""

    def __init__(self, initial=None):
        self._balances = _validate_initial(initial)
        # cmd_id -> (command_tuple, result_dict)
        self._successful_commands = {}
        self._lock = threading.Lock()

    def snapshot(self):
        """Return a new dict of balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply a credit or debit command and return the result.

        Raises:
            ValueError:        if the command structure is invalid
            CommandConflict:   if the command id was already used with
                               different content
            InsufficientFunds: if a debit would make the balance negative
        """
        # Validate purely on input — no state touched, so ValueError is
        # guaranteed to leave everything unchanged.
        cmd_id, account, kind, amount = _validate_command(command)

        # A hashable tuple capturing the full command content for comparison.
        command_content = (command["id"], command["account"],
                           command["kind"], command["amount"])

        with self._lock:
            # Idempotency / conflict check
            if cmd_id in self._successful_commands:
                stored_content, stored_result = self._successful_commands[cmd_id]
                if stored_content == command_content:
                    # R4 — identical replay
                    return dict(stored_result)
                else:
                    # R5 — conflict
                    raise CommandConflict(
                        f"command id {cmd_id!r} already used with "
                        f"different content"
                    )

            # Implicitly create accounts with zero balance on first touch.
            if account not in self._balances:
                self._balances[account] = 0

            current_balance = self._balances[account]

            if kind == "debit":
                if current_balance < amount:
                    # R6 — do NOT record the command id; it stays reusable
                    raise InsufficientFunds(
                        f"insufficient funds in {account!r}: "
                        f"balance {current_balance}, debit {amount}"
                    )
                new_balance = current_balance - amount
            else:  # credit
                new_balance = current_balance + amount

            self._balances[account] = new_balance

            result = {
                "id": cmd_id,
                "account": account,
                "balance": new_balance,
            }

            # Record for idempotency
            self._successful_commands[cmd_id] = (command_content, dict(result))

            return dict(result)
