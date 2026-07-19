"""Public API for cursorvault.

Exposes:
    - CursorError: raised for malformed or unknown cursors.
    - paginate(records, cursor=None, limit=3): cursor-based pagination.
"""

from cursorvault._core import CursorError, paginate

__all__ = ["CursorError", "paginate"]