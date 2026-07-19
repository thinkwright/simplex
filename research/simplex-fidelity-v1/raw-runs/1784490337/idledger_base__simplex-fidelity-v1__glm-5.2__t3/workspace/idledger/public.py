"""Idempotent, thread-safe ledger of integer-cent account balances.

Only the Python standard library is used (``threading``), satisfying the
"standard library only" constraint.
"""

import threading

__all__ = ["Ledger", "InsufficientFunds", "CommandConflict"]

# The exact set of fields a command must carry -- no more, no less.
_REQUIRED_KEYS = frozenset({"id", "account", "kind", "amount"})


def _is_int(value):
    """Return True only for genuine integers (``bool`` is rejected)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_hashable(value):
    """Return True when ``value`` can be used as a dictionary key."""
    try:
        hash(value)
        return True
    except TypeError:
        return False


class InsufficientFunds(Exception):
    """Raised when a debit would leave a negative balance."""


class CommandConflict(Exception):
    """Raised when a successful command id is reused with different content."""


class Ledger:
    """An idempotent, thread-safe ledger of integer-cent balances.

    Balances and command amounts are integer cents.  No successful operation
    ever leaves a negative balance.
    """

    def __init__(self, initial=None):
        self._lock = threading.Lock()
        self._balances = {}
        # command id -> (command dict, result dict) for every successful apply.
        self._history = {}
        if initial is not None:
            self._balances = self._build_initial(initial)

    # -- construction -----------------------------------------------------

    @staticmethod
    def _build_initial(initial):
        if not isinstance(initial, dict):
            raise ValueError("initial balances must be a mapping")
        balances = {}
        for account, balance in initial.items():
            if not _is_hashable(account):
                raise ValueError("account names must be hashable")
            if not _is_int(balance) or balance < 0:
                raise ValueError("initial balances must be non-negative integers")
            balances[account] = balance
        return balances

    # -- inspection -------------------------------------------------------

    def snapshot(self):
        """Return a new account-name-sorted dict of the current balances."""
        with self._lock:
            return {account: self._balances[account]
                    for account in sorted(self._balances)}

    # -- mutation ---------------------------------------------------------

    def apply(self, command):
        """Apply a credit/debit command idempotently and atomically.

        ``command`` must be a mapping with exactly the keys ``id``, ``account``,
        ``kind`` and ``amount``; ``kind`` is ``"credit"`` or ``"debit"`` and
        ``amount`` is a positive integer.  On success a new dict with exactly
        ``id``, ``account`` and ``balance`` is returned.
        """
        # Validate structure first: this never mutates state and never
        # consumes a command id, so a ValueError leaves everything unchanged.
        self._validate_command(command)

        cmd_id = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]

        with self._lock:
            # Idempotency / conflict handling for a previously used id.
            if cmd_id in self._history:
                stored_command, stored_result = self._history[cmd_id]
                if stored_command == command:
                    # Identical repeat: return the original result, no re-apply.
                    return dict(stored_result)
                raise CommandConflict(
                    "command id %r was already used with different content"
                    % (cmd_id,)
                )

            current = self._balances.get(account, 0)
            if kind == "credit":
                new_balance = current + amount
            else:  # debit
                new_balance = current - amount
                if new_balance < 0:
                    # Atomic failure: no balance change, id not consumed.
                    raise InsufficientFunds(
                        "debit of %d from %r with balance %d would overdraw"
                        % (amount, account, current)
                    )

            # Commit both the balance and the history entry together.
            self._balances[account] = new_balance
            result = {"id": cmd_id, "account": account, "balance": new_balance}
            self._history[cmd_id] = (dict(command), result)
            return dict(result)

    @staticmethod
    def _validate_command(command):
        if not isinstance(command, dict):
            raise ValueError("command must be a mapping")
        if set(command.keys()) != _REQUIRED_KEYS:
            raise ValueError(
                "command must have exactly id, account, kind, and amount fields"
            )
        if command["kind"] not in ("credit", "debit"):
            raise ValueError("kind must be 'credit' or 'debit'")
        amount = command["amount"]
        if not _is_int(amount) or amount <= 0:
            raise ValueError("amount must be a positive integer")
        if not _is_hashable(command["id"]):
            raise ValueError("command id must be hashable")
        if not _is_hashable(command["account"]):
            raise ValueError("account must be hashable")