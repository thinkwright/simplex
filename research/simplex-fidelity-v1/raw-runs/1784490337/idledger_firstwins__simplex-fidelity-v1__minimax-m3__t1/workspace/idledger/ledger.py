"""Ledger implementation.

A thread-safe ledger that supports idempotent command application.
"""

from threading import RLock


class InsufficientFunds(Exception):
    """Raised when a debit would cause a negative balance."""


class CommandConflict(Exception):
    """Raised when a command id is reused with different content."""


_VALID_KINDS = ("credit", "debit")
_REQUIRED_COMMAND_KEYS = ("id", "account", "kind", "amount")


def _validate_initial(initial):
    if initial is None:
        return {}
    if not isinstance(initial, dict):
        raise ValueError("initial must be a mapping or None")
    balances = {}
    for account, balance in initial.items():
        if not isinstance(account, str):
            raise ValueError("account names must be strings")
        if isinstance(balance, bool) or not isinstance(balance, int):
            raise ValueError("balances must be integers")
        if balance < 0:
            raise ValueError("balances must be non-negative")
        balances[account] = balance
    return balances


def _validate_command(command):
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping")
    if set(command.keys()) != set(_REQUIRED_COMMAND_KEYS):
        raise ValueError(
            "command must contain exactly id, account, kind, and amount"
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
        raise ValueError("command kind must be 'credit' or 'debit'")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("command amount must be an integer")
    if amount <= 0:
        raise ValueError("command amount must be a positive integer")

    return cmd_id, account, kind, amount


class Ledger:
    """A ledger with idempotent command application.

    Commands are identified by an id; repeating an identical successful
    command returns the original result without re-applying it.
    """

    def __init__(self, initial=None):
        self._lock = RLock()
        self._balances = _validate_initial(initial)
        self._history = {}  # cmd_id -> (account, kind, amount, resulting_balance)

    def snapshot(self):
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        cmd_id, account, kind, amount = _validate_command(command)

        with self._lock:
            existing = self._history.get(cmd_id)
            if existing is not None:
                orig_account, orig_kind, orig_amount, orig_balance = existing
                if (
                    orig_account == account
                    and orig_kind == kind
                    and orig_amount == amount
                ):
                    return {"id": cmd_id, "account": orig_account, "balance": orig_balance}
                # Reused id with different content: first successful command wins.
                return {"id": cmd_id, "account": orig_account, "balance": orig_balance}

            current = self._balances.get(account, 0)
            if kind == "debit":
                if current - amount < 0:
                    raise InsufficientFunds(
                        f"debit of {amount} from account {account!r} "
                        f"with balance {current} would go negative"
                    )
                new_balance = current - amount
            else:
                new_balance = current + amount

            self._balances[account] = new_balance
            self._history[cmd_id] = (account, kind, amount, new_balance)
            return {"id": cmd_id, "account": account, "balance": new_balance}