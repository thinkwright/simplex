"""Core implementation for cursorvault cursor-based pagination.

This module depends only on the Python standard library.
"""


class CursorError(Exception):
    """Raised when a cursor is malformed or refers to an unknown record."""


def _validate_limit(limit):
    """Return ``limit`` when it is an int in the inclusive range [1, 100].

    Booleans are explicitly rejected: although ``bool`` subclasses ``int`` in
    Python, this contract treats booleans as non-integers.

    Raises:
        ValueError: if ``limit`` is not an integer or is outside [1, 100].
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive; "
            "booleans are not integers (got %r)" % (limit,)
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive "
            "(got %r)" % (limit,)
        )
    return limit


def paginate(records, cursor=None, limit=3):
    """Return a single page of ``records`` using cursor-based pagination.

    Each record must expose a unique string ``id`` field. Records are returned
    in their input order. When ``cursor`` is provided it is the ``id`` of the
    first record to return, and that record is included in the page.

    The returned dict has exactly three keys:

        - ``items``: the records in the current page (input order preserved)
        - ``next_cursor``: the ``id`` of the first record not returned, or
          ``None`` when no records remain
        - ``has_more``: ``True`` exactly when records remain after the page

    Neither ``records`` nor any record dict is mutated by this function.

    Raises:
        ValueError: if ``limit`` is not an integer in [1, 100].
        CursorError: if a non-null ``cursor`` is unknown or malformed.
    """
    limit = _validate_limit(limit)

    if records is None:
        raise TypeError("records must be a sequence of record mappings")

    count = len(records)

    start = 0
    if cursor is not None:
        start = -1
        for index in range(count):
            if records[index]["id"] == cursor:
                start = index
                break
        if start == -1:
            raise CursorError("unknown or malformed cursor: %r" % (cursor,))

    end = start + limit
    items = list(records[start:end])
    has_more = end < count
    next_cursor = records[end]["id"] if has_more else None

    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}