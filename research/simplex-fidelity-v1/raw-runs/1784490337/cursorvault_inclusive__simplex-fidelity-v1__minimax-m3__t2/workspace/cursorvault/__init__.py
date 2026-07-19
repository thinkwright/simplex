"""cursorvault: cursor-based pagination over records with unique string ids."""

from cursorvault.public import paginate, CursorError

__all__ = ["paginate", "CursorError"]