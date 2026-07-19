"""Public API for configweave.

Only the Python standard library and configweave itself are imported.
"""

from configweave._core import merge_layers

__all__ = ["merge_layers"]