"""Core implementation of cursor pagination.

Only the Python standard library is used.
"""

from __future__ import annotations

import copy


class CursorError(Exception):
    """Raised when a cursor is malformed or does not match any record."""


def _validate_limit(limit):
    # Booleans are instances of int in Python; per the contract they are
    # not valid limits here.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer between 1 and 100 inclusive")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be an integer between 1 and 100 inclusive")


def _parse_cursor(cursor):
    if cursor is None:
        return 0
    if not isinstance(cursor, str):
        raise CursorError("cursor must be a string or None")
    try:
        index = int(cursor)
    except ValueError:
        raise CursorError("cursor is not a valid integer index") from None
    if str(index) != cursor:
        raise CursorError("cursor is not a valid integer index")
    if index < 0:
        raise CursorError("cursor must be a non-negative index")
    return index


def paginate(records, cursor=None, limit=3):
    """Return a page of ``records`` starting at ``cursor`` with up to ``limit`` items.

    The returned dict has exactly three keys: ``items``, ``next_cursor``,
    and ``has_more``. Input records are not mutated.
    """
    _validate_limit(limit)

    # Defensive shallow copy of the outer list so we never hand back the
    # caller's list object. Individual record dicts are also copied so the
    # caller cannot observe mutation of items we return.
    if records is None:
        records = []
    if not isinstance(records, list):
        raise CursorError("records must be a list")

    working = [copy.copy(r) if isinstance(r, dict) else r for r in records]

    start = _parse_cursor(cursor)

    if start > len(working):
        raise CursorError("cursor is beyond the end of records")

    page = working[start : start + limit]
    end = start + len(page)
    has_more = end < len(working)
    next_cursor = str(end) if has_more else None

    return {
        "items": page,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }