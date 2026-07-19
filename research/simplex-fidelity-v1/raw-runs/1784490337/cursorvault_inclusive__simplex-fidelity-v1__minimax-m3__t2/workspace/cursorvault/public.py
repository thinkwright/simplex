"""Public API for cursorvault.

Exposes:
    - paginate(records, cursor=None, limit=3): cursor-based pagination.
    - CursorError: raised for malformed or unknown cursors.
"""

from cursorvault.pagination import paginate, CursorError

__all__ = ["paginate", "CursorError"]