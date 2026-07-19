"""Public API for the cursorvault package.

Exposes:
    - paginate(records, cursor=None, limit=3)
    - CursorError
"""

from cursorvault._pagination import CursorError, paginate

__all__ = ["CursorError", "paginate"]