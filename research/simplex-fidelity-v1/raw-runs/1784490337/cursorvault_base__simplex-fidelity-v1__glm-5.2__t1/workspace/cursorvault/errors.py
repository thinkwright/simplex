"""Error types for the cursorvault package.

This module deliberately depends on nothing outside the Python standard
library so that the whole package satisfies the standard-library-only
contract.
"""

__all__ = ["CursorError"]


class CursorError(Exception):
    """Raised when a pagination cursor is malformed or unknown.

    A cursor is *malformed* when it is not ``None`` and not a string, and
    *unknown* when it does not match the ``id`` of any record in the input.
    """