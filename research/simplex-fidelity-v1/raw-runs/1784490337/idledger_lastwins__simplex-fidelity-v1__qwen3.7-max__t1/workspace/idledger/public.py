"""Public API for the idledger package."""

import threading


class InsufficientFunds(Exception):
    """Raised when a debit would result in a negative balance."""
    pass


class CommandConflict(Exception):
    """Raised when a conflicting command replacement cannot be applied."""
    pass


class Ledger:
    """A thread-safe idempotent ledger with command conflict resolution.

    Parameters
    ----------
    initial : dict or None
        Mapping of account names (str) to non-negative integer balances.
    """

    def __init__(self, initial=None):
        self._lock = threading.Lock()
        self._balances: dict[str, int] = {}
        # _commands stores successful commands: id -> (command_copy, result_copy)
        self._commands: dict = {}

        if initial is not None:
            if not isinstance(initial, dict):
                raise ValueError("initial must be a dict mapping account names to balances")
            for account, balance in initial.items():
                if not isinstance(account, str):
                    raise ValueError(
                        f"account name must be a string, got {type(account).__name__}"
                    )
                if isinstance(balance, bool) or not isinstance(balance, int):
                    raise ValueError(
                        f"balance must be an integer, got {type(balance).__name__}"
                    )
                if balance < 0:
                    raise ValueError(
                        f"balance for {account!r} must be non-negative, got {balance}"
                    )
            # Only mutate state after all validation passes (atomic)
            for account, balance in initial.items():
                self._balances[account] = balance

    def snapshot(self) -> dict:
        """Return a new dict of account balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command) -> dict:
        """Apply a command to the ledger.

        Parameters
        ----------
        command : dict
            Must contain exactly the keys: id, account, kind, amount.

        Returns
        -------
        dict
            Contains exactly the keys: id, account, balance.

        Raises
        ------
        ValueError
            If the command structure is invalid.
        InsufficientFunds
            If a debit would result in a negative balance.
        CommandConflict
            If a conflicting command replacement fails.
        """
        with self._lock:
            return self._apply_locked(command)

    # ------------------------------------------------------------------
    # Internal helpers (must be called while holding self._lock)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_command(command):
        """Validate command structure. Returns (cmd_id, account, kind, amount).

        Raises ValueError on any structural problem.
        """
        if not isinstance(command, dict):
            raise ValueError("command must be a dict")

        required_keys = {"id", "account", "kind", "amount"}
        actual_keys = set(command.keys())
        if actual_keys != required_keys:
            extra = actual_keys - required_keys
            missing = required_keys - actual_keys
            parts = []
            if extra:
                parts.append(f"unexpected keys: {extra}")
            if missing:
                parts.append(f"missing keys: {missing}")
            raise ValueError(f"invalid command structure – {', '.join(parts)}")

        cmd_id = command["id"]
        account = command["account"]
        kind = command["kind"]
        amount = command["amount"]

        # Validate id is hashable
        try:
            hash(cmd_id)
        except TypeError:
            raise ValueError("command id must be hashable")

        if not isinstance(account, str):
            raise ValueError(f"account must be a string, got {type(account).__name__}")

        if kind not in ("credit", "debit"):
            raise ValueError(f"kind must be 'credit' or 'debit', got {kind!r}")

        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError(f"amount must be an integer, got {type(amount).__name__}")

        if amount <= 0:
            raise ValueError(f"amount must be positive, got {amount}")

        return cmd_id, account, kind, amount

    def _execute(self, account: str, kind: str, amount: int) -> int:
        """Apply a credit/debit to *account* and return the new balance.

        Raises InsufficientFunds if the debit would go negative.
        """
        if kind == "credit":
            self._balances[account] += amount
        else:  # debit
            new_balance = self._balances[account] - amount
            if new_balance < 0:
                raise InsufficientFunds(
                    f"insufficient funds in {account!r}: "
                    f"balance {self._balances[account]}, debit {amount}"
                )
            self._balances[account] = new_balance
        return self._balances[account]

    def _apply_locked(self, command):
        """Core apply logic, called while holding the lock."""
        # --- Validate (raises ValueError on bad structure) ---
        cmd_id, account, kind, amount = self._validate_command(command)

        # Account must exist
        if account not in self._balances:
            raise ValueError(f"account {account!r} does not exist in the ledger")

        # --- Idempotency / conflict check ---
        if cmd_id in self._commands:
            stored_cmd, stored_result = self._commands[cmd_id]

            # R4: identical successful command → return cached result
            if (
                stored_cmd["account"] == account
                and stored_cmd["kind"] == kind
                and stored_cmd["amount"] == amount
            ):
                return dict(stored_result)

            # R5: conflicting command id → attempt atomic replacement
            orig_account = stored_cmd["account"]
            orig_kind = stored_cmd["kind"]
            orig_amount = stored_cmd["amount"]

            # Snapshot for rollback
            saved_balances = dict(self._balances)
            saved_commands = dict(self._commands)

            # Step 1: reverse the original command
            reverse_kind = "credit" if orig_kind == "debit" else "debit"
            try:
                self._execute(orig_account, reverse_kind, orig_amount)
            except InsufficientFunds:
                # Cannot reverse → preserve original, signal conflict
                self._balances = saved_balances
                self._commands = saved_commands
                raise CommandConflict(
                    f"cannot reverse original command {cmd_id!r}; "
                    f"original preserved"
                )

            # Remove old command record before applying replacement
            del self._commands[cmd_id]

            # Step 2: apply the replacement command
            try:
                new_balance = self._execute(account, kind, amount)
            except InsufficientFunds:
                # Replacement fails → full rollback, preserve original
                self._balances = saved_balances
                self._commands = saved_commands
                raise CommandConflict(
                    f"replacement command for {cmd_id!r} failed; "
                    f"original preserved"
                )

            # Success → record the replacement
            result_dict = {"id": cmd_id, "account": account, "balance": new_balance}
            self._commands[cmd_id] = (dict(command), dict(result_dict))
            return dict(result_dict)

        # --- New command ---
        new_balance = self._execute(account, kind, amount)
        result_dict = {"id": cmd_id, "account": account, "balance": new_balance}
        self._commands[cmd_id] = (dict(command), dict(result_dict))
        return dict(result_dict)
