"""Core implementation of cursor-based pagination.

Only the Python standard library is used.
"""

from cursorvault._impl import CursorError, paginate

__all__ = ["CursorError", "paginate"]