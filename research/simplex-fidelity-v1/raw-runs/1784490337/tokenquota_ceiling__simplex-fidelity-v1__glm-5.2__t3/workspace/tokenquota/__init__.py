"""tokenquota: a small token-bucket rate limiter.

This package only depends on the Python standard library.
"""

from .public import Bucket

__all__ = ["Bucket"]