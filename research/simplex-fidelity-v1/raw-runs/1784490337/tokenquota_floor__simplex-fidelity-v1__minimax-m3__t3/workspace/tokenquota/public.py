"""Public API for the tokenquota package.

Exposes :class:`Bucket`, a token-bucket rate limiter whose refill is driven by
an injectable clock. Only the Python standard library is used.
"""

from tokenquota._bucket import Bucket

__all__ = ["Bucket"]