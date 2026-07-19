"""tokenquota: a thread-safe token bucket rate limiter.

The public API is :class:`tokenquota.public.Bucket`.
"""

from tokenquota.public import Bucket

__all__ = ["Bucket"]