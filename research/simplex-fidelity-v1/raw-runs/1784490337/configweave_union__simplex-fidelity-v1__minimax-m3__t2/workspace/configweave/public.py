"""Public API for configweave.

Exposes :func:`merge_layers`, the single entry point for merging layered
configuration dictionaries.
"""

from configweave.core import merge_layers

__all__ = ["merge_layers"]