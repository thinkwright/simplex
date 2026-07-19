"""Public API for cursorvault.

Exposes:
    - CursorError: raised for malformed or unknown cursors.
    - paginate: cursor-based pagination over records with unique string id fields.
"""

from cursorvault._impl import CursorError, paginate

__all__ = ["CursorError", "paginate"]