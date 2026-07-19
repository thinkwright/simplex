"""Ledger implementation.

A Ledger tracks integer-cent balances per account name. Commands are applied
with an id; the same id is idempotent (returns the original result), and a
conflicting command with the same id atomically replaces the prior one.
"""

from threading import RLock


class InsufficientFunds(Exception):
    """Raised when a debit would make an account balance negative."""


class CommandConflict(Exception):
    """Raised when a command id conflicts with a prior command and the
    conflict cannot be resolved atomically (e.g. the replacement command
    itself is invalid)."""


_VALID_KINDS = ("credit", "debit")


def _validate_initial(initial):
    """Validate the initial mapping. Returns a sorted dict copy.

    Raises ValueError on any invalid entry.
    """
    if initial is None:
        return {}
    if not isinstance(initial, dict):
        raise ValueError("initial must be a mapping of account names to balances")
    result = {}
    for account, balance in initial.items():
        if not isinstance(account, str):
            raise ValueError("account names must be strings")
        if isinstance(balance, bool) or not isinstance(balance, int):
            raise ValueError("balances must be integers")
        if balance < 0:
            raise ValueError("balances must be non-negative")
        result[account] = balance
    return dict(sorted(result.items()))


def _validate_command(command):
    """Validate a command structure. Returns (id, account, kind, amount).

    Raises ValueError on any structural problem.
    """
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping")
    if set(command.keys()) != {"id", "account", "kind", "amount"}:
        raise ValueError(
            "command must contain exactly id, account, kind, and amount"
        )
    cid = command["id"]
    account = command["account"]
    kind = command["kind"]
    amount = command["amount"]

    if not isinstance(cid, str):
        raise ValueError("command id must be a string")
    if not isinstance(account, str):
        raise ValueError("command account must be a string")
    if kind not in _VALID_KINDS:
        raise ValueError("command kind must be 'credit' or 'debit'")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("command amount must be an integer")
    if amount <= 0:
        raise ValueError("command amount must be a positive integer")

    return cid, account, kind, amount


class Ledger:
    """A thread-safe ledger of integer-cent balances.

    Ledger(initial=None) creates a ledger from an optional mapping of
    account names to non-negative integer balances.

    apply(command) applies a command and returns a dict with the command's
    id, account, and the resulting balance.

    snapshot() returns a new account-name-sorted dict of balances.
    """

    def __init__(self, initial=None):
        self._lock = RLock()
        # Validate up front so a bad initial state fails before any state
        # is established.
        validated = _validate_initial(initial)
        self._balances = validated
        # History of successful commands: id -> (account, kind, amount, balance)
        self._history = {}

    def snapshot(self):
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        # Validate the command structure outside the lock; if it's invalid
        # we raise ValueError without touching any state.
        cid, account, kind, amount = _validate_command(command)

        with self._lock:
            # Idempotent replay: same id, same command -> return original.
            prior = self._history.get(cid)
            if prior is not None:
                p_account, p_kind, p_amount, p_balance = prior
                if (
                    p_account == account
                    and p_kind == kind
                    and p_amount == amount
                ):
                    return {
                        "id": cid,
                        "account": account,
                        "balance": p_balance,
                    }
                # Conflict: atomically replace the original.
                # Step 1: reverse the original.
                if p_kind == "credit":
                    self._balances[p_account] -= p_amount
                else:
                    self._balances[p_account] += p_amount
                # Step 2: try to apply the replacement.
                try:
                    new_balance = self._apply_no_lock(account, kind, amount)
                except InsufficientFunds:
                    # Preserve the original: re-apply the prior command.
                    if p_kind == "credit":
                        self._balances[p_account] += p_amount
                    else:
                        self._balances[p_account] -= p_amount
                    # Restore history to the original.
                    self._history[cid] = prior
                    raise
                # Step 3: record the replacement.
                self._history[cid] = (account, kind, amount, new_balance)
                return {
                    "id": cid,
                    "account": account,
                    "balance": new_balance,
                }

            # Fresh command.
            new_balance = self._apply_no_lock(account, kind, amount)
            self._history[cid] = (account, kind, amount, new_balance)
            return {
                "id": cid,
                "account": account,
                "balance": new_balance,
            }

    def _apply_no_lock(self, account, kind, amount):
        """Apply a validated command without acquiring the lock.

        Caller must hold self._lock. Raises InsufficientFunds if the
        resulting balance would be negative; in that case no state is
        mutated and the history is not updated.
        """
        current = self._balances.get(account, 0)
        if kind == "credit":
            new_balance = current + amount
        else:  # debit
            new_balance = current - amount
        if new_balance < 0:
            raise InsufficientFunds(
                "debit of {0} from account {1} would leave a negative balance".format(
                    amount, account
                )
            )
        self._balances[account] = new_balance
        return new_balance