"""Public API for cursorvault.

Exposes ``paginate`` and ``CursorError``. The implementation lives in
``cursorvault.core``; this module re-exports the public surface.
"""

from cursorvault.core import CursorError, paginate

__all__ = ["CursorError", "paginate"]