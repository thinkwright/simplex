"""Public API for the cursorvault package.

This module is implemented using only the Python standard library.
"""

import re

__all__ = ["paginate", "CursorError"]


class CursorError(Exception):
    """Raised when a pagination cursor is malformed or unknown."""


# A valid cursor is a canonical decimal (base-10) non-negative integer
# string: one or more ASCII digits, with no sign, whitespace, or other text.
_CURSOR_RE = re.compile(r"[0-9]+")


def paginate(records, cursor=None, limit=3):
    """Paginate ``records`` using an index-based cursor.

    ``records`` is a sequence of record dicts, each with a unique string ``id``.
    ``cursor`` is either ``None`` (start at the beginning) or a decimal string
    giving the zero-based index of the first record to return.
    ``limit`` is an integer from 1 through 100 inclusive (booleans are not
    accepted as integers).

    Returns a new dict with exactly ``items``, ``next_cursor`` and ``has_more``.
    ``records`` and its record dicts are never mutated.
    """
    # Validate the limit before touching records (X1).
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive"
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive"
        )

    # Validate the cursor before touching records (X2).
    if cursor is None:
        start = 0
    elif isinstance(cursor, str):
        if _CURSOR_RE.fullmatch(cursor) is None:
            raise CursorError(
                "cursor must be a decimal non-negative integer string"
            )
        start = int(cursor)
    else:
        raise CursorError("cursor must be a string or None")

    # Build the page without mutating records or any record dict (R6).
    total = len(records)
    end = start + limit
    items = list(records[start:end])
    has_more = end < total
    next_cursor = str(end) if has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}