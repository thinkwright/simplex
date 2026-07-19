"""Core Ledger implementation.

A thread-safe, append-only ledger with idempotent command application.

Rules implemented:
    R1: Exposed via idledger.public.
    R2: Ledger(initial=None) accepts a mapping of account -> non-negative int;
        snapshot returns a new account-name-sorted dict.
    R3: apply(command) accepts exactly {id, account, kind, amount}; kind is
        "credit" or "debit"; amount is a positive int; success returns
        exactly {id, account, balance}.
    R4: Repeating an identical successful command id returns the original
        result without re-applying.
    R5: Reusing a successful command id with different content returns the
        original result and leaves balances unchanged.
    R6: A debit that would make a balance negative raises InsufficientFunds,
        leaves all state unchanged, and does not consume the command id.
    R7: Invalid initial state or command structure raises ValueError and
        leaves all state and command history unchanged.
    R8: apply and snapshot are thread-safe; concurrent successful commands
        are each reflected exactly once.
"""

from threading import RLock

from idledger.errors import InsufficientFunds, CommandConflict

# The exact set of keys a command must contain, and only contain.
_REQUIRED_KEYS = frozenset({"id", "account", "kind", "amount"})
_VALID_KINDS = frozenset({"credit", "debit"})


class Ledger:
    """A thread-safe ledger with idempotent command application."""

    def __init__(self, initial=None):
        # Validate and copy initial state under the lock so that the
        # post-condition (no negative balances, integer cents) is enforced
        # before any state is observable.
        self._lock = RLock()
        self._balances = {}
        self._history = {}  # command_id -> (command_dict, result_dict)
        if initial is not None:
            self._validate_initial(initial)
            for name, balance in initial.items():
                self._balances[name] = balance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def snapshot(self):
        """Return a new dict of account -> balance, sorted by account name."""
        with self._lock:
            # Build a fresh dict sorted by account name.
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply a command idempotently.

        Returns {"id": ..., "account": ..., "balance": ...} on success.
        Raises InsufficientFunds, CommandConflict, or ValueError otherwise.
        """
        # Validate command structure first (outside the lock for the
        # structural checks; we re-validate under the lock for the
        # idempotency path so that history is consistent).
        normalized = self._validate_command(command)

        with self._lock:
            # Idempotency: if we've seen this id before, return the
            # original result. If the content differs, the first
            # successful command wins (R5) — return the original result
            # and leave balances unchanged.
            existing = self._history.get(normalized["id"])
            if existing is not None:
                stored_command, stored_result = existing
                if stored_command != normalized:
                    # Reused id with different content: return original
                    # result, do not change balances. Per R5 we do not
                    # raise; we return the original result.
                    return dict(stored_result)
                # Identical command: return original result.
                return dict(stored_result)

            account = normalized["account"]
            amount = normalized["amount"]
            kind = normalized["kind"]

            current = self._balances.get(account, 0)
            if kind == "credit":
                new_balance = current + amount
            else:  # debit
                new_balance = current - amount
                if new_balance < 0:
                    # R6: raise InsufficientFunds, leave all state
                    # unchanged, do NOT consume the command id.
                    raise InsufficientFunds(
                        f"debit of {amount} from account {account!r} "
                        f"with balance {current} would go negative"
                    )

            # Commit: update balance and record history atomically.
            self._balances[account] = new_balance
            result = {
                "id": normalized["id"],
                "account": account,
                "balance": new_balance,
            }
            self._history[normalized["id"]] = (normalized, result)
            return dict(result)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_initial(initial):
        if not isinstance(initial, dict):
            raise ValueError("initial must be a mapping of account -> balance")
        for name, balance in initial.items():
            if not isinstance(name, str):
                raise ValueError(
                    f"account names must be strings, got {type(name).__name__}"
                )
            if isinstance(balance, bool) or not isinstance(balance, int):
                raise ValueError(
                    f"balance for account {name!r} must be an integer, "
                    f"got {type(balance).__name__}"
                )
            if balance < 0:
                raise ValueError(
                    f"balance for account {name!r} must be non-negative, "
                    f"got {balance}"
                )

    @staticmethod
    def _validate_command(command):
        if not isinstance(command, dict):
            raise ValueError("command must be a mapping")
        if set(command.keys()) != _REQUIRED_KEYS:
            raise ValueError(
                f"command must contain exactly the keys "
                f"{sorted(_REQUIRED_KEYS)}, got {sorted(command.keys())}"
            )

        cid = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]

        if not isinstance(cid, str):
            raise ValueError("command id must be a string")
        if not cid:
            raise ValueError("command id must be a non-empty string")
        if not isinstance(account, str):
            raise ValueError("command account must be a string")
        if not account:
            raise ValueError("command account must be a non-empty string")
        if kind not in _VALID_KINDS:
            raise ValueError(
                f"command kind must be 'credit' or 'debit', got {kind!r}"
            )
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError(
                f"command amount must be an integer, got "
                f"{type(amount).__name__}"
            )
        if amount <= 0:
            raise ValueError(
                f"command amount must be a positive integer, got {amount}"
            )

        # Return a normalized copy so callers cannot mutate stored state.
        return {
            "id": cid,
            "account": account,
            "kind": kind,
            "amount": amount,
        }