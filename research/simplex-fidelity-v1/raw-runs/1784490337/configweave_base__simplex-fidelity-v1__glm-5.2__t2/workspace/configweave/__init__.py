"""configweave: layered configuration merging.

The canonical public entry point is :func:`configweave.public.merge_layers`.
It is re-exported here for convenience.
"""

from configweave.public import merge_layers

__all__ = ["merge_layers"]