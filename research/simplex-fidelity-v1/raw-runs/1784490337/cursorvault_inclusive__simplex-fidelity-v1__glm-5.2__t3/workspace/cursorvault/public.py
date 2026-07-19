"""Public API for cursorvault cursor-based pagination.

This module uses only the Python standard library (and the cursorvault
package itself) so that ``cursorvault`` has no third-party dependencies.
"""

from cursorvault.errors import CursorError

__all__ = ["paginate", "CursorError"]

_DEFAULT_LIMIT = 3
_MIN_LIMIT = 1
_MAX_LIMIT = 100


def paginate(records, cursor=None, limit=_DEFAULT_LIMIT):
    """Return one page of ``records`` using cursor-based pagination.

    ``records`` is an iterable of dicts, each carrying a unique string ``id``
    field.  ``cursor`` is either ``None`` (start from the beginning) or the id
    of the first record to include.  ``limit`` is the page size (1-100).

    The result is a new dict with exactly the keys ``items``, ``next_cursor``
    and ``has_more``.  Neither ``records`` nor any record dict is mutated.
    """
    # R3 / X1: validate limit before touching records.  Booleans are a
    # subclass of int, so they are rejected explicitly.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer from 1 through 100 inclusive")
    if limit < _MIN_LIMIT or limit > _MAX_LIMIT:
        raise ValueError("limit must be an integer from 1 through 100 inclusive")

    # X2 (type): a provided cursor must be a string id.
    if cursor is not None and not isinstance(cursor, str):
        raise CursorError("cursor must be a string id or None")

    # R6: materialize records without mutating the caller's container.
    if records is None:
        raise ValueError("records must be an iterable of dicts with an id field")
    try:
        record_list = list(records)
    except TypeError as exc:
        raise ValueError(
            "records must be an iterable of dicts with an id field"
        ) from exc

    # Build an id -> position index while validating basic record shape.
    index = {}
    for position, record in enumerate(record_list):
        if not isinstance(record, dict) or "id" not in record:
            raise ValueError("each record must be a dict with an id field")
        record_id = record["id"]
        try:
            index[record_id] = position
        except TypeError as exc:
            raise ValueError("record id must be a hashable value") from exc

    # X2 (existence): the cursor must reference an existing record id.
    if cursor is not None:
        if cursor not in index:
            raise CursorError("cursor does not match any record id")
        start = index[cursor]
    else:
        start = 0

    # R2 / R4 / R5: slice the page and compute the next cursor.
    end = start + limit
    page = record_list[start:end]
    has_more = end < len(record_list)
    next_cursor = record_list[end]["id"] if has_more else None

    return {"items": page, "next_cursor": next_cursor, "has_more": has_more}