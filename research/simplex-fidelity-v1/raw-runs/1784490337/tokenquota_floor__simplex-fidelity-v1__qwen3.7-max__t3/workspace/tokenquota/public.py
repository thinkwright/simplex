"""Public API for tokenquota package."""
import time
import threading
import math


class Bucket:
    """Thread-safe token bucket with configurable capacity and refill rate.
    
    Args:
        capacity: Maximum number of tokens (must be positive)
        refill_per_second: Rate at which tokens are added (must be non-negative)
        clock: Optional callable returning current time (defaults to time.time)
    
    The bucket starts full at capacity.
    """
    
    def __init__(self, capacity, refill_per_second, clock=None):
        # Validate capacity
        if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        
        # Validate refill_per_second
        if isinstance(refill_per_second, bool) or not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")
        
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.clock = clock if clock is not None else time.time
        self.balance = float(capacity)  # starts full
        self.last_time = self.clock()
        self.lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time. Must be called with lock held."""
        current_time = self.clock()
        elapsed = current_time - self.last_time
        
        # Treat backward clock movement as zero elapsed time
        if elapsed < 0:
            elapsed = 0
        
        # Only update balance if time has passed
        if elapsed > 0:
            self.balance += elapsed * self.refill_per_second
            # Never exceed capacity
            self.balance = min(self.balance, self.capacity)
            # Round down to nearest integer
            self.balance = math.floor(self.balance)
            self.last_time = current_time
    
    def allow(self, amount=1):
        """Try to consume tokens from the bucket.
        
        Args:
            amount: Number of tokens to consume (must be positive and not boolean)
        
        Returns:
            True if tokens were consumed, False if insufficient tokens
        
        Raises:
            ValueError: If amount is invalid
        """
        # Validate amount
        if isinstance(amount, bool):
            raise ValueError("amount must not be boolean")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")
        
        with self.lock:
            self._refill()
            if self.balance >= amount:
                self.balance -= amount
                return True
            return False
    
    def available(self):
        """Get current token balance without consuming.
        
        Returns:
            Current number of available tokens (integer after refill)
        """
        with self.lock:
            self._refill()
            return self.balance
