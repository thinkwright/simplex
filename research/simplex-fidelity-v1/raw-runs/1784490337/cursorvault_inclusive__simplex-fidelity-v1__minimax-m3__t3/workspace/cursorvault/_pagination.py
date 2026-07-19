"""Internal pagination implementation for cursorvault.

This module is private. The public surface lives in ``cursorvault.public``.
Only the Python standard library is used.
"""


class CursorError(Exception):
    """Raised when a cursor is malformed or does not match any record."""


_MIN_LIMIT = 1
_MAX_LIMIT = 100


def _validate_limit(limit):
    # Booleans are a subclass of int in Python, but the contract excludes them.
    if type(limit) is not int or isinstance(limit, bool):
        raise ValueError(
            "limit must be an integer from {0} through {1} inclusive".format(
                _MIN_LIMIT, _MAX_LIMIT
            )
        )
    if limit < _MIN_LIMIT or limit > _MAX_LIMIT:
        raise ValueError(
            "limit must be an integer from {0} through {1} inclusive".format(
                _MIN_LIMIT, _MAX_LIMIT
            )
        )


def _find_start_index(records, cursor):
    if cursor is None:
        return 0
    for index, record in enumerate(records):
        # Defensive: every record must be a dict with a string ``id``.
        if not isinstance(record, dict):
            raise CursorError("cursor does not match any record")
        record_id = record.get("id")
        if not isinstance(record_id, str):
            raise CursorError("cursor does not match any record")
        if record_id == cursor:
            return index
    raise CursorError("cursor does not match any record")


def paginate(records, cursor=None, limit=3):
    """Return a page of records starting at ``cursor``.

    Args:
        records: A sequence of dicts, each with a unique string ``id`` field.
        cursor: The ``id`` of the first record to include, or ``None`` to
            start from the beginning.
        limit: Page size; must be an integer in [1, 100]. Booleans are not
            accepted as integers.

    Returns:
        A dict with keys ``items``, ``next_cursor``, and ``has_more``.

    Raises:
        ValueError: If ``limit`` is not a valid integer in range.
        CursorError: If ``cursor`` is non-null but does not match any record.
    """
    # Validate limit first; this never touches ``records``.
    _validate_limit(limit)

    # Empty input is always a terminal page, regardless of cursor/limit.
    if not records:
        return {"items": [], "next_cursor": None, "has_more": False}

    start = _find_start_index(records, cursor)

    # Slice without mutating the input list or any record dict.
    page = records[start:start + limit]
    end_index = start + len(page)
    has_more = end_index < len(records)

    if has_more:
        next_cursor = records[end_index]["id"]
    else:
        next_cursor = None

    return {
        "items": list(page),
        "next_cursor": next_cursor,
        "has_more": has_more,
    }