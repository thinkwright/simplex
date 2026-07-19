"""Core implementation of the idledger ledger.

Only the Python standard library is used here (``threading`` and
``collections.abc``); no third-party dependencies are required.
"""

import threading
from collections.abc import Mapping


class InsufficientFunds(Exception):
    """Raised when a debit would leave an account with a negative balance."""


class CommandConflict(Exception):
    """Raised when a successful command id is reused with different content."""


def _is_int(value):
    """Return ``True`` when *value* is an ``int`` but not a ``bool``.

    ``bool`` is a subclass of ``int`` in Python, so it is rejected explicitly
    so that values such as ``True``/``False`` are not silently treated as the
    integers ``1``/``0``.
    """
    return isinstance(value, int) and not isinstance(value, bool)


_REQUIRED_KEYS = frozenset(("id", "account", "kind", "amount"))


class Ledger:
    """An idempotent, thread-safe ledger of integer-cent account balances.

    Balances are stored as integer cents.  Every successful command is recorded
    by its ``id`` so that repeating an identical command returns the original
    result without re-applying it, while reusing an id with different content
    raises :class:`CommandConflict`.
    """

    def __init__(self, initial=None):
        self._lock = threading.RLock()
        self._balances = self._build_initial(initial)
        # command id -> result dict ({"id", "account", "balance"})
        self._results = {}
        # command id -> normalized command dict (for content comparison)
        self._commands = {}

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_initial(initial):
        if initial is None:
            return {}
        if not isinstance(initial, Mapping):
            raise ValueError(
                "initial must be a mapping of account names to non-negative "
                "integer balances"
            )
        balances = {}
        for name, balance in initial.items():
            if not _is_int(balance) or balance < 0:
                raise ValueError(
                    "invalid balance %r for account %r: balances must be "
                    "non-negative integers" % (balance, name)
                )
            balances[name] = balance
        return balances

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def snapshot(self):
        """Return a new dict of balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply an idempotent command and return its result.

        The command must be a mapping with exactly the keys ``id``,
        ``account``, ``kind`` and ``amount`` where ``kind`` is ``"credit"``
        or ``"debit"`` and ``amount`` is a positive integer.  On success a
        mapping with exactly ``id``, ``account`` and ``balance`` is returned.
        """
        self._validate_command(command)
        cmd = dict(command)
        with self._lock:
            cid = cmd["id"]
            existing = self._results.get(cid)
            if existing is not None:
                if self._commands[cid] == cmd:
                    # Identical successful command: return the original result.
                    return dict(existing)
                raise CommandConflict(
                    "command id %r already used with different content" % (cid,)
                )

            account = cmd["account"]
            kind = cmd["kind"]
            amount = cmd["amount"]
            current = self._balances.get(account, 0)

            if kind == "debit":
                if amount > current:
                    # Atomic failure: no state changes, id not consumed.
                    raise InsufficientFunds(
                        "debit of %r from account %r would leave a negative "
                        "balance" % (amount, account)
                    )
                new_balance = current - amount
            else:  # credit
                new_balance = current + amount

            # Commit atomically under the lock.
            self._balances[account] = new_balance
            result = {"id": cid, "account": account, "balance": new_balance}
            self._results[cid] = result
            self._commands[cid] = cmd
            return dict(result)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_command(command):
        if not isinstance(command, Mapping):
            raise ValueError(
                "command must be a mapping with exactly id, account, kind, "
                "and amount"
            )
        if set(command.keys()) != _REQUIRED_KEYS:
            raise ValueError(
                "command must have exactly id, account, kind, and amount"
            )
        kind = command["kind"]
        if kind not in ("credit", "debit"):
            raise ValueError("kind must be 'credit' or 'debit'")
        amount = command["amount"]
        if not _is_int(amount) or amount <= 0:
            raise ValueError("amount must be a positive integer")
        try:
            hash(command["id"])
        except TypeError:
            raise ValueError("command id must be hashable")
        try:
            hash(command["account"])
        except TypeError:
            raise ValueError("command account must be hashable")