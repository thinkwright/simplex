"""cursorvault: cursor-based pagination utilities (standard library only).

The supported public entry point is :mod:`cursorvault.public`, which exposes
``paginate`` and ``CursorError``. They are re-exported here for convenience.
"""

from cursorvault.public import CursorError, paginate

__all__ = ["CursorError", "paginate"]