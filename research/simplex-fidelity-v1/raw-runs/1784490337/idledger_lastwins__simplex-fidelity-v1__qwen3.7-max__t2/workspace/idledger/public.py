"""Public API for idledger."""

import threading
from typing import Optional, Dict, Any


class InsufficientFunds(Exception):
    """Raised when a debit would result in a negative balance."""
    pass


class CommandConflict(Exception):
    """Raised when there's a conflict in command processing."""
    pass


class Ledger:
    """A thread-safe ledger with idempotent command processing."""
    
    def __init__(self, initial: Optional[Dict[str, int]] = None):
        """
        Initialize the ledger with optional initial balances.
        
        Args:
            initial: Optional mapping of account names to non-negative integer balances.
            
        Raises:
            ValueError: If initial state is invalid (negative balances, non-integer values, etc.)
        """
        self._lock = threading.RLock()
        self._balances: Dict[str, int] = {}
        self._commands: Dict[str, Dict[str, Any]] = {}  # command_id -> {command, result}
        
        if initial is not None:
            if not isinstance(initial, dict):
                raise ValueError("Initial state must be a dictionary")
            
            for account, balance in initial.items():
                if not isinstance(account, str):
                    raise ValueError(f"Account name must be a string, got {type(account)}")
                if not isinstance(balance, int) or isinstance(balance, bool):
                    raise ValueError(f"Balance must be an integer, got {type(balance)}")
                if balance < 0:
                    raise ValueError(f"Initial balance cannot be negative: {balance}")
                self._balances[account] = balance
    
    def snapshot(self) -> Dict[str, int]:
        """
        Return a snapshot of current balances sorted by account name.
        
        Returns:
            A new dictionary with account names as keys and balances as values,
            sorted by account name.
        """
        with self._lock:
            return dict(sorted(self._balances.items()))
    
    def apply(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a command to the ledger.
        
        Args:
            command: A dictionary with exactly keys: id, account, kind, amount
                    - id: unique command identifier
                    - account: account name (string)
                    - kind: 'credit' or 'debit'
                    - amount: positive integer amount
                    
        Returns:
            A dictionary with id, account, and resulting balance.
            
        Raises:
            ValueError: If command structure is invalid.
            InsufficientFunds: If debit would result in negative balance.
        """
        with self._lock:
            # Validate command structure
            self._validate_command(command)
            
            cmd_id = command['id']
            account = command['account']
            kind = command['kind']
            amount = command['amount']
            
            # Check if this command ID was already processed successfully
            if cmd_id in self._commands:
                stored = self._commands[cmd_id]
                stored_command = stored['command']
                
                # Check if it's the same command (idempotency - R4)
                if self._commands_equal(command, stored_command):
                    return stored['result'].copy()
                
                # It's a conflicting command (R5) - need to replace
                return self._replace_command(cmd_id, stored_command, command)
            
            # New command - apply it
            result = self._apply_new_command(account, kind, amount)
            result_dict = {
                'id': cmd_id,
                'account': account,
                'balance': result
            }
            
            # Store the successful command
            self._commands[cmd_id] = {
                'command': command.copy(),
                'result': result_dict.copy()
            }
            
            return result_dict
    
    def _validate_command(self, command: Dict[str, Any]) -> None:
        """Validate command structure."""
        if not isinstance(command, dict):
            raise ValueError("Command must be a dictionary")
        
        required_keys = {'id', 'account', 'kind', 'amount'}
        if set(command.keys()) != required_keys:
            raise ValueError(f"Command must have exactly keys {required_keys}, got {set(command.keys())}")
        
        # Validate id
        cmd_id = command['id']
        if not isinstance(cmd_id, str):
            raise ValueError(f"Command id must be a string, got {type(cmd_id)}")
        
        # Validate account
        account = command['account']
        if not isinstance(account, str):
            raise ValueError(f"Account must be a string, got {type(account)}")
        
        # Validate kind
        kind = command['kind']
        if kind not in ('credit', 'debit'):
            raise ValueError(f"Kind must be 'credit' or 'debit', got {kind}")
        
        # Validate amount
        amount = command['amount']
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError(f"Amount must be an integer, got {type(amount)}")
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")
    
    def _commands_equal(self, cmd1: Dict[str, Any], cmd2: Dict[str, Any]) -> bool:
        """Check if two commands are equal."""
        return (cmd1['id'] == cmd2['id'] and
                cmd1['account'] == cmd2['account'] and
                cmd1['kind'] == cmd2['kind'] and
                cmd1['amount'] == cmd2['amount'])
    
    def _apply_new_command(self, account: str, kind: str, amount: int) -> int:
        """
        Apply a new command and return the resulting balance.
        
        Raises:
            InsufficientFunds: If debit would result in negative balance.
        """
        # Ensure account exists
        if account not in self._balances:
            self._balances[account] = 0
        
        current_balance = self._balances[account]
        
        if kind == 'credit':
            new_balance = current_balance + amount
        else:  # debit
            new_balance = current_balance - amount
            if new_balance < 0:
                raise InsufficientFunds(
                    f"Insufficient funds in account '{account}': "
                    f"balance {current_balance}, debit {amount}"
                )
        
        self._balances[account] = new_balance
        return new_balance
    
    def _replace_command(
        self,
        cmd_id: str,
        old_command: Dict[str, Any],
        new_command: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replace an existing command with a new one (R5).
        
        This atomically:
        1. Reverses the original command
        2. Applies the new command
        3. If new command fails, restores the original
        
        Returns:
            The result of the new command.
            
        Raises:
            InsufficientFunds: If the new command would fail.
        """
        old_account = old_command['account']
        old_kind = old_command['kind']
        old_amount = old_command['amount']
        
        new_account = new_command['account']
        new_kind = new_command['kind']
        new_amount = new_command['amount']
        
        # Save state for potential rollback
        saved_balances = self._balances.copy()
        
        try:
            # Step 1: Reverse the original command
            if old_kind == 'credit':
                # Reverse a credit by debiting
                self._balances[old_account] -= old_amount
            else:
                # Reverse a debit by crediting
                self._balances[old_account] += old_amount
            
            # Step 2: Apply the new command
            result_balance = self._apply_new_command(new_account, new_kind, new_amount)
            
            # Success - update stored command
            result_dict = {
                'id': cmd_id,
                'account': new_account,
                'balance': result_balance
            }
            
            self._commands[cmd_id] = {
                'command': new_command.copy(),
                'result': result_dict.copy()
            }
            
            return result_dict
            
        except InsufficientFunds:
            # New command failed - restore original state
            self._balances = saved_balances
            # Re-raise the exception
            raise
