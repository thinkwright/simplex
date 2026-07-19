"""cursorvault: cursor-based pagination using only the Python standard library.

The package re-exports the public API from :mod:`cursorvault.public` so that
``paginate`` and ``CursorError`` are available both as
``cursorvault.public.paginate`` and ``cursorvault.paginate``.
"""

from cursorvault.public import paginate, CursorError

__all__ = ["paginate", "CursorError"]