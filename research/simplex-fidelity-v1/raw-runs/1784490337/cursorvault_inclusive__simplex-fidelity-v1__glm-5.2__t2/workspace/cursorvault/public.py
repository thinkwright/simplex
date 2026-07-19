"""Public API for the cursorvault package.

This module exposes :class:`CursorError` and :func:`paginate`.  It depends
only on the Python standard library (in fact, it needs no imports at all).
"""

__all__ = ["CursorError", "paginate"]


class CursorError(Exception):
    """Raised when a cursor is malformed or unknown to ``paginate``."""

    pass


def paginate(records, cursor=None, limit=3):
    """Return a single page of ``records`` keyed by cursor.

    ``records`` is a sequence of mappings, each carrying a unique string
    ``id`` field.  A non-null ``cursor`` is the ``id`` of the first record to
    return (that record is included in the page).  The result is a new dict
    with exactly three keys: ``items``, ``next_cursor`` and ``has_more``.

    ``limit`` must be an integer in the closed range ``[1, 100]``; booleans are
    rejected even though ``bool`` subclasses ``int``.

    The input ``records`` list and every record mapping are left untouched.
    """
    # [R3, X1] Validate the limit before touching the records.  Booleans are
    # not acceptable integers for this contract.
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive; got %r"
            % (limit,)
        )
    if limit < 1 or limit > 100:
        raise ValueError(
            "limit must be an integer from 1 through 100 inclusive; got %r"
            % (limit,)
        )

    # [R6] Materialise the records into a fresh list so the caller's sequence
    # is never mutated.  The record mappings themselves are shared by
    # reference but are never modified here.
    records_list = list(records)

    # [R4] Locate the first record to return.
    if cursor is None:
        start = 0
    else:
        start = None
        for index, record in enumerate(records_list):
            if isinstance(record, dict) and record.get("id") == cursor:
                start = index
                break
        if start is None:
            # [X2] Malformed or unknown cursor.
            raise CursorError("cursor not found in records: %r" % (cursor,))

    end = start + limit
    items = records_list[start:end]

    # [R5] ``has_more`` is true exactly when records remain after the page.
    has_more = end < len(records_list)

    # [R4] When more records remain, ``next_cursor`` is the id of the first
    # record not returned in the current page; otherwise it is null.
    next_cursor = records_list[end]["id"] if has_more else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }