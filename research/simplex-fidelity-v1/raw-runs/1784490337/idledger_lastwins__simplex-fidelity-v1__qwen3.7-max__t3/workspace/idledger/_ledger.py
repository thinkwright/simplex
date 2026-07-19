"""Core Ledger implementation."""

import threading
from ._exceptions import InsufficientFunds, CommandConflict


def _is_valid_int(value):
    """Check if value is an integer but not a boolean."""
    return type(value) is int


class Ledger:
    """A thread-safe ledger with idempotent command application."""

    def __init__(self, initial=None):
        self._lock = threading.Lock()
        self._balances = {}
        self._commands = {}  # cmd_id -> (command_dict, result_dict)

        if initial is not None:
            if not isinstance(initial, dict):
                raise ValueError("initial must be a dict mapping account names to balances")
            for name, balance in initial.items():
                if not isinstance(name, str) or not name:
                    raise ValueError(f"account name must be a non-empty string: {name!r}")
                if not _is_valid_int(balance) or balance < 0:
                    raise ValueError(
                        f"balance must be a non-negative integer for account {name!r}: {balance!r}"
                    )
            # Only mutate state after all validation passes
            for name, balance in initial.items():
                self._balances[name] = balance

    def snapshot(self):
        """Return a new dict of account balances sorted by account name."""
        with self._lock:
            return dict(sorted(self._balances.items()))

    def apply(self, command):
        """Apply a command to the ledger.

        Args:
            command: dict with exactly keys id, account, kind, amount.

        Returns:
            dict with keys id, account, balance.

        Raises:
            ValueError: if command structure is invalid.
            InsufficientFunds: if debit would cause negative balance.
        """
        with self._lock:
            # Validate command structure first (R7 - atomic, no state change)
            self._validate_command(command)

            cmd_id = command['id']
            account = command['account']
            kind = command['kind']
            amount = command['amount']

            # Check if this command id was already used successfully
            if cmd_id in self._commands:
                original_cmd, original_result = self._commands[cmd_id]

                # R4: identical command → return cached result
                if (original_cmd['account'] == account and
                        original_cmd['kind'] == kind and
                        original_cmd['amount'] == amount):
                    return dict(original_result)

                # R5: conflicting command → atomic replace
                return self._replace_command(cmd_id, original_cmd, command)

            # New command: apply to balances
            new_balance = self._execute(account, kind, amount)
            result = {'id': cmd_id, 'account': account, 'balance': new_balance}
            # Store copies to prevent external mutation
            self._commands[cmd_id] = (
                {'id': cmd_id, 'account': account, 'kind': kind, 'amount': amount},
                dict(result),
            )
            return dict(result)

    def _validate_command(self, command):
        """Validate command structure. Raises ValueError on any issue."""
        if not isinstance(command, dict):
            raise ValueError("command must be a dict")

        expected_keys = {'id', 'account', 'kind', 'amount'}
        if set(command.keys()) != expected_keys:
            extra = set(command.keys()) - expected_keys
            missing = expected_keys - set(command.keys())
            parts = []
            if extra:
                parts.append(f"unexpected keys: {extra}")
            if missing:
                parts.append(f"missing keys: {missing}")
            raise ValueError(f"invalid command structure: {', '.join(parts)}")

        # Validate id is hashable
        cmd_id = command['id']
        try:
            hash(cmd_id)
        except TypeError:
            raise ValueError(f"command id must be hashable: {cmd_id!r}")

        # Validate account
        account = command['account']
        if not isinstance(account, str):
            raise ValueError(f"account must be a string: {account!r}")
        if account not in self._balances:
            raise ValueError(f"unknown account: {account!r}")

        # Validate kind
        kind = command['kind']
        if kind not in ('credit', 'debit'):
            raise ValueError(f"kind must be 'credit' or 'debit': {kind!r}")

        # Validate amount (positive integer, not bool)
        amount = command['amount']
        if not _is_valid_int(amount) or amount <= 0:
            raise ValueError(f"amount must be a positive integer: {amount!r}")

    def _execute(self, account, kind, amount):
        """Apply a credit or debit to an account balance.

        Returns the new balance. Raises InsufficientFunds if debit would go negative.
        """
        if kind == 'debit':
            if self._balances[account] < amount:
                raise InsufficientFunds(
                    f"insufficient funds in {account!r}: "
                    f"balance {self._balances[account]}, debit {amount}"
                )
            self._balances[account] -= amount
        else:  # credit
            self._balances[account] += amount
        return self._balances[account]

    def _replace_command(self, cmd_id, original_cmd, new_command):
        """Atomically replace a conflicting command.

        Reverses the original, applies the replacement.
        If replacement fails, preserves the original and raises.
        """
        # Save state for rollback
        saved_balances = dict(self._balances)
        saved_commands = {k: (dict(v[0]), dict(v[1])) for k, v in self._commands.items()}

        try:
            # Reverse the original command
            orig_account = original_cmd['account']
            orig_kind = original_cmd['kind']
            orig_amount = original_cmd['amount']
            reverse_kind = 'debit' if orig_kind == 'credit' else 'credit'
            self._execute(orig_account, reverse_kind, orig_amount)

            # Remove original from command history
            del self._commands[cmd_id]

            # Apply the replacement command
            new_account = new_command['account']
            new_kind = new_command['kind']
            new_amount = new_command['amount']
            new_balance = self._execute(new_account, new_kind, new_amount)

            result = {'id': cmd_id, 'account': new_account, 'balance': new_balance}
            self._commands[cmd_id] = (
                {'id': cmd_id, 'account': new_account, 'kind': new_kind, 'amount': new_amount},
                dict(result),
            )
            return dict(result)

        except (InsufficientFunds, ValueError):
            # Rollback: restore balances and command history
            self._balances = saved_balances
            self._commands = saved_commands
            raise
