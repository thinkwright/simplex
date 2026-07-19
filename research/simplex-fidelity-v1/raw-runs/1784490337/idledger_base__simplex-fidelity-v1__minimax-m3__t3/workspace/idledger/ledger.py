"""Ledger implementation.

A small, thread-safe ledger that records commands by id for idempotency.
"""

from threading import RLock

from idledger.errors import CommandConflict, InsufficientFunds


_CREDIT = "credit"
_DEBIT = "debit"
_VALID_KINDS = (_CREDIT, _DEBIT)
_REQUIRED_COMMAND_KEYS = frozenset({"id", "account", "kind", "amount"})


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
    if set(command.keys()) != _REQUIRED_COMMAND_KEYS:
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
    """A thread-safe ledger with idempotent command application."""

    def __init__(self, initial=None):
        self._lock = RLock()
        with self._lock:
            self._balances = _validate_initial(initial)
            # command id -> (account, kind, amount, resulting_balance)
            self._history = {}

    def snapshot(self):
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        # Validate outside the lock first; this is cheap and raises ValueError
        # without touching any state.
        cmd_id, account, kind, amount = _validate_command(command)

        with self._lock:
            existing = self._history.get(cmd_id)
            if existing is not None:
                prev_account, prev_kind, prev_amount, prev_balance = existing
                if (
                    prev_account == account
                    and prev_kind == kind
                    and prev_amount == amount
                ):
                    return {
                        "id": cmd_id,
                        "account": prev_account,
                        "balance": prev_balance,
                    }
                raise CommandConflict(
                    f"command id {cmd_id!r} already used with different content"
                )

            current = self._balances.get(account, 0)
            if kind == _DEBIT:
                new_balance = current - amount
                if new_balance < 0:
                    raise InsufficientFunds(
                        f"debit of {amount} from account {account!r} "
                        f"with balance {current} would go negative"
                    )
            else:  # _CREDIT
                new_balance = current + amount

            self._balances[account] = new_balance
            self._history[cmd_id] = (account, kind, amount, new_balance)
            return {"id": cmd_id, "account": account, "balance": new_balance}