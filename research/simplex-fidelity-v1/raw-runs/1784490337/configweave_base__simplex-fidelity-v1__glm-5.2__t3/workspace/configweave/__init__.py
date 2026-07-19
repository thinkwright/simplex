"""configweave: merge layered configuration dictionaries.

Only the Python standard library is used (see ``configweave.public`` for the
public API).
"""

from configweave.public import merge_layers

__all__ = ["merge_layers"]