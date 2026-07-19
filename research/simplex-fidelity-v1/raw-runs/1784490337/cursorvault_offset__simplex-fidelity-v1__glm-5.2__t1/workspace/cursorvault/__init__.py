"""cursorvault: cursor-based pagination over record lists.

This package uses only the Python standard library.
"""

from cursorvault.public import CursorError, paginate

__all__ = ["CursorError", "paginate"]