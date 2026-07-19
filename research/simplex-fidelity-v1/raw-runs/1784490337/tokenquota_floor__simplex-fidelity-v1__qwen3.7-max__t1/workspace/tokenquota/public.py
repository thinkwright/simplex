import threading
import time
import math


class Bucket:
    """Thread-safe token bucket with configurable capacity and refill rate."""
    
    def __init__(self, capacity, refill_per_second, clock=None):
        """Initialize a token bucket starting at full capacity.
        
        Args:
            capacity: Maximum number of tokens (must be positive)
            refill_per_second: Rate of token replenishment (must be non-negative)
            clock: Optional callable returning current time (defaults to time.time)
        
        Raises:
            ValueError: If capacity <= 0 or refill_per_second < 0
        """
        if isinstance(capacity, bool) or not isinstance(capacity, (int, float)) or capacity <= 0:
            raise ValueError("capacity must be positive")
        if isinstance(refill_per_second, bool) or not isinstance(refill_per_second, (int, float)) or refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")
        
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.clock = clock if clock is not None else time.time
        self.balance = float(capacity)
        self.last_time = self.clock()
        self.lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time, clamp to capacity, and floor."""
        current_time = self.clock()
        elapsed = current_time - self.last_time
        
        # Treat backward clock movement as zero elapsed time
        if elapsed < 0:
            elapsed = 0
        
        # Add tokens based on elapsed time
        self.balance += elapsed * self.refill_per_second
        
        # Clamp to capacity
        self.balance = min(self.balance, float(self.capacity))
        
        # Round down to nearest integer
        self.balance = math.floor(self.balance)
        
        self.last_time = current_time
    
    def allow(self, amount=1):
        """Attempt to consume tokens from the bucket.
        
        Refills the bucket first, then tries to consume the specified amount.
        
        Args:
            amount: Number of tokens to consume (must be positive and not boolean)
        
        Returns:
            bool: True if tokens were consumed, False if insufficient tokens
        
        Raises:
            ValueError: If amount <= 0 or amount is boolean
        """
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("amount must be positive and not boolean")
        
        with self.lock:
            self._refill()
            if self.balance >= amount:
                self.balance -= amount
                return True
            return False
    
    def available(self):
        """Get the current number of available tokens without consuming.
        
        Refills the bucket first, then returns the current balance.
        
        Returns:
            int: Current number of available tokens
        """
        with self.lock:
            self._refill()
            return self.balance
