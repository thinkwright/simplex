"""Public API for the :mod:`idledger` package.

This module exposes the ledger implementation together with the two exception
types that callers may need to handle.  Only the Python standard library is
used (see constraint [C2]).

Public objects
--------------
Ledger
    A thread-safe ledger of integer-cent account balances.
InsufficientFunds
    Raised when a debit would leave an account with a negative balance.
CommandConflict
    Raised when a successful command id is reused with different content.
"""

import threading
from collections.abc import Mapping

__all__ = ["Ledger", "InsufficientFunds", "CommandConflict"]


class InsufficientFunds(Exception):
    """Raised when a debit would leave an account with a negative balance."""


class CommandConflict(Exception):
    """Raised when a successful command id is reused with different content."""


# A command must carry exactly these four keys.
_COMMAND_KEYS = frozenset(("id", "account", "kind", "amount"))
_VALID_KINDS = ("credit", "debit")


def _is_int(value):
    """Return True only for genuine ints (``bool`` is rejected)."""
    # ``bool`` is a subclass of ``int``; treat it as a distinct, invalid type so
    # that values such as ``True``/``False`` are never accepted as amounts or
    # balances.
    return type(value) is int


def _validate_initial(initial):
    """Validate and copy the initial balance mapping.

    Returns a fresh dict of account name -> non-negative int balance.
    Raises ``ValueError`` for any invalid initial state.
    """
    if initial is None:
        return {}
    if not isinstance(initial, Mapping):
        raise ValueError("initial balances must be a mapping or None")
    validated = {}
    for name, balance in initial.items():
        if not isinstance(name, str):
            raise ValueError("account names must be strings")
        if not _is_int(balance) or balance < 0:
            raise ValueError("balances must be non-negative integers")
        validated[name] = balance
    return validated


def _validate_command(command):
    """Validate the structure of a command.

    Returns the tuple ``(id, account, kind, amount)``.  Raises ``ValueError``
    for any structurally invalid command.
    """
    if not isinstance(command, Mapping):
        raise ValueError("command must be a mapping")
    if set(command.keys()) != _COMMAND_KEYS:
        raise ValueError(
            "command must have exactly the keys: id, account, kind, amount"
        )

    cid = command["id"]
    try:
        hash(cid)
    except TypeError:
        raise ValueError("command id must be hashable")

    account = command["account"]
    if not isinstance(account, str):
        raise ValueError("account must be a string")

    kind = command["kind"]
    if kind not in _VALID_KINDS:
        raise ValueError("kind must be 'credit' or 'debit'")

    amount = command["amount"]
    if not _is_int(amount) or amount <= 0:
        raise ValueError("amount must be a positive integer")

    return cid, account, kind, amount


class Ledger:
    """A thread-safe ledger of integer-cent account balances.

    Each successful command is recorded under its command id so that repeating
    the identical command is idempotent, while reusing the id with different
    content is rejected.

    Parameters
    ----------
    initial:
        Optional mapping of account names (strings) to non-negative integer
        balances (cents).  Defaults to an empty ledger.
    """

    def __init__(self, initial=None):
        self._lock = threading.RLock()
        self._balances = _validate_initial(initial)
        # command id -> (command copy, result copy)
        self._history = {}

    def snapshot(self):
        """Return a new dict of balances keyed by account name, sorted."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply ``command`` and return its result.

        ``command`` must be a mapping with exactly the keys ``id``, ``account``,
        ``kind`` and ``amount`` where ``kind`` is ``"credit"`` or ``"debit"`` and
        ``amount`` is a positive integer.  A success returns a mapping with
        exactly ``id``, ``account`` and ``balance``.

        Raises
        ------
        ValueError
            If the command structure is invalid.
        CommandConflict
            If a successful command id is reused with different content.
        InsufficientFunds
            If a debit would leave a negative balance.
        """
        with self._lock:
            cid, account, kind, amount = _validate_command(command)

            # Idempotent replay or conflict detection for a known command id.
            stored = self._history.get(cid)
            if stored is not None:
                stored_command, stored_result = stored
                if stored_command == command:
                    return dict(stored_result)
                raise CommandConflict(
                    "command id %r already used with different content" % (cid,)
                )

            current = self._balances.get(account, 0)
            if kind == "credit":
                new_balance = current + amount
            else:  # debit
                new_balance = current - amount
                if new_balance < 0:
                    # Atomic failure: do not consume the command id.
                    raise InsufficientFunds(
                        "debit of %d from %r exceeds available balance %d"
                        % (amount, account, current)
                    )

            self._balances[account] = new_balance
            result = {"id": cid, "account": account, "balance": new_balance}
            self._history[cid] = (dict(command), dict(result))
            return dict(result)