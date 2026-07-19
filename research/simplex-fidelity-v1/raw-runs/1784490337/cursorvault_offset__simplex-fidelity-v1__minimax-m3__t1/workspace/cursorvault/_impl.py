"""Implementation of cursor-based pagination.

Only the Python standard library is used.
"""

from cursorvault.errors import CursorError
from cursorvault.pagination import paginate

__all__ = ["CursorError", "paginate"]