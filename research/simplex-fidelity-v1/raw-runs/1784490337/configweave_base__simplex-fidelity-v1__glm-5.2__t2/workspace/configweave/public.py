"""Public API for :mod:`configweave`.

The single supported entry point is :func:`merge_layers`.
"""

from configweave._merge import merge_layers

__all__ = ["merge_layers"]