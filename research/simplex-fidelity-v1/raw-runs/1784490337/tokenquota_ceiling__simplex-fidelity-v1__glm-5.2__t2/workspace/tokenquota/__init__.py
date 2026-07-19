"""tokenquota: a small, dependency-free token-bucket rate limiter.

The public API lives in :mod:`tokenquota.public`.
"""

from tokenquota.public import Bucket

__all__ = ["Bucket"]