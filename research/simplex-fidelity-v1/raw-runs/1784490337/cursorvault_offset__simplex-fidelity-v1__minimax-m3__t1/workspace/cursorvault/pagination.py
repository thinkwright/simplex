"""Pagination logic for cursorvault.

Contract summary:
    - records: iterable of dicts each having a unique string ``id`` field.
    - cursor: optional decimal string; the zero-based index of the first record
      to return. ``None`` (or absent) starts at index 0.
    - limit: integer in [1, 100]; booleans are rejected.

Returns a dict ``{"items": [...], "next_cursor": str|None, "has_more": bool}``.
The input records (and the dicts within them) are never mutated.
"""

from cursorvault.errors import CursorError


def _validate_limit(limit):
    # Booleans are a subclass of int in Python; explicitly reject them.
    if isinstance(limit, bool):
        raise ValueError("limit must be an integer from 1 through 100 inclusive")
    if not isinstance(limit, int):
        raise ValueError("limit must be an integer from 1 through 100 inclusive")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be an integer from 1 through 100 inclusive")


def _parse_cursor(cursor):
    if cursor is None:
        return 0
    if not isinstance(cursor, str):
        raise CursorError("cursor must be a decimal string or None")
    # Reject empty strings and whitespace-only strings.
    if cursor == "":
        raise CursorError("cursor must be a decimal string or None")
    # Must be all digits (no sign, no decimal point, no whitespace).
    if not cursor.isdigit():
        raise CursorError("cursor must be a decimal string or None")
    # ``isdigit`` accepts unicode digit characters; restrict to ASCII 0-9.
    for ch in cursor:
        if not ("0" <= ch <= "9"):
            raise CursorError("cursor must be a decimal string or None")
    return int(cursor)


def paginate(records, cursor=None, limit=3):
    """Return a page of records using a decimal-string cursor.

    See module docstring for the full contract.
    """
    _validate_limit(limit)

    # Materialize input once so we can both validate and slice without
    # mutating the caller's data.
    if records is None:
        records_list = []
    else:
        try:
            records_list = list(records)
        except TypeError:
            raise TypeError("records must be iterable")

    start = _parse_cursor(cursor)

    if start < 0:
        raise CursorError("cursor is out of range")

    if start > len(records_list):
        raise CursorError("cursor is out of range")

    end = start + limit
    page = records_list[start:end]

    has_more = end < len(records_list)
    next_cursor = str(end) if has_more else None

    # Build the result with shallow copies of each record dict so callers
    # cannot mutate the originals through the returned items.
    items = [dict(record) for record in page]

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }