"""Public API for cursorvault.

Exposes ``paginate`` and ``CursorError`` for external callers.
"""

from cursorvault._core import CursorError, paginate

__all__ = ["CursorError", "paginate"]