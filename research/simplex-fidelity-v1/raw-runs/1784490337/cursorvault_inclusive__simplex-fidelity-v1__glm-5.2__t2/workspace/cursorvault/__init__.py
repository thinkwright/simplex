"""cursorvault: cursor-based pagination utilities.

The public API lives in :mod:`cursorvault.public` and is re-exported here for
convenience.  Only the Python standard library and cursorvault itself are used.
"""

from .public import CursorError, paginate

__all__ = ["CursorError", "paginate"]