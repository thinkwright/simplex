"""Public API for cursorvault."""

from .core import paginate
from .errors import CursorError

__all__ = ["paginate", "CursorError"]