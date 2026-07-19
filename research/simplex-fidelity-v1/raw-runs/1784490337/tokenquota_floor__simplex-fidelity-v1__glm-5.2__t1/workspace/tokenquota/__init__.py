"""tokenquota package.

Convenience re-export of the public API. The canonical entry point is
``tokenquota.public`` (see RULES [R1]).
"""

from tokenquota.public import Bucket

__all__ = ["Bucket"]