"""Public API for the cursorvault package.

Importing ``paginate`` and ``CursorError`` from :mod:`cursorvault.public` is
the supported way to use cursorvault. This module re-exports the
implementation from :mod:`cursorvault._core` and depends only on cursorvault
itself (no third-party packages).
"""

from cursorvault._core import CursorError, paginate

__all__ = ["CursorError", "paginate"]