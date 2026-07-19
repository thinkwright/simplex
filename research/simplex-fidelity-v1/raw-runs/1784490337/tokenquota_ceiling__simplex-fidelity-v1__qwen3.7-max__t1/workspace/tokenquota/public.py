"""Public API for tokenquota package."""

import time
import threading
import math


class Bucket:
    """A token bucket for rate limiting.
    
    Args:
        capacity: Maximum number of tokens (must be positive)
        refill_per_second: Rate of token refill (must be non-negative)
        clock: Optional clock function returning current time (defaults to time.time)
    
    The bucket starts full (at capacity).
    """
    
    def __init__(self, capacity, refill_per_second, clock=None):
        # R6: Validate capacity
        if isinstance(capacity, bool):
            raise ValueError("capacity cannot be boolean")
        if not isinstance(capacity, (int, float)):
            raise ValueError("capacity must be a positive number")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        
        # R6: Validate refill_per_second
        if isinstance(refill_per_second, bool):
            raise ValueError("refill_per_second cannot be boolean")
        if not isinstance(refill_per_second, (int, float)):
            raise ValueError("refill_per_second must be a non-negative number")
        if refill_per_second < 0:
            raise ValueError("refill_per_second must be non-negative")
        
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.clock = clock if clock is not None else time.time
        self.balance = float(capacity)  # R1: starts full
        self.last_refill_time = self.clock()
        self.lock = threading.Lock()  # R7: thread safety
    
    def _refill(self):
        """Internal refill logic. Must be called under lock.
        
        R3: Adds elapsed_seconds * refill_per_second tokens, capped at capacity.
            Backward clock movement is treated as zero elapsed time.
        R4: After positive-time refill and capacity clamp, rounds balance up to
            nearest integer without exceeding capacity.
        """
        current_time = self.clock()
        elapsed = current_time - self.last_refill_time
        
        # R3: backward clock movement = zero elapsed time
        if elapsed > 0:
            # Add tokens based on elapsed time
            self.balance += elapsed * self.refill_per_second
            
            # Clamp to capacity
            if self.balance > self.capacity:
                self.balance = self.capacity
            
            # R4: round up to nearest integer, but not exceeding capacity
            self.balance = min(math.ceil(self.balance), self.capacity)
            
            # Update last refill time only when moving forward
            self.last_refill_time = current_time
    
    def allow(self, amount=1):
        """Attempt to consume tokens from the bucket.
        
        Args:
            amount: Number of tokens to consume (default 1, must be positive and not boolean)
        
        Returns:
            True if tokens were consumed, False if insufficient tokens
        
        Raises:
            ValueError: If amount is invalid (X1)
        """
        # R6: Validate amount
        if isinstance(amount, bool):
            raise ValueError("amount cannot be boolean")
        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a positive number")
        if amount <= 0:
            raise ValueError("amount must be positive")
        
        # R7: Thread-safe operation
        with self.lock:
            self._refill()
            
            # R2: consume if enough tokens, otherwise return false without consuming
            if self.balance >= amount:
                self.balance -= amount
                return True
            else:
                return False
    
    def available(self):
        """Get the current number of available tokens without consuming.
        
        Returns:
            Current token balance (R5)
        """
        # R7: Thread-safe operation
        with self.lock:
            self._refill()
            return self.balance
