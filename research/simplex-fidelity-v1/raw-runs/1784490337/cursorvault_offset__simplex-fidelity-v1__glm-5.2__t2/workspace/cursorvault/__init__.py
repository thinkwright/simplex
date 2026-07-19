"""cursorvault: index-based cursor pagination over record lists.

The public API lives in :mod:`cursorvault.public` and is re-exported here for
convenience.
"""

from cursorvault.public import CursorError, paginate

__all__ = ["CursorError", "paginate"]