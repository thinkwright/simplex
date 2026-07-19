import threading
from typing import Optional, Dict, Any


class InsufficientFunds(Exception):
    """Raised when a debit would result in a negative balance."""
    pass


class CommandConflict(Exception):
    """Raised when there is a conflict with command execution."""
    pass


class Ledger:
    """A thread-safe ledger that tracks account balances with idempotent commands."""
    
    def __init__(self, initial: Optional[Dict[str, int]] = None):
        """
        Initialize the ledger with optional initial balances.
        
        Args:
            initial: A mapping of account names to non-negative integer balances.
            
        Raises:
            ValueError: If initial state is invalid (not a mapping, non-string keys,
                       non-integer values, or negative balances).
        """
        self._lock = threading.Lock()
        self._balances = {}
        self._commands = {}  # command_id -> result
        
        if initial is not None:
            # Validate initial state
            if not isinstance(initial, dict):
                raise ValueError("Initial state must be a mapping")
            
            for account, balance in initial.items():
                if not isinstance(account, str):
                    raise ValueError("Account names must be strings")
                if not isinstance(balance, int) or isinstance(balance, bool):
                    raise ValueError("Balances must be integers")
                if balance < 0:
                    raise ValueError("Balances must be non-negative")
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
            command: A dictionary with exactly four keys: id, account, kind, amount.
                    - id: command identifier (any hashable type)
                    - account: account name (string)
                    - kind: 'credit' or 'debit' (string)
                    - amount: positive integer
        
        Returns:
            A dictionary with id, account, and balance (the resulting balance).
            
        Raises:
            ValueError: If command structure is invalid or account doesn't exist.
            InsufficientFunds: If debit would result in negative balance.
        """
        with self._lock:
            # Validate command structure first (before any state changes)
            if not isinstance(command, dict):
                raise ValueError("Command must be a dict")
            
            # Check for exactly the required fields
            required_fields = {'id', 'account', 'kind', 'amount'}
            if set(command.keys()) != required_fields:
                raise ValueError("Command must have exactly id, account, kind, amount fields")
            
            cmd_id = command['id']
            account = command['account']
            kind = command['kind']
            amount = command['amount']
            
            # Validate field types and values
            if not isinstance(account, str):
                raise ValueError("Account must be a string")
            if kind not in ('credit', 'debit'):
                raise ValueError("Kind must be 'credit' or 'debit'")
            if not isinstance(amount, int) or isinstance(amount, bool):
                raise ValueError("Amount must be an integer")
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            # Check if command id already exists (idempotency)
            if cmd_id in self._commands:
                # R4/R5: return original result without reapplying
                return self._commands[cmd_id]
            
            # Check account exists
            if account not in self._balances:
                raise ValueError(f"Account '{account}' does not exist")
            
            # Apply command atomically
            current_balance = self._balances[account]
            
            if kind == 'debit':
                if current_balance < amount:
                    # R6: raise InsufficientFunds without consuming command id
                    raise InsufficientFunds(f"Insufficient funds in account '{account}'")
                new_balance = current_balance - amount
            else:  # credit
                new_balance = current_balance + amount
            
            # Update balance
            self._balances[account] = new_balance
            
            # Store command result for idempotency
            result = {
                'id': cmd_id,
                'account': account,
                'balance': new_balance
            }
            self._commands[cmd_id] = result
            
            return result
