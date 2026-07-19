"""cursorvault: cursor-based pagination over records with unique string ids.

The public API lives in :mod:`cursorvault.public` and is re-exported here for
convenience. Only the Python standard library is used.
"""

from cursorvault.public import CursorError, paginate

__all__ = ["CursorError", "paginate"]