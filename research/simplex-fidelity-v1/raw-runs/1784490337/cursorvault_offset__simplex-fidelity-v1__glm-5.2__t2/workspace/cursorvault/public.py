"""Public API for the cursorvault package.

Exposes :func:`paginate` and :class:`CursorError` for index-based cursor
pagination over sequences of records that carry unique string ``id`` fields.

Only the Python standard library is used by this module.
"""

import re

__all__ = ["paginate", "CursorError"]

# A valid (non-null) cursor is a non-empty run of ASCII decimal digits, i.e. the
# decimal representation of a non-negative integer index.
_CURSOR_PATTERN = re.compile(r"[0-9]+")


class CursorError(Exception):
    """Raised when a cursor is malformed or refers to an unknown position."""


def paginate(records, cursor=None, limit=3):
    """Return one page of ``records`` using index-based cursor pagination.

    ``records`` is a sequence of mappings, each with a unique string ``id``.
    ``cursor`` is either ``None`` (begin at the first record) or a decimal
    string giving the zero-based index of the first record to return.
    ``limit`` must be an integer from 1 through 100 inclusive; booleans are not
    accepted as integers.

    The result is a brand new dict with exactly the keys ``items``,
    ``next_cursor`` and ``has_more``. ``items`` is a new list preserving the
    input order. Neither ``records`` nor any record mapping is mutated, and
    repeated calls with equal inputs return equal results.
    """
    # --- limit validation (R3, X1) -------------------------------------------
    # bool is a subclass of int, so it must be rejected explicitly: booleans are
    # not integers for this contract.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer from 1 through 100 inclusive")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be an integer from 1 through 100 inclusive")

    total = len(records)

    # --- cursor validation (R4, X2) ------------------------------------------
    if cursor is None:
        start = 0
    else:
        if not isinstance(cursor, str) or _CURSOR_PATTERN.fullmatch(cursor) is None:
            raise CursorError("cursor must be None or a non-negative decimal string")
        start = int(cursor)
        # A non-null cursor must point at an existing record; an index at or past
        # the end of the records is unknown.
        if start >= total:
            raise CursorError("cursor does not refer to a valid record")

    # --- page selection (R2, R4, R5) ------------------------------------------
    end = start + limit
    if end > total:
        end = total
    # Slicing produces a new list of the same record mappings (no mutation).
    items = list(records[start:end])

    has_more = end < total
    # When records remain, the next cursor is the index immediately after the
    # returned page (which equals ``end`` because the page is full in that case).
    next_cursor = str(end) if has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}