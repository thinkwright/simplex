"""tokenquota: a standard-library-only token bucket rate limiter.

The package exposes :class:`Bucket` from :mod:`tokenquota.public`.
"""

from tokenquota.public import Bucket

__all__ = ["Bucket"]