"""Ledger implementation.

This module implements a small ledger that tracks integer-cent balances
across named accounts. It supports idempotent command application via
command ids, atomic replacement of conflicting commands, and is safe
for concurrent use from multiple threads.
"""

from threading import RLock


class InsufficientFunds(Exception):
    """Raised when a debit would leave an account with a negative balance."""


class CommandConflict(Exception):
    """Internal sentinel used to signal a conflicting command id.

    This is not part of the public contract; it is raised internally
    during the atomic replace path so the caller can distinguish a
    conflict from other failures.
    """


_VALID_KINDS = ("credit", "debit")
_REQUIRED_COMMAND_KEYS = ("id", "account", "kind", "amount")


def _validate_initial(initial):
    if initial is None:
        return {}
    if not isinstance(initial, dict):
        raise ValueError("initial must be a mapping of account name to balance")
    result = {}
    for account, balance in initial.items():
        if not isinstance(account, str) or not account:
            raise ValueError("account names must be non-empty strings")
        if isinstance(balance, bool) or not isinstance(balance, int):
            raise ValueError("balances must be integers")
        if balance < 0:
            raise ValueError("balances must be non-negative")
        result[account] = balance
    return result


def _validate_command(command):
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping")
    if set(command.keys()) != set(_REQUIRED_COMMAND_KEYS):
        raise ValueError(
            "command must contain exactly the keys: id, account, kind, amount"
        )
    cid = command["id"]
    if not isinstance(cid, str) or not cid:
        raise ValueError("command id must be a non-empty string")
    account = command["account"]
    if not isinstance(account, str) or not account:
        raise ValueError("command account must be a non-empty string")
    kind = command["kind"]
    if kind not in _VALID_KINDS:
        raise ValueError("command kind must be 'credit' or 'debit'")
    amount = command["amount"]
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("command amount must be an integer")
    if amount <= 0:
        raise ValueError("command amount must be a positive integer")
    return cid, account, kind, amount


class Ledger:
    """A ledger of integer-cent balances keyed by account name."""

    def __init__(self, initial=None):
        self._lock = RLock()
        # Snapshot of balances; mutated only under self._lock.
        self._balances = _validate_initial(initial)
        # History of successfully applied commands: id -> (account, kind, amount, balance).
        self._history = {}

    def snapshot(self):
        with self._lock:
            # Return a new dict sorted by account name.
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        cid, account, kind, amount = _validate_command(command)

        with self._lock:
            # Idempotent replay: same id + same payload returns the original result.
            prior = self._history.get(cid)
            if prior is not None:
                prior_account, prior_kind, prior_amount, prior_balance = prior
                if (
                    prior_account == account
                    and prior_kind == kind
                    and prior_amount == amount
                ):
                    return {
                        "id": cid,
                        "account": prior_account,
                        "balance": prior_balance,
                    }
                # Conflict: attempt atomic replace.
                return self._replace_conflicting(cid, prior, account, kind, amount)

            # Fresh command: apply it.
            return self._apply_fresh(cid, account, kind, amount)

    # --- internal helpers (must be called with self._lock held) ---

    def _apply_fresh(self, cid, account, kind, amount):
        # Ensure the account exists with a zero balance if not present.
        current = self._balances.get(account, 0)
        if kind == "debit":
            if current - amount < 0:
                raise InsufficientFunds(
                    "debit of {} from account {!r} would leave a negative balance".format(
                        amount, account
                    )
                )
            new_balance = current - amount
        else:  # credit
            new_balance = current + amount

        self._balances[account] = new_balance
        self._history[cid] = (account, kind, amount, new_balance)
        return {"id": cid, "account": account, "balance": new_balance}

    def _replace_conflicting(self, cid, prior, account, kind, amount):
        prior_account, prior_kind, prior_amount, _prior_balance = prior

        # Reverse the original command.
        if prior_kind == "debit":
            # Original debit: reverse by crediting prior_amount.
            self._balances[prior_account] = (
                self._balances.get(prior_account, 0) + prior_amount
            )
        else:
            # Original credit: reverse by debiting prior_amount.
            self._balances[prior_account] = (
                self._balances.get(prior_account, 0) - prior_amount
            )

        # Try to apply the replacement.
        try:
            result = self._apply_fresh(cid, account, kind, amount)
        except Exception:
            # Restore the original state and re-raise.
            if prior_kind == "debit":
                self._balances[prior_account] = (
                    self._balances.get(prior_account, 0) - prior_amount
                )
            else:
                self._balances[prior_account] = (
                    self._balances.get(prior_account, 0) + prior_amount
                )
            # Original history entry is preserved.
            raise

        return result