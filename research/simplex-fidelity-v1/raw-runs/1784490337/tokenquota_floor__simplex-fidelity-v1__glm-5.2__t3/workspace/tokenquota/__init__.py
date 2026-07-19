"""The :mod:`tokenquota` package.

The public API is :class:`tokenquota.public.Bucket`, re-exported here for
convenience::

    from tokenquota import Bucket
    from tokenquota.public import Bucket  # equivalent
"""

from tokenquota.public import Bucket

__all__ = ["Bucket"]