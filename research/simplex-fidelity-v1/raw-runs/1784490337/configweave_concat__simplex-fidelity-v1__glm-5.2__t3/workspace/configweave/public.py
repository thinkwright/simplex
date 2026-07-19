"""Public API for configweave.

The canonical import path for the public API is::

    from configweave.public import merge_layers
"""

from configweave.merge import merge_layers

__all__ = ["merge_layers"]